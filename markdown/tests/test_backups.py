import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'assistant'))
import backups


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'thesis'
        self.store = Path(self.temp.name) / 'backups'
        self.root.mkdir()
        (self.root/'metadata.yaml').write_text('chapters: [one.md]',encoding='utf-8')
        (self.root/'one.md').write_text('旧章节',encoding='utf-8')
        (self.root/'figure.png').write_bytes(b'original image')
        self.saved = backups.create(self.root,self.store,'第一版')

    def test_roundtrip_and_undo_restore(self):
        (self.root/'one.md').write_text('新章节',encoding='utf-8')
        (self.root/'new.md').write_text('新增',encoding='utf-8')
        (self.root/'figure.png').write_bytes(b'new image')
        before = backups.inventory(self.root)
        p = backups.preview(self.root,self.store,self.saved['id'])
        self.assertEqual(p['removed'],['new.md'])
        result=backups.restore(self.root,self.store,self.saved['id'],p['revision'])
        self.assertEqual((self.root/'one.md').read_text(encoding='utf-8'),'旧章节')
        self.assertEqual((self.root/'figure.png').read_bytes(),b'original image')
        self.assertFalse((self.root/'new.md').exists())
        safety=result['safety']['id']
        backups.restore(self.root,self.store,safety,backups.preview(self.root,self.store,safety)['revision'])
        self.assertEqual(backups.inventory(self.root),before)

    def test_stale_preview_and_corrupt_backup_rejected(self):
        p=backups.preview(self.root,self.store,self.saved['id'])
        (self.root/'one.md').write_text('modified')
        with self.assertRaises(ValueError):
            backups.restore(self.root,self.store,self.saved['id'],p['revision'])
        (self.store/self.saved['id']/'thesis/one.md').write_text('corrupt')
        with self.assertRaises(ValueError): backups.preview(self.root,self.store,self.saved['id'])
        with self.assertRaises(ValueError): backups.preview(self.root,self.store,'../../thesis')

    def test_failed_swap_rolls_back(self):
        (self.root/'one.md').write_text('current')
        current=backups.inventory(self.root)
        actual=backups.os.replace
        def fail_stage(source,target):
            if '.restore-' in str(source): raise OSError('simulated disk error')
            return actual(source,target)
        with patch.object(backups.os,'replace',side_effect=fail_stage):
            with self.assertRaises(OSError):
                backups.restore(self.root,self.store,self.saved['id'],backups.revision(current))
        self.assertEqual(backups.inventory(self.root),current)

    def test_http_restore_invalidates_old_page(self):
        import app, threading, urllib.request, urllib.error, json
        from http.server import ThreadingHTTPServer
        with patch.multiple(app, THESIS_DIR=self.root, MARKDOWN_ROOT=Path(self.temp.name),
                            BUILD_PDF=Path(self.temp.name)/'old.pdf', PROJECT_MODE='thesis'):
            server=ThreadingHTTPServer(('127.0.0.1',0),app.AssistantHandler)
            server.state=app.ServerState(token='test-token')
            worker=threading.Thread(target=server.serve_forever,daemon=True); worker.start()
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            url=f'http://127.0.0.1:{server.server_port}/api/backups'
            def post(body):
                request=urllib.request.Request(url,data=json.dumps(body).encode(),headers={'X-XIT-Token':'test-token'})
                return json.load(opener.open(request,timeout=5))
            try:
                saved=post({'action':'create','name':'HTTP测试'})
                (self.root/'one.md').write_text('changed')
                app.BUILD_PDF.write_bytes(b'old pdf')
                preview=json.load(opener.open(url+'?id='+saved['id'],timeout=5))
                post({'action':'restore','id':saved['id'],'revision':preview['revision']})
                self.assertFalse(app.BUILD_PDF.exists())
                self.assertEqual((self.root/'one.md').read_text(encoding='utf-8'),'旧章节')
                with self.assertRaises(urllib.error.HTTPError) as error: post({'action':'create'})
                self.assertEqual(error.exception.code,403)
            finally:
                server.shutdown(); server.server_close(); worker.join()
