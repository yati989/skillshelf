import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InstallTests(unittest.TestCase):
    def run_install(self, dest, *names):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/install.py'),
                               '--dest', str(dest), *names], text=True, capture_output=True)

    def test_companion_and_runtime_work_from_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / 'skills'
            result = self.run_install(dest, 'reading-agent')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual({p.name for p in dest.iterdir()}, {'reading-agent', 'personal-context'})
            pointer = json.loads((dest / 'reading-agent/project.json').read_text())
            self.assertEqual(Path(pointer['project_root']), ROOT / 'runtime')
            env = dict(os.environ)
            env.pop('KNOWLEDGE_BASE_PROJECT', None)
            for skill, script in [('reading-agent', 'read.py'), ('personal-context', 'context.py')]:
                probe = subprocess.run([sys.executable, str(dest / skill / 'scripts' / script), '--help'],
                                       cwd=directory, env=env, capture_output=True, text=True)
                self.assertEqual(probe.returncode, 0, probe.stderr)
                self.assertIn('usage:', probe.stdout.lower())

    def test_conflict_aborts_before_any_other_skill_is_copied(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory)
            existing = dest / 'student-agent'
            existing.mkdir()
            marker = existing / 'my-notes.txt'
            marker.write_text('preserve me')
            result = self.run_install(dest, 'student-agent', 'auto-complete')
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(marker.read_text(), 'preserve me')
            self.assertFalse((dest / 'auto-complete').exists())

    def test_unknown_or_path_like_skill_name_does_not_create_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / 'skills'
            result = self.run_install(dest, '../private')
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(dest.exists())

    def test_all_installs_only_catalog_skills_without_personal_records(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / 'skills'
            result = self.run_install(dest, '--all')
            self.assertEqual(result.returncode, 0, result.stderr)
            catalog = json.loads((ROOT / 'catalog.json').read_text())
            self.assertEqual({p.name for p in dest.iterdir()}, {s['name'] for s in catalog['skills']})
            self.assertFalse(list(dest.rglob('knowledge-book')))
            self.assertFalse(list(dest.rglob('yati-context.md')))
            self.assertFalse(list(dest.rglob('bank')))


if __name__ == '__main__':
    unittest.main()
