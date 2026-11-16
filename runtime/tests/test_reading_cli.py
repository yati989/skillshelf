import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]


class ReadingCommandTests(unittest.TestCase):
    def command(self, root, *arguments):
        environment = dict(os.environ, PYTHONPATH=str(PROJECT / 'src'),
                           PYTHONDONTWRITEBYTECODE='1')
        return subprocess.run(
            [sys.executable, '-m', 'knowledge_base.reading_cli', '--root', str(root),
             *arguments], cwd=str(root.parent), env=environment,
            text=True, capture_output=True,
        )

    def test_commands_complete_a_read_and_save_without_tutor_state(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            root = folder / '.kb-workspace'
            source = folder / 'essay.md'
            source.write_text('# Observation\n\nA careful observation can support several explanations.\n', encoding='utf-8')
            initialized = self.command(root, 'init')
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            ingested = self.command(root, 'ingest', str(source), '--title', 'Observation')
            self.assertEqual(ingested.returncode, 0, ingested.stderr)
            resource = json.loads(ingested.stdout)
            read = self.command(root, 'read', resource['source_id'])
            self.assertEqual(read.returncode, 0, read.stderr)
            passage = json.loads(read.stdout)
            body = next(b for b in passage['blocks'] if 'several explanations' in b['text'])
            payload = folder / 'note.json'
            payload.write_text(json.dumps({
                'kind': 'session', 'id': 'first-reading', 'title': 'First reading',
                'body': 'We discussed the distinction between observing and explaining.',
                'citations': [{'source_id': resource['source_id'],
                               'source_hash': passage['source_hash'],
                               'block_id': body['block_id']}],
            }), encoding='utf-8')
            saved = self.command(root, 'save-note', str(payload))
            self.assertEqual(saved.returncode, 0, saved.stderr)
            resumed = self.command(root, 'context')
            self.assertEqual(resumed.returncode, 0, resumed.stderr)
            self.assertIn('first-reading', resumed.stdout)
            self.assertFalse((root / 'subjects').exists())
            self.assertFalse((root / 'history').exists())

    def test_launcher_uses_explicit_project_from_an_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            root = folder / 'reading-data'
            launcher = PROJECT.parent / 'skills/reading-agent/scripts/read.py'
            completed = subprocess.run(
                [sys.executable, str(launcher), '--project', str(PROJECT),
                 '--root', str(root), 'init'], cwd=str(folder), capture_output=True,
                text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((root / 'library').is_dir())
            self.assertFalse((folder / '.kb-workspace').exists())

    def test_launcher_selects_project_virtual_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / 'project with spaces'
            module = project / 'src/knowledge_base'
            module.mkdir(parents=True)
            (module / '__init__.py').write_text('')
            (module / 'reading_cli.py').write_text(
                'import json, sys\ndef main(args):\n'
                '    print(json.dumps({"prefix": sys.prefix, "args": args}))\n'
                '    return 0\n')
            subprocess.run([sys.executable, '-m', 'venv', '--without-pip',
                            str(project / '.venv')], check=True, capture_output=True)
            launcher = PROJECT.parent / 'skills/reading-agent/scripts/read.py'
            result = subprocess.run([sys.executable, str(launcher), '--project', str(project),
                                     '--root', str(project / 'data'), 'context'],
                                    cwd=directory, capture_output=True, text=True,
                                    env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            self.assertEqual(result.returncode, 0, result.stderr)
            value = json.loads(result.stdout)
            self.assertEqual(Path(value['prefix']).resolve(), (project / '.venv').resolve())
            self.assertEqual(value['args'], ['--root', str(project / 'data'), 'context'])

    def test_bad_payload_and_invalid_limits_report_actionable_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            root = folder / '.kb-workspace'
            payload = folder / 'not-a-note.json'
            payload.write_text('[]', encoding='utf-8')
            failed = self.command(root, 'save-note', str(payload))
            self.assertEqual(failed.returncode, 1)
            self.assertIn('JSON object', failed.stderr)
            bad_limit = self.command(root, 'search', 'idea', '--limit', '-1')
            self.assertEqual(bad_limit.returncode, 1)
            self.assertFalse(root.exists())


if __name__ == '__main__':
    unittest.main()
