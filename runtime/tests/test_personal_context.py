import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from knowledge_base.personal_context import PersonalContextStore, PersonalContextError
from knowledge_base.personal_context_cli import main

class NarrativeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.store=PersonalContextStore(Path(self.temp.name))
        self.store.initialize()
    def tearDown(self): self.temp.cleanup()
    def fact(self, key='reading-style'):
        return dict(action='add',key=key,fact='Prefers discussion.',confidence='high',evidence='Explicit request')
    def narrative(self, text='A connected portrait with café examples.'):
        return dict(action='replace-narrative',key='profile-narrative',markdown=text,sensitivity='restricted',evidence='Selected discussions; interpretation is tentative.')
    def propose(self, changes):
        return self.store.propose(dict(source={'workflow':'test'},changes=changes))['proposal_id']
    def test_separate_approval_rejection_and_private_index(self):
        original=self.store.markdown_path.read_bytes()
        proposal=self.propose([self.fact(),self.narrative()])
        self.assertEqual(original,self.store.markdown_path.read_bytes())
        self.store.approve(proposal,['reading-style'])
        self.assertEqual(original,self.store.markdown_path.read_bytes())
        self.assertNotIn('narrative',json.loads(self.store.profile_path.read_text()))
        self.store.approve(proposal,['profile-narrative'])
        self.assertEqual('A connected portrait with café examples.\n',self.store.markdown_path.read_text())
        self.assertEqual(self.store.get('profile-narrative')['sensitivity'],'restricted')
        index=self.store.index(category='narrative')
        self.assertEqual(index[0]['key'],'profile-narrative')
        self.assertNotIn('markdown',index[0])
        rejected=self.propose([self.narrative('Declined words')])
        self.store.reject(rejected,'User declined')
        self.assertNotIn('Declined words',self.store.markdown_path.read_text())
        self.assertEqual(len(list((self.store.root/'history').glob('*.json'))),2)
    def test_facts_import_update_delete_and_no_change_preserve_portrait(self):
        self.store.approve(self.propose([self.narrative()]))
        before=self.store.markdown_path.read_bytes()
        self.store.apply_approved_facts([self.fact()],{'workflow':'approved-tutor-import'})
        update=self.fact();update.update(action='update',fact='Prefers examples.')
        self.store.approve(self.propose([update]))
        self.assertEqual(self.store.get('reading-style')['fact'],'Prefers examples.')
        self.store.approve(self.propose([dict(action='delete',key='reading-style',reason='User request')]))
        with self.assertRaises(PersonalContextError):self.store.get('reading-style')
        self.store.record_no_change({'workflow':'test'},'Nothing new')
        self.store.initialize()
        self.assertEqual(before,self.store.markdown_path.read_bytes())
    def test_restore_approved_narrative_without_changing_history(self):
        self.store.approve(self.propose([self.narrative()]))
        profile=self.store.profile_path.read_bytes()
        history={p.name:p.read_bytes() for p in (self.store.root/'history').glob('*')}
        expected=self.store.markdown_path.read_bytes()
        self.store.markdown_path.unlink()
        output=io.StringIO()
        with redirect_stdout(output):code=main(['--root',str(self.store.root),'export-markdown'])
        self.assertEqual(code,0)
        self.assertEqual(expected,self.store.markdown_path.read_bytes())
        self.assertEqual(profile,self.store.profile_path.read_bytes())
        self.assertEqual(history,{p.name:p.read_bytes() for p in (self.store.root/'history').glob('*')})
        stamp=self.store.markdown_path.stat().st_mtime_ns
        self.store.export_markdown()
        self.assertEqual(stamp,self.store.markdown_path.stat().st_mtime_ns)
    def test_legacy_markdown_preserved_and_never_promoted(self):
        self.store.markdown_path.write_text('Legacy facts or an external draft\n')
        self.store.initialize()
        self.store.apply_approved_facts([self.fact()],{'workflow':'approved-import'})
        self.store.export_markdown()
        self.assertEqual(self.store.markdown_path.read_text(),'Legacy facts or an external draft\n')
        self.assertNotIn('narrative',json.loads(self.store.profile_path.read_text()))
    def test_narrative_replacement_and_removal_have_history(self):
        self.store.approve(self.propose([self.narrative('First portrait')]))
        self.store.approve(self.propose([self.narrative('Revised portrait')]))
        self.store.approve(self.propose([dict(action='delete-narrative',key='profile-narrative',evidence='User requested removal')]))
        with self.assertRaises(PersonalContextError):self.store.get('profile-narrative')
        self.store.export_markdown()
        self.assertNotIn('portrait',self.store.markdown_path.read_text())
        history=[json.loads(p.read_text()) for p in (self.store.root/'history').glob('*')]
        self.assertTrue(any(h['changes'][0]['before'] and h['changes'][0]['before'].get('markdown')=='Revised portrait' and h['changes'][0]['after'] is None for h in history))
    def test_invalid_proposals_do_not_mutate_profile(self):
        before=self.store.profile_path.read_bytes()
        for bad in [dict(self.narrative(),key='other'),dict(self.narrative(),markdown=''),dict(self.fact(),key='profile-narrative'),dict(self.narrative(),sensitivity='unknown'),dict(self.fact(),action='update')]:
            with self.assertRaises(PersonalContextError):self.propose([bad])
        self.assertEqual(before,self.store.profile_path.read_bytes())

if __name__=='__main__':unittest.main()
