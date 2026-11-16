#!/usr/bin/env python3
"""Install selected SkillShelf skills without replacing existing folders."""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('skills', nargs='*', help='Skill names from the catalog')
    parser.add_argument('--all', action='store_true', help='Install every catalog skill')
    parser.add_argument('--list', action='store_true', help='List the catalog without installing')
    parser.add_argument('--dest', type=Path, default=Path.home() / '.agents' / 'skills')
    parser.add_argument('--knowledge-base', type=Path, default=ROOT / 'runtime')
    args = parser.parse_args(argv)
    catalog = {s['name']: s for s in json.loads((ROOT / 'catalog.json').read_text())['skills']}
    if args.list:
        for name, item in sorted(catalog.items()):
            print(f"{name:24} {item['summary']}")
        return 0
    if args.all and args.skills:
        parser.error('Choose named skills or --all, not both.')
    selected = set(catalog if args.all else args.skills)
    if not selected:
        parser.error('Choose one or more skills, --all, or --list.')
    unknown = selected - catalog.keys()
    if unknown:
        parser.error('Unknown skills: ' + ', '.join(sorted(unknown)))
    pending = list(selected)
    while pending:
        name = pending.pop()
        for dep in catalog[name]['dependencies']:
            if dep not in selected:
                selected.add(dep)
                pending.append(dep)
    dest = args.dest.expanduser().resolve()
    runtime = args.knowledge_base.expanduser().resolve()
    if any(catalog[n]['runtime'] for n in selected):
        required = ['__main__.py', 'reading_cli.py', 'personal_context_cli.py']
        if not all((runtime / 'src' / 'knowledge_base' / n).is_file() for n in required):
            parser.error('--knowledge-base must contain the compatible src/knowledge_base runtime.')
    conflicts = [n for n in sorted(selected) if (dest / n).exists() or (dest / n).is_symlink()]
    if conflicts:
        print('Nothing installed. Existing skill folders: ' + ', '.join(conflicts), file=sys.stderr)
        return 1
    # Reject a destination within the source tree to avoid copying into itself.
    sources = ROOT / 'skills'
    if dest == sources or sources in dest.parents:
        parser.error('The installation destination must be outside the source skills tree.')
    dest.mkdir(parents=True, exist_ok=True)
    for name in sorted(selected):
        target = dest / name
        shutil.copytree(ROOT / 'skills' / name, target,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store', 'project.json'))
        if name in {'reading-agent', 'personal-context'}:
            (target / 'project.json').write_text(json.dumps({'project_root': str(runtime)}, indent=2) + '\n')
        print(f'Installed {name} -> {target}')
    print('Reload your agent to discover the installed skills.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
