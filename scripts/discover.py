#!/usr/bin/env python3
"""Discover skills that have eval cases.

Scans a directory for skills with evals/ subdirectories containing YAML files.
Outputs a JSON array for use with GitHub Actions dynamic matrix.

Usage:
    python discover.py [skills-dir]
    python discover.py ./skills

Output (to GITHUB_OUTPUT):
    skills=["tf-guide","k8s-operator-sdk","secure-gh-workflow"]
"""

import json
import os
import sys
from pathlib import Path


def discover_skills(skills_dir: Path) -> list[str]:
    """Find all skill directories that have eval cases."""
    skills = []
    if not skills_dir.is_dir():
        return skills

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        evals_dir = skill_dir / "evals"
        if not evals_dir.is_dir():
            continue
        yaml_files = list(evals_dir.glob("*.yaml")) + list(evals_dir.glob("*.yml"))
        if yaml_files:
            skills.append(skill_dir.name)

    return skills


def main() -> None:
    skills_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(os.environ.get("SKILLS_DIR", "skills"))

    skills = discover_skills(skills_dir)
    skills_json = json.dumps(skills)

    print(f"Discovered {len(skills)} skills with evals: {', '.join(skills)}")

    # Set GitHub Actions output
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"skills={skills_json}\n")
            f.write(f"count={len(skills)}\n")
    else:
        print(skills_json)


if __name__ == "__main__":
    main()
