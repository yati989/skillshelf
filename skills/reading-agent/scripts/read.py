#!/usr/bin/env python3
"""Find the shared project and run its reading commands from any directory."""

import argparse
import json
import os
import sys
from pathlib import Path


def main():
    options = argparse.ArgumentParser(add_help=False)
    options.add_argument('--project', type=Path)
    args, remaining = options.parse_known_args()
    skill = Path(__file__).resolve().parents[1]
    configured = os.environ.get('KNOWLEDGE_BASE_PROJECT')
    config = skill / 'project.json'
    if args.project:
        project = args.project.expanduser().resolve()
    elif configured:
        project = Path(configured).expanduser().resolve()
    elif config.is_file():
        project = Path(json.loads(config.read_text())['project_root']).expanduser().resolve()
    else:
        candidates = [skill.parent.parent / "runtime", skill.parent.parent] + [Path.cwd()] + list(Path.cwd().parents)
        project = next((p for p in candidates
                        if (p / 'src/knowledge_base/reading_cli.py').is_file()), None)
    if project is None or not (project / 'src/knowledge_base/reading_cli.py').is_file():
        print('Reading Agent needs its Knowledge Base project. Supply --project PATH '
              'or set KNOWLEDGE_BASE_PROJECT.', file=sys.stderr)
        return 1
    project_environment = project / '.venv'
    project_python = project_environment / 'bin/python'
    if project_python.is_file() and Path(sys.prefix).resolve() != project_environment.resolve():
        os.execv(str(project_python), [str(project_python), str(Path(__file__).resolve()),
                                      *sys.argv[1:]])
    sys.path.insert(0, str(project / 'src'))
    if not any(arg == '--root' or arg.startswith('--root=') for arg in remaining):
        remaining = ['--root', str(project / '.kb-workspace')] + remaining
    from knowledge_base.reading_cli import main as run
    return run(remaining)


if __name__ == '__main__':
    raise SystemExit(main())
