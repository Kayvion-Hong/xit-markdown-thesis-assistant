import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import test_assistant
assistant = test_assistant.assistant


class NoviceTests(unittest.TestCase):
    fixture = test_assistant.AssistantTests.fixture
    def test_history_restore_and_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            thesis, metadata = self.fixture(Path(tmp))
            with patch.object(assistant, 'THESIS_DIR', thesis), patch.object(assistant, 'METADATA_PATH', metadata):
                for i in range(105):
                    assistant.save_content('chapters/01.md', str(i))
                versions = assistant.history('chapters/01.md')
                self.assertEqual(len(versions), 100)
                self.assertEqual(versions[0]['text'], '103')
                assistant.save_content('chapters/01.md', versions[0]['text'])
                self.assertEqual(assistant.read_content('chapters/01.md'), '103')
                self.assertEqual(assistant.history('chapters/01.md')[0]['text'], '104')
                with self.assertRaises(assistant.AssistantError):
                    assistant.history('../outside.md')

    def test_reference_import_is_atomic_on_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            thesis, metadata = self.fixture(Path(tmp))
            (thesis / 'references.bib').write_text('', encoding='utf-8')
            with patch.object(assistant, 'THESIS_DIR', thesis), patch.object(assistant, 'METADATA_PATH', metadata):
                assistant.add_reference({'key':'test2026','title':'Test','author':'Author','year':'2026'})
                original = assistant.read_content('references.bib')
                with self.assertRaises(assistant.AssistantError):
                    assistant.import_references('@book{new2026,title={New}}\n@book{test2026,title={Duplicate}}')
                self.assertEqual(assistant.read_content('references.bib'), original)
                self.assertEqual(assistant.import_references('@online{other2026,title={Other}}'), 1)
                self.assertIn('other2026', {r['key'] for r in assistant.references()})
                with self.assertRaises(assistant.AssistantError):
                    assistant.import_references('@book{broken,title={oops')

    def test_issue_locations_and_code_examples(self):
        with tempfile.TemporaryDirectory() as tmp:
            thesis, metadata = self.fixture(Path(tmp))
            (thesis / 'references.bib').write_text('', encoding='utf-8')
            (thesis / 'chapters/01.md').write_text('# Title\n![Missing](figures/missing.png)\nText [@absent]\n```\n[@example]\n```', encoding='utf-8')
            with patch.object(assistant, 'THESIS_DIR', thesis), patch.object(assistant, 'METADATA_PATH', metadata):
                issues = assistant.writing_issues()
                self.assertEqual([i['line'] for i in issues], [2, 3])
                self.assertTrue(all(i['path'] == 'chapters/01.md' for i in issues))


if __name__ == '__main__':
    unittest.main()
