#!/usr/bin/env python3
"""Validate the SkillShelf distribution using only the Python standard library."""
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {
    'batch-grill-me', 'code-review', 'codebase-design', 'diagnosing-bugs',
    'grill-me', 'grill-with-docs', 'grilling', 'handoff',
    'improve-codebase-architecture', 'to-spec', 'draft-outreach',
    'enrich-companies', 'enrich-jobs', 'find-profile-links', 'full-pipeline',
    'mock-interview', 'tailor-resumes',
}


def validate():
    errors = []
    catalog = json.loads((ROOT / 'catalog.json').read_text())
    names = [s['name'] for s in catalog['skills']]
    folders = {p.parent.name for p in (ROOT / 'skills').glob('*/SKILL.md')}
    if len(names) != len(set(names)) or set(names) != folders:
        errors.append('Catalog and skill folders differ or contain duplicate names.')
    if folders & EXCLUDED:
        errors.append('Excluded skills present: ' + ', '.join(sorted(folders & EXCLUDED)))
    for item in catalog['skills']:
        name = item['name']
        if set(item['dependencies']) - folders:
            errors.append(name + ': unknown companion dependency')
        skill = ROOT / 'skills' / name / 'SKILL.md'
        if not skill.is_file():
            continue
        match = re.match(r'\A---\n(.*?)\n---\n', skill.read_text(), re.S)
        if not match:
            errors.append(name + ': missing frontmatter')
            continue
        front = match.group(1)
        if not re.search(r'^name:\s*' + re.escape(name) + r'\s*$', front, re.M):
            errors.append(name + ': mismatched frontmatter name')
        if not re.search(r'^description:\s*\S.+$', front, re.M):
            errors.append(name + ': missing description')
        if not (skill.parent / 'agents/openai.yaml').is_file():
            errors.append(name + ': missing agent metadata')
    forbidden_names = {'project.json', '.job-atlas-managed.json', '.DS_Store', 'yati-context.md', 'theme-stats.json'}
    for folder in [ROOT / 'skills', ROOT / 'runtime/src', ROOT / 'runtime/tests', ROOT / 'docs', ROOT / 'scripts']:
        for path in folder.rglob('*'):
            if path.is_symlink():
                errors.append(str(path.relative_to(ROOT)) + ': symlinks are not distributable')
            if not path.is_file() or '__pycache__' in path.parts:
                continue
            rel = str(path.relative_to(ROOT))
            if path.name in forbidden_names or 'knowledge-book' in path.parts or 'bank' in path.parts:
                errors.append(rel + ': private or local artifact')
            if path.suffix in {'.py', '.md', '.json', '.yaml', '.html'}:
                text = path.read_text()
                # Do not embed a particular machine or the author's old private workspace.
                if path.resolve() != Path(__file__).resolve() and re.search(r'/Users/' + r'admin/|\.chatgpt-projects/|Indian' + ' counsel', text):
                    errors.append(rel + ': machine-specific or personal content')
                if path.suffix == '.py':
                    try:
                        ast.parse(text, filename=rel)
                    except SyntaxError as exc:
                        errors.append(f'{rel}: {exc}')
                if path.suffix == '.md':
                    for target in re.findall(r'\]\(([^)\s]+)\)', text):
                        if target.startswith(('http:', 'https:', 'mailto:', '#', '/', '~', '<')):
                            continue
                        target = target.split('#')[0]
                        if target and not (path.parent / target).exists():
                            errors.append(f'{rel}: missing Markdown target {target}')
    return errors


def main():
    errors = validate()
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print('Validated catalog, 17 skill folders, local links, Python syntax, and distribution exclusions.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
