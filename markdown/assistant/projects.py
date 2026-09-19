"""User-owned projects and pinned templates, independent of the program folder."""
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import uuid
import zipfile

import backups
import yaml

VERSION = '0.6.0'


def data_home():
    return Path(os.environ.get('XIT_DATA_HOME', str(Path.home() / 'Documents' / 'XIT论文'))).resolve()


def read(root):
    root = Path(root).resolve()
    info = yaml.safe_load((root / 'project.yaml').read_text(encoding='utf-8'))
    if not isinstance(info, dict) or info.get('schema_version') != 1 or info.get('mode') not in ('thesis', 'ai'):
        raise ValueError('不是受支持的论文项目，请选择包含 project.yaml 的文件夹。')
    if not (root / 'thesis/metadata.yaml').is_file():
        raise ValueError('论文资料文件缺失，请从备份恢复。')
    template = root / 'template.zip'
    if not template.is_file() or hashlib.sha256(template.read_bytes()).hexdigest() != info.get('template_sha256'):
        raise ValueError('项目排版模板缺失或已被改动。请恢复原 template.zip，避免静默改变论文格式。')
    return info


def create(source, template, name, mode='thesis', destination=None):
    base = Path(destination or data_home()).resolve()
    base.mkdir(parents=True, exist_ok=True)
    name = str(name).strip()
    if not name or len(name) > 80:
        raise ValueError('请填写 1–80 个字的项目名称。')
    # Display names never become path components, including Windows reserved names.
    root = base / ('paper-' + uuid.uuid4().hex[:12])
    staging = Path(tempfile.mkdtemp(prefix='.creating-', dir=base))
    try:
        backups.inventory(Path(source))  # Reject links before copying user files.
        shutil.copytree(source, staging / 'thesis')
        shutil.copyfile(template, staging / 'template.zip')
        info = dict(schema_version=1, name=name, mode=mode, created_with=VERSION,
                    template_sha256=hashlib.sha256((staging / 'template.zip').read_bytes()).hexdigest())
        (staging / 'project.yaml').write_text(yaml.safe_dump(info, allow_unicode=True), encoding='utf-8')
        staging.rename(root)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return root


def listing():
    result = []
    configs = set(data_home().glob('*/project.yaml'))
    for marker in data_home().glob('default-*.txt'):
        configs.add(Path(marker.read_text(encoding='utf-8')) / 'project.yaml')
    for config in sorted(configs):
        try:
            info = read(config.parent)
            result.append(dict(name=info['name'], mode=info['mode'], path=str(config.parent)))
        except (ValueError, OSError, yaml.YAMLError) as error:
            result.append(dict(name=config.parent.name, path=str(config.parent), error=str(error)))
    return result


def remember(root):
    info = read(root)
    home = data_home(); home.mkdir(parents=True, exist_ok=True)
    marker = home / ('default-' + info['mode'] + '.txt')
    staging = marker.with_suffix('.tmp-' + uuid.uuid4().hex)
    staging.write_text(str(Path(root).resolve()), encoding='utf-8')
    os.replace(staging, marker)


def daily_backup(root):
    root = Path(root)
    marker = root / 'backups' / ('daily-' + date.today().isoformat() + '.json')
    if not marker.exists():
        result = backups.create(root / 'thesis', root / 'backups', '每日启动备份 ' + date.today().isoformat())
        marker.write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')


def export(root, target):
    """Export thesis + history + pinned template; never include runtime or generated PDF."""
    root = Path(root)
    read(root)
    files = backups.inventory(root / 'thesis')
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in ('project.yaml', 'template.zip'):
            archive.write(root / name, 'XIT-project/' + name)
        for name in files:
            archive.write(root / 'thesis' / name, 'XIT-project/thesis/' + name)
