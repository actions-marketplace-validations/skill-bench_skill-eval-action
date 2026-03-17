#!/usr/bin/env python3
"""Generate a self-contained HTML eval viewer from workspace data.

Embeds all eval results as JSON into a single HTML file that can be
viewed offline or uploaded as a GitHub Actions artifact.
"""

import json
import os
from pathlib import Path

WORKSPACE = Path(os.environ["WORKSPACE"])
SKILL_NAME = os.environ["SKILL_NAME"]
TEMPLATE_PATH = Path(os.environ.get("TEMPLATE_PATH", ""))


def build_viewer_data() -> dict:
    """Build the data payload for the viewer template."""
    summary_path = WORKSPACE / "summary.json"
    if not summary_path.exists():
        return {"skill_name": SKILL_NAME, "runs": [], "benchmark": None}

    summary = json.loads(summary_path.read_text())

    # Load grading details for each case
    cases = []
    for r in summary.get("results", []):
        case_slug = r["name"].replace(" ", "-").lower()
        case_dir = WORKSPACE / case_slug

        case_data = {"name": r["name"], "status": r["status"]}

        grading_path = case_dir / "grading.json"
        if grading_path.exists():
            case_data["grading"] = json.loads(grading_path.read_text())

        response_path = case_dir / "response.md"
        if response_path.exists():
            case_data["response"] = response_path.read_text()[:5000]

        metadata_path = case_dir / "eval_metadata.json"
        if metadata_path.exists():
            case_data["metadata"] = json.loads(metadata_path.read_text())

        timing_path = case_dir / "timing.json"
        if timing_path.exists():
            case_data["timing"] = json.loads(timing_path.read_text())

        cases.append(case_data)

    # Transform cases into the runs format the viewer template expects:
    #   run.id          - string (case name)
    #   run.prompt      - string (user prompt)
    #   run.grading     - object with expectations[], summary, eval_feedback
    #   run.timing      - object with total_duration_seconds, total_tokens
    #   run.outputs     - array of {type, name, content} objects
    runs = []
    for case_data in cases:
        # Convert timing field names to match viewer expectations
        timing = case_data.get("timing")
        if timing and "duration_seconds" in timing and "total_duration_seconds" not in timing:
            timing["total_duration_seconds"] = timing["duration_seconds"]

        # Convert response string to outputs array format
        response = case_data.get("response", "")
        outputs = []
        if response:
            outputs = [{"type": "text", "name": "response.md", "content": response}]

        run = {
            "id": case_data["name"],
            "prompt": case_data.get("metadata", {}).get("prompt", "") or "(no prompt)",
            "grading": case_data.get("grading"),
            "timing": timing,
            "outputs": outputs,
        }
        runs.append(run)

    return {
        "skill_name": SKILL_NAME,
        "runs": runs,
        "summary": summary,
        "generated_at": summary.get("timestamp", ""),
    }


def main() -> None:
    if not TEMPLATE_PATH.exists():
        print(f"Warning: viewer template not found at {TEMPLATE_PATH}")
        # Generate a minimal self-contained viewer
        data = build_viewer_data()
        html = f"""<!DOCTYPE html>
<html><head><title>Eval: {SKILL_NAME}</title>
<style>body{{font-family:monospace;max-width:900px;margin:40px auto;padding:0 20px}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px;text-align:left}}
.pass{{color:green}}.fail{{color:red}}pre{{background:#f4f4f4;padding:12px;overflow-x:auto}}</style></head>
<body><h1>Skill Eval: {SKILL_NAME}</h1>
<pre id="data">{json.dumps(data, indent=2)}</pre>
</body></html>"""
        (WORKSPACE / "viewer.html").write_text(html)
        return

    # Use the full viewer template
    template = TEMPLATE_PATH.read_text()
    data = build_viewer_data()
    data_json = json.dumps(data)

    # Embed data into template — variable must be EMBEDDED_DATA to match viewer.html
    if "/*__EMBEDDED_DATA__*/" in template:
        html = template.replace("/*__EMBEDDED_DATA__*/", f"const EMBEDDED_DATA = {data_json};")
    else:
        script = f"<script>const EMBEDDED_DATA = {data_json};</script>"
        html = template.replace("</head>", f"{script}\n</head>")

    output_path = WORKSPACE / "viewer.html"
    output_path.write_text(html)
    print(f"Viewer generated: {output_path}")

    # Set output
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"viewer_html={output_path}\n")


if __name__ == "__main__":
    main()
