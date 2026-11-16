#!/usr/bin/env python3
"""Locate the Knowledge Base project and run personal-context commands."""

import argparse
import json
import os
import sys
from pathlib import Path


def main():
    options = argparse.ArgumentParser(add_help=False)
    options.add_argument("--project", type=Path)
    args, remaining = options.parse_known_args()
    skill = Path(__file__).resolve().parents[1]
    configured = os.environ.get("KNOWLEDGE_BASE_PROJECT")
    config = skill / "project.json"
    if args.project:
        project = args.project.expanduser().resolve()
    elif configured:
        project = Path(configured).expanduser().resolve()
    elif config.is_file():
        project = Path(json.loads(config.read_text())["project_root"]).expanduser().resolve()
    else:
        candidates = [skill.parent.parent / "runtime", skill.parent.parent, Path.cwd(), *Path.cwd().parents]
        project = next(
            (
                item
                for item in candidates
                if (item / "src/knowledge_base/personal_context_cli.py").is_file()
            ),
            None,
        )
    if project is None or not (
        project / "src/knowledge_base/personal_context_cli.py"
    ).is_file():
        print(
            "Personal Context needs its Knowledge Base project. Supply --project PATH "
            "or set KNOWLEDGE_BASE_PROJECT.",
            file=sys.stderr,
        )
        return 1
    environment = project / ".venv"
    project_python = environment / "bin/python"
    if project_python.is_file() and Path(sys.prefix).resolve() != environment.resolve():
        os.execv(
            str(project_python),
            [str(project_python), str(Path(__file__).resolve()), *sys.argv[1:]],
        )
    sys.path.insert(0, str(project / "src"))
    from knowledge_base.personal_context_cli import main as run

    return run(remaining)


if __name__ == "__main__":
    raise SystemExit(main())
