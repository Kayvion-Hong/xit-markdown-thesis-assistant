"""Local project snapshots; runtime and generated PDFs are deliberately excluded."""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import time


def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise ValueError('项目中有外部链接，请先移除链接后再备份。')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def revision(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def locate(store, identity):
    if not re.fullmatch(r'[0-9]+-[a-f0-9]{12}', identity):
        raise ValueError('备份编号不正确。')
    folder = store / identity
    if not (folder / 'info.json').is_file() or not (folder / 'thesis').is_dir():
        raise ValueError('找不到完整备份。')
    return folder


def listing(store):
    result = []
    for path in sorted(store.glob('*/info.json'), reverse=True):
        try:
            info = json.loads(path.read_text(encoding='utf-8'))
            locate(store, path.parent.name)
            result.append(dict(info, id=path.parent.name))
        except (ValueError, OSError):
            continue
    return result


def create(root, store, name):
    identity = f'{time.time_ns()}-{secrets.token_hex(6)}'
    folder = store / identity
    before = inventory(root)
    folder.mkdir(parents=True)
    shutil.copytree(root, folder / 'thesis')
    if inventory(folder / 'thesis') != before or inventory(root) != before:
        raise ValueError('备份期间文件发生变化，请停止其他程序的编辑后重试。')
    info = {'name': str(name).strip()[:80] or '手动备份',
            'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'files': len(before),
            'revision': revision(before)}
    (folder / 'info.json').write_text(json.dumps(info, ensure_ascii=False), encoding='utf-8')
    return dict(info, id=identity)


def preview(root, store, identity):
    folder = locate(store, identity)
    desired = inventory(folder / 'thesis')
    info = json.loads((folder / 'info.json').read_text(encoding='utf-8'))
    if revision(desired) != info['revision']:
        raise ValueError('备份文件校验失败，已停止恢复。')
    current = inventory(root)
    visible = lambda name: not name.startswith('.history/')
    return {'revision': revision(current),
            'changed': [name for name in desired if visible(name) and current.get(name) != desired[name]],
            'removed': [name for name in current if visible(name) and name not in desired]}


def restore(root, store, identity, expected):
    changes = preview(root, store, identity)
    if changes['revision'] != expected:
        raise ValueError('预览后项目又发生了变化，请重新预览再恢复。')
    source = locate(store, identity) / 'thesis'
    temporary = root.with_name(root.name + '.restore-' + secrets.token_hex(6))
    shutil.copytree(source, temporary)
    if inventory(temporary) != inventory(source):
        raise ValueError('恢复副本校验失败，当前项目未修改。')
    safety = create(root, store, '恢复前自动保护备份')
    if revision(inventory(root)) != expected:
        raise ValueError('项目已发生变化，停止恢复。')
    previous = root.with_name(root.name + '.before-restore-' + secrets.token_hex(6))
    os.replace(root, previous)
    try:
        os.replace(temporary, root)
    except OSError:
        os.replace(previous, root)
        raise
    # Keep the old directory as additional recovery protection; never discard user files.
    return {'safety': safety, 'previous': str(previous)}
