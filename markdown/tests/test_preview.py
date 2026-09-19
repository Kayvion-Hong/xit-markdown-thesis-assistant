from pathlib import Path
import tempfile,threading,sys,unittest,json,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'assistant'))
import preview


class PreviewTests(unittest.TestCase):
    def test_snapshot_and_failure_keep_last_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir();(source/'chapter.md').write_text('old')
            cache=root/'preview';lock=threading.Lock()
            def compiler(snapshot,output):
                self.assertTrue(lock.acquire(False));lock.release()
                (source/'chapter.md').write_text('new')
                self.assertEqual((snapshot/'chapter.md').read_text(),'old')
                output.mkdir();(output/'thesis.pdf').write_bytes(b'%PDF-test-success')
                (output/'project').mkdir()
                (output/'project/source-map.json').write_text(json.dumps({'files': {'chapter.md':'digest'}, 'anchors': []}))
                return {'ok':True,'output':'success'}
            self.assertTrue(preview.compile_snapshot(source,cache,lock,compiler)['ok'])
            previous=(cache/'latest.pdf').read_bytes()
            previous_map=(cache/'latest-map.json').read_bytes()
            self.assertEqual(json.loads(previous_map)['pdf_sha256'],hashlib.sha256(previous).hexdigest())
            def failure(snapshot,output):return {'ok':False,'output':'bad formula'}
            self.assertFalse(preview.compile_snapshot(source,cache,lock,failure)['ok'])
            self.assertEqual((cache/'latest.pdf').read_bytes(),previous)
            self.assertEqual((cache/'latest-map.json').read_bytes(),previous_map)
            self.assertFalse(list(cache.glob('job-*')))

    def test_exception_keeps_pdf_and_cleans_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir();cache=root/'preview';cache.mkdir()
            (cache/'latest.pdf').write_bytes(b'%PDF-old')
            def fail(*args):raise TimeoutError('timeout')
            with self.assertRaises(TimeoutError):preview.compile_snapshot(source,cache,threading.Lock(),fail)
            self.assertEqual((cache/'latest.pdf').read_bytes(),b'%PDF-old')
            self.assertFalse(list(cache.glob('job-*')))
