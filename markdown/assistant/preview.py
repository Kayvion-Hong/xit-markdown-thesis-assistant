"""Compile a source snapshot; preserve the last successful PDF on any failure."""
import os
import json
import hashlib
from pathlib import Path
import shutil
import tempfile
from datetime import datetime, timezone
import backups


def fingerprint(source):
    files = backups.inventory(source)
    return backups.revision({name: digest for name, digest in files.items()
                             if not name.startswith('.history/') and '.tmp-' not in name})


def status(source, cache):
    manifest = cache / 'latest-map.json'
    if not manifest.is_file() or not (cache / 'latest.pdf').is_file():
        return {'state': 'missing', 'time': None}
    info = json.loads(manifest.read_text(encoding='utf-8'))
    current = info.get('source_revision') == fingerprint(source)
    return {'state': 'current' if current else 'stale', 'time': info.get('compiled_at'),
            'portable_fonts': info.get('portable_fonts', False)}


def compile_snapshot(source, cache, write_lock, compiler):
    cache.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='job-',dir=cache) as temporary:
        job=Path(temporary)
        snapshot=job/'source'
        with write_lock:
            shutil.copytree(source,snapshot,ignore=shutil.ignore_patterns('.history','*.tmp-*'))
        source_revision = fingerprint(snapshot)
        # The source lock is released: writing and autosaving can continue while compiling.
        result=compiler(snapshot,job/'build')
        pdf=job/'build/thesis.pdf'
        if result.get('ok') and pdf.is_file() and pdf.read_bytes().startswith(b'%PDF'):
            staged=cache/'latest.tmp'
            shutil.copyfile(pdf,staged)
            mapping=job/'build/project/source-map.json'
            payload=json.loads(mapping.read_text(encoding='utf-8')) if mapping.is_file() else {'files':{},'anchors':[]}
            payload['pdf_sha256']=hashlib.sha256(staged.read_bytes()).hexdigest()
            payload.update(source_revision=source_revision,
                           compiled_at=datetime.now(timezone.utc).isoformat(),
                           portable_fonts=bool(result.get('portable_fonts')))
            map_stage=cache/'latest-map.tmp'
            map_stage.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
            os.replace(staged,cache/'latest.pdf')
            os.replace(map_stage,cache/'latest-map.json')
            result['pdf']=True
        else:
            result['ok']=False
            result['pdf']=(cache/'latest.pdf').is_file()
        logs=job/'build/logs'
        if logs.is_dir():
            shutil.copytree(logs,cache/'last-logs',dirs_exist_ok=True)
            result['output']=result.get('output','')+'\n完整编译日志已保留：'+str(cache/'last-logs')
        (cache/'last-build.txt').write_text(result.get('output',''),encoding='utf-8')
        result['preview_status'] = status(source, cache)
        return result
