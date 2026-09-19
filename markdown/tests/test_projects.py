import io
from pathlib import Path
import tempfile
import threading
import unittest
import zipfile

import backups
import preview
import projects


class ProjectSafetyTests(unittest.TestCase):
    def test_copy_pins_template_and_export_reopens_without_program(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / 'old'; source.mkdir()
            (source / 'metadata.yaml').write_text('title: test', encoding='utf-8')
            (source / 'chapter.md').write_text('my thesis', encoding='utf-8')
            template = base / 'original.zip'; template.write_bytes(b'original template')
            root = projects.create(source, template, '../CON', destination=base / 'papers')
            (root / 'thesis/chapter.md').write_text('edited', encoding='utf-8')
            self.assertEqual((source / 'chapter.md').read_text(), 'my thesis')
            template.write_bytes(b'program upgrade')
            self.assertEqual((root / 'template.zip').read_bytes(), b'original template')
            archive = io.BytesIO(); projects.export(root, archive)
            with zipfile.ZipFile(archive) as exported:
                self.assertEqual(exported.read('XIT-project/thesis/chapter.md'), b'edited')
                exported.extractall(base / 'recovered')
            self.assertEqual(projects.read(base / 'recovered/XIT-project')['name'], '../CON')
            (root / 'template.zip').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, '模板'):
                projects.read(root)

    def test_daily_backup_once_and_restore_original(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root / 'thesis').mkdir()
            chapter = root / 'thesis/chapter.md'; chapter.write_text('before')
            projects.daily_backup(root)
            chapter.write_text('after')
            projects.daily_backup(root)
            copies = backups.listing(root / 'backups')
            self.assertEqual(len(copies), 1)
            details = backups.preview(root / 'thesis', root / 'backups', copies[0]['id'])
            backups.restore(root / 'thesis', root / 'backups', copies[0]['id'], details['revision'])
            self.assertEqual(chapter.read_text(), 'before')

    def test_preview_detects_metadata_images_and_ignores_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = root / 'source'; source.mkdir()
            (source / 'metadata.yaml').write_text('title: first')
            cache = root / 'cache'
            def compiler(snapshot, output):
                output.mkdir(); (output / 'thesis.pdf').write_bytes(b'%PDF-demo')
                return {'ok': True, 'portable_fonts': True}
            preview.compile_snapshot(source, cache, threading.RLock(), compiler)
            self.assertEqual(preview.status(source, cache)['state'], 'current')
            (source / '.history').mkdir(); (source / '.history/old.txt').write_text('old')
            self.assertEqual(preview.status(source, cache)['state'], 'current')
            (source / 'figure.png').write_bytes(b'image')
            self.assertEqual(preview.status(source, cache)['state'], 'stale')
            (source / 'figure.png').unlink()
            (source / 'metadata.yaml').write_text('title: second')
            self.assertEqual(preview.status(source, cache)['state'], 'stale')
