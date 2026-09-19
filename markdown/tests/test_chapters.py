import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import test_assistant

assistant = test_assistant.assistant


class ChapterTests(unittest.TestCase):
    def test_add_reorder_rename_archive_restore_and_stale_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            thesis, metadata = test_assistant.AssistantTests().fixture(Path(tmp))
            original = '# 原章 {#ch:original}\n\n正文保持不变。\n'
            (thesis / 'chapters/01.md').write_text(original, encoding='utf-8')
            with patch.object(assistant, 'THESIS_DIR', thesis), patch.object(assistant, 'METADATA_PATH', metadata):
                def action(operation, **kwargs):
                    return assistant.manage_chapter({'action':operation, 'revision':assistant.chapter_payload()['revision'], **kwargs})
                for number in range(2, 8):
                    action('add', title=f'扩展章 {number}')
                self.assertEqual(len(assistant.load_metadata()['chapters']), 7)
                action('rename', path='chapters/01.md', title='新的标题')
                self.assertEqual((thesis / 'chapters/01.md').read_text(encoding='utf-8'), '# 新的标题 {#ch:original}\n\n正文保持不变。\n')
                action('down', path='chapters/01.md')
                self.assertEqual(assistant.load_metadata()['chapters'][1], 'chapters/01.md')
                stale = assistant.chapter_payload()['revision']
                original_bytes = (thesis / 'chapters/01.md').read_bytes()
                action('remove', path='chapters/01.md')
                self.assertEqual((thesis / 'chapters/01.md').read_bytes(), original_bytes)
                self.assertNotIn('chapters/01.md', assistant.allowed_content_paths())
                with self.assertRaises(assistant.AssistantError):
                    assistant.manage_chapter({'action':'add','title':'stale','revision':stale})
                action('restore', path='chapters/01.md')
                self.assertEqual(assistant.load_metadata()['chapters'][-1], 'chapters/01.md')
                for relative in list(assistant.load_metadata()['chapters'])[4:]:
                    action('remove', path=relative)
                self.assertEqual(len(assistant.load_metadata()['chapters']), 4)
                self.assertEqual(assistant.load_metadata()['custom_setting'], 'must-survive')

    def test_last_chapter_and_untrusted_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            thesis, metadata = test_assistant.AssistantTests().fixture(Path(tmp))
            with patch.object(assistant, 'THESIS_DIR', thesis), patch.object(assistant, 'METADATA_PATH', metadata):
                for operation, relative in [('remove','chapters/01.md'), ('rename','../escape.md'), ('restore','../escape.md')]:
                    with self.assertRaises(assistant.AssistantError):
                        assistant.manage_chapter({'action':operation, 'path':relative, 'title':'Test', 'revision':assistant.chapter_payload()['revision']})
                self.assertEqual(len(assistant.load_metadata()['chapters']), 1)
