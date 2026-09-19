#!/usr/bin/env python3
"""Local browser UI for editing and building the Markdown thesis.

The server binds only to 127.0.0.1 and accepts writes only for an allowlist of
thesis files. It intentionally uses the Python standard library plus PyYAML.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import secrets
import re
import hashlib
import time
import shutil
import subprocess
import sys
import threading
import webbrowser
import backups
import preview
import projects
import tempfile
from urllib.request import build_opener, ProxyHandler
from urllib.error import URLError
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import compatibility
import portable_fonts

try:
    import yaml
except ImportError as exc:
    raise SystemExit("缺少 PyYAML。请运行：python -m pip install -r requirements.txt") from exc


ASSISTANT_DIR = Path(__file__).resolve().parent
MARKDOWN_ROOT = ASSISTANT_DIR.parent
REPO_ROOT = MARKDOWN_ROOT.parent
THESIS_DIR = MARKDOWN_ROOT / "thesis"
METADATA_PATH = THESIS_DIR / "metadata.yaml"
STATIC_DIR = ASSISTANT_DIR / "static"
BUILD_PDF = MARKDOWN_ROOT / "build" / "thesis.pdf"
PROJECT_MODE = 'thesis'
PROJECT_DIR = None
# Project handshakes stay on loopback even when Windows has a system proxy.
LOCAL_HTTP = build_opener(ProxyHandler({}))


def template_path():
    if PROJECT_DIR:
        projects.read(PROJECT_DIR)
        return PROJECT_DIR / 'template.zip'
    return REPO_ROOT / '厦门工学院毕业设计论文模板.zip'


def preview_directory():
    return PROJECT_DIR / '.preview' if PROJECT_DIR else MARKDOWN_ROOT / '.preview' / PROJECT_MODE


def backup_directory():
    return PROJECT_DIR / 'backups' if PROJECT_DIR else MARKDOWN_ROOT / '.project-backups' / PROJECT_MODE


def select_external_project(path):
    global PROJECT_DIR, THESIS_DIR, METADATA_PATH, BUILD_PDF, PROJECT_MODE
    root = Path(path).resolve()
    info = projects.read(root)
    PROJECT_DIR = root
    PROJECT_MODE = info['mode']
    THESIS_DIR = root / 'thesis'
    METADATA_PATH = THESIS_DIR / 'metadata.yaml'
    BUILD_PDF = root / 'build' / 'thesis.pdf'


def project_port(path):
    return 20000 + int(hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:8], 16) % 30000


def select_project(mode: str) -> None:
    global THESIS_DIR, METADATA_PATH, BUILD_PDF, PROJECT_MODE, PROJECT_DIR
    PROJECT_DIR = None
    if mode not in ('thesis', 'ai'):
        raise AssistantError('不支持的项目。')
    PROJECT_MODE = mode
    THESIS_DIR = MARKDOWN_ROOT / ('examples/ai/thesis' if mode == 'ai' else 'thesis')
    METADATA_PATH = THESIS_DIR / 'metadata.yaml'
    BUILD_PDF = MARKDOWN_ROOT / ('build-ai' if mode == 'ai' else 'build') / 'thesis.pdf'
MAX_BODY_BYTES = 25 * 1024 * 1024
WRITE_LOCK = threading.RLock()
BUILD_LOCK = threading.Lock()

# Portable tools are scoped to this process; no system PATH changes.
portable_tex = REPO_ROOT / 'runtime' / 'TinyTeX' / 'bin' / 'windows'
if os.name == 'nt' and portable_tex.is_dir():
    os.environ['PATH'] = str(portable_tex) + os.pathsep + os.environ.get('PATH', '')
    for tool in ('xelatex', 'biber'):
        os.environ['XIT_' + tool.upper()] = str(portable_tex / (tool + '.exe'))


def safe_write(path: Path, text: str) -> None:
    """Keep the previous content before atomic replacement, at most 100 revisions."""
    with WRITE_LOCK:
        if path.is_file() and path.read_text(encoding='utf-8') == text:
            return
        folder = THESIS_DIR / '.history' / hashlib.sha256(path.resolve().relative_to(THESIS_DIR.resolve()).as_posix().encode()).hexdigest()
        folder.mkdir(parents=True, exist_ok=True)
        if path.is_file():
            (folder / (str(time.time_ns()) + '.txt')).write_bytes(path.read_bytes())
        temporary = path.with_name(path.name + '.tmp-' + secrets.token_hex(4))
        try:
            temporary.write_text(text, encoding='utf-8')
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        for old in sorted(folder.glob('*.txt'), reverse=True)[100:]:
            old.unlink()


def history_path(relative: str) -> tuple[Path, Path]:
    path = METADATA_PATH if relative == 'metadata.yaml' else allowed_content_paths().get(relative)
    if path is None:
        raise AssistantError('不允许访问这个文件的历史。')
    folder = THESIS_DIR / '.history' / hashlib.sha256(path.resolve().relative_to(THESIS_DIR.resolve()).as_posix().encode()).hexdigest()
    return path, folder


def history(relative: str) -> list[dict]:
    _, folder = history_path(relative)
    return [{'id': p.stem, 'time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(p.stem) / 1e9)),
             'text': p.read_text(encoding='utf-8')} for p in sorted(folder.glob('*.txt'), reverse=True)]


def references() -> list[dict]:
    path = str(load_metadata().get('bibliography', 'references.bib'))
    text = read_content(path)
    try:
        import bibtexparser
        entries = bibtexparser.loads(text, parser=bibtexparser.bparser.BibTexParser(ignore_nonstandard_types=False)).entries
        return [{'key': e['ID'], 'title': e.get('title', '')} for e in entries]
    except ImportError:
        return [{'key': m.group(1), 'title': ''} for m in re.finditer(r'@\w+\s*\{\s*([\w:.-]+)\s*,', text)]


def import_references(text: str) -> int:
    import bibtexparser
    if not text.strip():
        raise AssistantError('文献文件为空。')
    parsed = bibtexparser.loads(text, parser=bibtexparser.bparser.BibTexParser(ignore_nonstandard_types=False))
    entries = parsed.entries
    declared = re.findall(r'@([A-Za-z]+)\s*[{(]', text)
    count = sum(kind.lower() not in ('comment', 'preamble', 'string') for kind in declared)
    if not entries or len(entries) != count:
        raise AssistantError('BibTeX 解析不完整，请检查花括号和条目格式。没有导入任何内容。')
    keys = [e['ID'] for e in entries]
    if len(set(keys)) != len(keys):
        raise AssistantError('导入文件中有重复文献代号，请先修正。')
    for entry in entries:
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]*', entry['ID']) or not entry.get('title'):
            raise AssistantError('每条文献必须有规范的英文代号和标题。')
    with WRITE_LOCK:
        collisions = set(keys) & {r['key'] for r in references()}
        if collisions:
            raise AssistantError('以下文献已存在，本次未导入：' + ', '.join(sorted(collisions)))
        path = str(load_metadata().get('bibliography', 'references.bib'))
        # Serialize parsed entries; resolve strings before writing and keep existing data.
        save_content(path, read_content(path).rstrip() + '\n\n' + bibtexparser.dumps(parsed))
    return len(entries)


def add_reference(values: dict) -> str:
    key = str(values.get('key', '')).strip()
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]*', key):
        raise AssistantError('文献代号请以英文字母开头，只使用英文、数字、点、冒号、横线或下划线。')
    with WRITE_LOCK:
        if key in {item['key'] for item in references()}:
            raise AssistantError('文献代号已存在，请换一个代号。')
        kind = values.get('type', 'article')
        if kind not in ('article', 'book', 'online', 'inproceedings'):
            raise AssistantError('不支持的文献类型。')
        fields = {}
        for field in ('title', 'author', 'year', 'journal', 'publisher', 'url', 'doi'):
            value = str(values.get(field, '')).strip()
            if any(c in value for c in '{}\\\r\n'):
                raise AssistantError('表单字段不能包含花括号、反斜线或换行；复杂 BibTeX 请使用文献库编辑。')
            if value:
                fields[field] = value
        if not all(fields.get(k) for k in ('title', 'author', 'year')):
            raise AssistantError('请填写标题、作者和年份。')
        if not re.fullmatch(r'\d{4}', fields['year']):
            raise AssistantError('年份应为四位数字。')
        entry = '@' + kind + '{' + key + ',\n' + ''.join(f'  {k} = {{{v}}},\n' for k,v in fields.items()) + '}\n'
        path = str(load_metadata().get('bibliography', 'references.bib'))
        save_content(path, read_content(path).rstrip() + '\n\n' + entry)
    return key


def writing_issues() -> list[dict]:
    issues = []
    labels = {}
    documents = []
    keys = {r['key'] for r in references()}
    for file in content_files():
        if not file['path'].endswith('.md'):
            continue
        text = read_content(file['path'])
        # Code blocks are examples, not prose references.
        text = re.sub(r'```[^\n]*\n[\s\S]*?```', lambda m: '\n' * m.group().count('\n'), text)
        text = re.sub(r'`[^`\n]*`', '', text)
        documents.append((file, text))
        for n, line in enumerate(text.splitlines(), 1):
            for label in re.findall(r'\{#([\w:.-]+)', line):
                if label in labels:
                    issues.append({'path': file['path'], 'line': n, 'message': f'标签 {label} 重复，请删除重复对象后通过插入按钮重新添加。'})
                labels[label] = True
    for file, text in documents:
        for n, line in enumerate(text.splitlines(), 1):
            for image in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', line):
                target = (THESIS_DIR / image).resolve()
                if not within(target, THESIS_DIR) or not target.is_file():
                    issues.append({'path': file['path'], 'line': n, 'message': f'图片不存在：{image}。请删除这条图片语句，再点击“上传图片”重新选择。'})
            for key in re.findall(r'(?<![\w])@([A-Za-z][\w:.-]*)', line):
                if key not in keys:
                    issues.append({'path': file['path'], 'line': n, 'message': f'找不到文献 {key}。请通过“文献引用”添加文献，或重新选择已有文献。'})
    return issues

METADATA_FIELDS = (
    "title", "english_title", "author", "student_id", "major", "grade",
    "supervisor", "date", "keywords_cn", "keywords_en",
)


class AssistantError(RuntimeError):
    pass


def load_metadata() -> dict[str, Any]:
    data = yaml.safe_load(METADATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssistantError("metadata.yaml 格式不正确。")
    return data


def save_metadata(values: dict[str, Any]) -> None:
    data = load_metadata()
    for key in METADATA_FIELDS:
        if key not in values:
            continue
        value = values[key]
        if key in {"keywords_cn", "keywords_en"}:
            if isinstance(value, str):
                for separator in ("，", "；", ";"):
                    value = value.replace(separator, ",")
                value = [item.strip() for item in value.split(",") if item.strip()]
            if not isinstance(value, list):
                raise AssistantError(f"{key} 必须是关键词列表。")
            data[key] = [str(item).strip() for item in value if str(item).strip()]
        else:
            data[key] = str(value).strip()
    safe_write(METADATA_PATH,
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000),
    )


def within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def chapter_file(relative: str) -> Path:
    path = (THESIS_DIR / relative).resolve()
    if not within(path, THESIS_DIR) or path.suffix.lower() != '.md':
        raise AssistantError('章节必须是论文目录内的 Markdown 文件。')
    return path


def chapter_title(relative: str) -> str:
    path = chapter_file(relative)
    if not path.is_file():
        return '文件缺失：' + relative
    first = path.read_text(encoding='utf-8').lstrip('\ufeff\r\n').split('\n', 1)[0]
    return re.sub(r'\s+\{#[^}]+\}\s*$', '', first[2:].strip()) if first.startswith('# ') else Path(relative).stem


def chapter_payload() -> dict[str, Any]:
    data = load_metadata()
    active = list(data.get('chapters', []))
    archived = list(data.get('archived_chapters', []))
    entries = []
    for relative in active + archived:
        path = chapter_file(relative)
        entries.append((relative, hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None))
    revision = hashlib.sha256(json.dumps([active, archived, entries], ensure_ascii=False).encode()).hexdigest()
    return {'chapters': [{'path': p, 'title': chapter_title(p)} for p in active],
            'archived': [{'path': p, 'title': chapter_title(p)} for p in archived], 'revision': revision}


def manage_chapter(body: dict[str, Any]) -> str:
    with WRITE_LOCK:
        if body.get('revision') != chapter_payload()['revision']:
            raise AssistantError('章节或内容已变化，请关闭章节管理后重新打开再操作。')
        data = load_metadata()
        active = list(data.get('chapters', []))
        archived = list(data.get('archived_chapters', []))
        action = body.get('action')
        relative = str(body.get('path', ''))
        if action in ('add', 'rename'):
            title = str(body.get('title', '')).strip()
            if not title or len(title) > 200 or any(c in title for c in '\r\n{}'):
                raise AssistantError('请输入单行章节名称（1–200 字），不要填写花括号或手动章节编号。')
        if action == 'add':
            relative = 'chapters/ch-' + secrets.token_hex(8) + '.md'
            path = chapter_file(relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            # A unique new file is created before the configuration is updated.
            with path.open('x', encoding='utf-8') as file:
                file.write('# ' + title + '\n\n请在这里填写本章正文。\n')
            active.append(relative)
        elif action == 'restore':
            if relative not in archived or not chapter_file(relative).is_file():
                raise AssistantError('找不到可恢复的章节。')
            archived.remove(relative)
            active.append(relative)
        else:
            if relative not in active:
                raise AssistantError('章节不在当前正文中。')
            index = active.index(relative)
            if action == 'remove':
                if len(active) <= 1:
                    raise AssistantError('正文至少保留一章；可以改名或修改其内容。')
                active.remove(relative)
                if relative not in archived:
                    archived.append(relative)
            elif action in ('up', 'down'):
                target = index + (-1 if action == 'up' else 1)
                if not 0 <= target < len(active):
                    raise AssistantError('该章已位于列表边界。')
                active[index], active[target] = active[target], active[index]
            elif action == 'rename':
                path = chapter_file(relative)
                text = path.read_text(encoding='utf-8')
                match = re.match(r'\ufeff?\s*# ([^\r\n]*)', text)
                if not match:
                    raise AssistantError('该章开头缺少一级标题，请先在编辑器第一行补上“# 章节名称”。')
                attribute = re.search(r'\s+(\{#[^}]+\})\s*$', match.group(1))
                replacement = title + (' ' + attribute.group(1) if attribute else '')
                safe_write(path, text[:match.start(1)] + replacement + text[match.end(1):])
            else:
                raise AssistantError('不支持的章节操作。')
        data['chapters'] = active
        data['archived_chapters'] = archived
        safe_write(METADATA_PATH, yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000))
        return relative


def content_files(metadata: dict[str, Any] | None = None) -> list[dict[str, str]]:
    data = metadata or load_metadata()
    items: list[tuple[str, str, str]] = [
        ("中文摘要", str(data.get("abstract_cn", "abstract-cn.md")), "摘要只写正文，不要添加一级标题。"),
        ("英文摘要", str(data.get("abstract_en", "abstract-en.md")), "英文摘要只写正文，不要添加一级标题。"),
    ]
    for index, relative in enumerate(data.get("chapters", []), 1):
        items.append((f"第 {index} 章：{chapter_title(str(relative))}", str(relative), "每章保留一个以 # 开头的一级标题；章节编号由模板自动生成。"))
    items.extend([
        ("总结", str(data.get("conclusion", "conclusion.md")), "只写正文，标题由模板生成。"),
        ("谢辞", str(data.get("acknowledgements", "acknowledgements.md")), "只写正文，标题由模板生成。"),
    ])
    for index, appendix in enumerate(data.get("appendices", []) or [], 1):
        if isinstance(appendix, dict) and appendix.get("source"):
            items.append((f"附录 {index}：{appendix.get('title', '')}", str(appendix["source"]), "只写正文，附录标题由模板生成。"))
    items.append(("参考文献库", str(data.get("bibliography", "references.bib")), "高级内容：BibTeX 条目。可先使用页面中的示例。"))

    result: list[dict[str, str]] = []
    for label, relative, hint in items:
        path = (THESIS_DIR / relative).resolve()
        if within(path, THESIS_DIR) and path.is_file():
            result.append({"label": label, "path": relative.replace("\\", "/"), "hint": hint})
    return result


def allowed_content_paths() -> dict[str, Path]:
    return {
        item["path"]: (THESIS_DIR / item["path"]).resolve()
        for item in content_files()
    }


def read_content(relative: str) -> str:
    path = allowed_content_paths().get(relative)
    if path is None:
        raise AssistantError("不允许读取这个文件。")
    return path.read_text(encoding="utf-8")


def save_content(relative: str, text: str) -> None:
    path = allowed_content_paths().get(relative)
    if path is None:
        raise AssistantError("不允许修改这个文件。")
    if not isinstance(text, str):
        raise AssistantError("正文内容格式不正确。")
    safe_write(path, text.replace("\r\n", "\n"))


def save_image(filename: str, encoded: str) -> str:
    clean = Path(filename).name
    if clean != filename or not clean:
        raise AssistantError("图片文件名不正确。")
    extension = Path(clean).suffix.lower()
    if extension not in {".png", ".jpg", ".jpeg", ".pdf"}:
        raise AssistantError("仅支持 PNG、JPG、JPEG 或 PDF 图片。")
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', clean):
        clean = 'image-' + secrets.token_hex(6) + extension
    try:
        payload = encoded.split(",", 1)[-1]
        raw = base64.b64decode(payload, validate=True)
    except Exception as exc:
        raise AssistantError("图片数据无法读取。") from exc
    if not raw or len(raw) > 20 * 1024 * 1024:
        raise AssistantError("图片不能为空，且单个文件不能超过 20 MB。")
    target = THESIS_DIR / "figures" / clean
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        stem, suffix = target.stem, target.suffix
        counter = 2
        while target.exists():
            target = target.with_name(f"{stem}-{counter}{suffix}")
            counter += 1
    target.write_bytes(raw)
    return f"figures/{target.name}"


def executable_status(name: str, args: list[str]) -> dict[str, str | bool]:
    override = os.environ.get(f"XIT_{name.upper()}")
    path = override if override and Path(override).is_file() else shutil.which(name)
    bundled = REPO_ROOT / "runtime" / "pandoc" / "pandoc.exe"
    if name == "pandoc" and os.name == "nt" and bundled.is_file() and not override:
        path = str(bundled)
    if not path:
        return {"ok": False, "version": "未安装或未加入 PATH"}
    try:
        result = subprocess.run(
            [path, *args], capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=8,
        )
        line = (result.stdout or result.stderr).splitlines()[0]
    except Exception as exc:
        return {"ok": False, "version": f"程序已找到，但无法运行：{exc}"}
    if name == "pandoc" and Path(path).resolve() == bundled.resolve():
        line = "随包内置 · " + line
    return {"ok": result.returncode == 0, "version": line.strip()}


def environment_status() -> dict[str, Any]:
    result = {
        "python": {"ok": sys.version_info >= (3, 10), "version": sys.version.split()[0]},
        "pyyaml": {"ok": True, "version": getattr(yaml, "__version__", "已安装")},
        "pandoc": executable_status("pandoc", ["--version"]),
        "xelatex": executable_status("xelatex", ["--version"]),
        "biber": executable_status("biber", ["--version"]),
        "template": {
            "ok": template_path().is_file(),
            "version": "项目固定模板已校验" if PROJECT_DIR else "程序附带模板",
        },
    }
    if os.name == 'nt':
        font_dir = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'Fonts'
        missing = [name for name in portable_fonts.WINDOWS_FONTS if not (Path('C:/Windows/Fonts') / name).is_file()]
        result['fonts'] = {'ok': not missing, 'version': '原模板常用字体文件已找到；以实际编译为准' if not missing else '缺少：' + ', '.join(missing) + '。可先用随包字体生成预览；定稿字体需另行核对。'}
    return result


ACTIONS = {
    'check': ['--validate-only'],
    'pdf': [],
    'pdf-portable': [],
    'final-check': ['--validate-only', '--strict'],
    'pdf-final': ['--strict'],
}


def run_action(action: str) -> dict[str, Any]:
    if not BUILD_LOCK.acquire(blocking=False):
        raise AssistantError('已有检查或编译正在运行，请等待完成。')
    try:
        with WRITE_LOCK:
            return run_action_locked(action)
    finally:
        BUILD_LOCK.release()


def run_action_locked(action: str) -> dict[str, Any]:
    flags = ACTIONS.get(action)
    if flags is None:
        raise AssistantError("不支持这个操作。")
    if action == 'pdf-final' and (os.name != 'nt' or not environment_status().get('fonts', {}).get('ok')):
        raise AssistantError('定稿导出需要 Windows 原模板字体。请先补齐字体；当前仍可使用随包字体预览。')
    command = [sys.executable, str(MARKDOWN_ROOT / 'tools/build.py'), '--source-dir', str(THESIS_DIR), '--build-dir', str(BUILD_PDF.parent), '--template-zip', str(template_path()), *flags]
    issues = writing_issues()
    if issues:
        return {'ok': False, 'returncode': 2, 'output': '请先处理上方的写作问题。', 'issues': issues, 'pdf': False}
    child_environment = dict(os.environ)
    child_environment["PYTHONUTF8"] = "1"
    child_environment["PYTHONIOENCODING"] = "utf-8"
    if action == 'pdf-final':
        child_environment.pop('XIT_PORTABLE_FONTS', None)
    if action == "pdf-portable":
        child_environment["XIT_PORTABLE_FONTS"] = "1"
    result = subprocess.run(
        command, cwd=MARKDOWN_ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=300, env=child_environment,
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "output": output,
        "pdf": result.returncode == 0 and BUILD_PDF.is_file(),
        "issues": [],
        'portable_fonts': '使用随包开源替代字体' in output,
    }


def run_preview() -> dict[str, Any]:
    if not BUILD_LOCK.acquire(blocking=False):
        return {'ok': False, 'busy': True, 'output': '另一个编译或环境操作正在运行，请稍后重试。'}
    try:
        def compiler(source, output):
            environment=dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
            result=subprocess.run([sys.executable,str(MARKDOWN_ROOT/'tools/build.py'),
                                   '--source-dir',str(source),'--build-dir',str(output), '--template-zip', str(template_path())],
                                  cwd=MARKDOWN_ROOT,env=environment,capture_output=True,text=True,
                                  encoding='utf-8',errors='replace',timeout=300)
            log=result.stdout+'\n'+result.stderr
            return {'ok':result.returncode==0,'output':log,
                    'portable_fonts':'使用随包开源替代字体' in log}
        return preview.compile_snapshot(THESIS_DIR,preview_directory(),WRITE_LOCK,compiler)
    finally:
        BUILD_LOCK.release()


def project_payload() -> dict[str, Any]:
    metadata = load_metadata()
    public_metadata: dict[str, Any] = {}
    for key in METADATA_FIELDS:
        value = metadata.get(key, [] if key.startswith("keywords_") else "")
        public_metadata[key] = ", ".join(map(str, value)) if isinstance(value, list) else value
    return {
        'mode': PROJECT_MODE,
        'app_version': projects.VERSION,
        'project_directory': str(PROJECT_DIR or THESIS_DIR),
        'external_project': PROJECT_DIR is not None,
        'project_name': projects.read(PROJECT_DIR)['name'] if PROJECT_DIR else '旧版项目（尚未分离）',
        'preview_status': preview.status(THESIS_DIR, preview_directory()),
        'chapter_count': len(metadata.get('chapters', [])),
        'project_id': hashlib.sha256(str(THESIS_DIR.resolve()).encode()).hexdigest(),
        "metadata": public_metadata,
        "files": content_files(metadata),
        "environment": environment_status(),
        "pdf": BUILD_PDF.is_file(),
        'preview_pdf': (preview_directory()/'latest.pdf').is_file() or BUILD_PDF.is_file(),
        'portable_fonts': (BUILD_PDF.parent/'build-report.txt').is_file() and '使用随包开源替代字体' in (BUILD_PDF.parent/'build-report.txt').read_text(encoding='utf-8'),
    }


@dataclass
class ServerState:
    token: str


class AssistantHandler(BaseHTTPRequestHandler):
    server_version = "XITThesisAssistant/" + projects.VERSION

    @property
    def state(self) -> ServerState:
        return self.server.state  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        print("[论文助手] " + format % args)

    def send_bytes(self, data: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, value: Any, status: int = 200) -> None:
        self.send_bytes(
            json.dumps(value, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8", status,
        )

    def require_token(self) -> bool:
        if self.headers.get("X-XIT-Token") != self.state.token:
            self.send_json({"ok": False, "error": "页面会话已失效，请刷新页面。"}, 403)
            return False
        return True

    def json_body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise AssistantError("请求长度不正确。") from exc
        if length <= 0 or length > MAX_BODY_BYTES:
            raise AssistantError("请求为空或超过 25 MB。")
        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as exc:
            raise AssistantError("请求内容无法读取。") from exc
        if not isinstance(value, dict):
            raise AssistantError("请求内容格式不正确。")
        return value

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path.startswith('/vendor/'):
                base=(STATIC_DIR/'vendor').resolve()
                path=(base/unquote(parsed.path[len('/vendor/'):])).resolve()
                if not path.is_relative_to(base) or not path.is_file():
                    self.send_error(404); return
                kind='text/javascript' if path.suffix=='.mjs' else mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
                self.send_bytes(path.read_bytes(),kind);return
            if parsed.path == '/preview-map.json':
                path=preview_directory()/'latest-map.json'
                self.send_json(json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {'files':{},'anchors':[]});return
            if parsed.path == '/preview.pdf':
                path=preview_directory()/'latest.pdf'
                if not path.is_file():path=BUILD_PDF
                if not path.is_file():self.send_error(404);return
                self.send_bytes(path.read_bytes(),'application/pdf');return
            if parsed.path == "/":
                html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
                html = html.replace("__XIT_TOKEN__", self.state.token)
                self.send_bytes(html.encode("utf-8"), "text/html; charset=utf-8")
                return
            if parsed.path in {"/app.css", "/app.js", "/novice.js", "/novice.css", "/chapters.js", "/tutorial.js", "/comfort.js", "/undo.js", "/drafts.js", "/compat.js", "/live-preview.js", "/onboarding.js", "/onboarding.css"}:
                file = STATIC_DIR / parsed.path[1:]
                kind = "text/css" if parsed.path.endswith(".css") else "text/javascript"
                self.send_bytes(file.read_bytes(), kind + "; charset=utf-8")
                return
            if parsed.path == '/api/backups':
                with WRITE_LOCK:
                    store = backup_directory()
                    identity = parse_qs(parsed.query).get('id', [''])[0]
                    result = backups.preview(THESIS_DIR, store, identity) if identity else {'backups': backups.listing(store)}
                self.send_json({'ok': True, **result})
                return
            if parsed.path == "/api/project":
                self.send_json({"ok": True, **project_payload()})
                return
            if parsed.path == '/api/identity':
                self.send_json({'project_id': hashlib.sha256(str(THESIS_DIR.resolve()).encode()).hexdigest(),
                                'project_directory': str(PROJECT_DIR or THESIS_DIR)})
                return
            if parsed.path == '/api/projects':
                self.send_json({'projects': projects.listing(), 'home': str(projects.data_home())}); return
            if parsed.path == '/api/health':
                with WRITE_LOCK:
                    self.send_json({'preview_status': preview.status(THESIS_DIR, preview_directory()),
                                    'issues': writing_issues(), 'backups': len(backups.listing(backup_directory()))})
                return
            if parsed.path == "/api/file":
                relative = parse_qs(parsed.query).get("path", [""])[0]
                content = read_content(relative)
                self.send_json({"ok": True, "path": relative, "text": content, 'revision': hashlib.sha256(content.encode()).hexdigest()})
                return
            if parsed.path == '/api/history':
                self.send_json({'ok': True, 'versions': history(parse_qs(parsed.query).get('path', [''])[0])})
                return
            if parsed.path == '/api/references':
                self.send_json({'ok': True, 'references': references()})
                return
            if parsed.path == '/api/chapters':
                with WRITE_LOCK:
                    self.send_json({'ok': True, **chapter_payload()})
                return
            if parsed.path == "/build/thesis.pdf" and BUILD_PDF.is_file():
                self.send_bytes(BUILD_PDF.read_bytes(), "application/pdf")
                return
            if parsed.path == '/original-preview.pdf' and PROJECT_MODE == 'ai':
                self.send_bytes((MARKDOWN_ROOT / 'examples/ai/original/preview.pdf').read_bytes(), 'application/pdf')
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except AssistantError as exc:
            self.send_json({"ok": False, "error": str(exc)}, 400)
        except Exception as exc:
            self.send_json({"ok": False, "error": f"读取失败：{exc}"}, 500)

    def do_POST(self) -> None:
        if not self.require_token():
            return
        try:
            body = self.json_body()
            if self.path == '/api/project-export':
                if not PROJECT_DIR:
                    raise AssistantError('请先通过“我的论文”复制到独立项目。')
                with WRITE_LOCK, tempfile.TemporaryFile() as archive:
                    projects.export(PROJECT_DIR, archive)
                    archive.seek(0)
                    self.send_bytes(archive.read(), 'application/zip')
                return
            if self.path == '/api/projects':
                action = body.get('action')
                if action == 'create':
                    mode = body.get('mode', 'thesis')
                    if mode not in ('thesis', 'ai', 'copy'):
                        raise AssistantError('不支持的项目类型。')
                    source = THESIS_DIR if mode == 'copy' else MARKDOWN_ROOT / ('examples/ai/thesis' if mode == 'ai' else 'thesis')
                    with WRITE_LOCK:
                        root = projects.create(source, template_path() if mode == 'copy' else REPO_ROOT / '厦门工学院毕业设计论文模板.zip', body.get('name', ''), PROJECT_MODE if mode == 'copy' else mode)
                elif action == 'open':
                    root = Path(str(body.get('path', ''))).resolve()
                    projects.read(root)
                elif action == 'import-legacy':
                    old = Path(str(body.get('path', ''))).resolve()
                    source = old / 'markdown/thesis'
                    template = old / '厦门工学院毕业设计论文模板.zip'
                    if not (source / 'metadata.yaml').is_file() or not template.is_file():
                        raise AssistantError('请选择旧版 XIT 文件夹：其中应同时有 markdown 和原模板 ZIP。')
                    root = projects.create(source, template, '从旧版导入的论文')
                else:
                    raise AssistantError('不支持的项目操作。')
                port = project_port(root / 'thesis')
                url = f'http://127.0.0.1:{port}/'
                try:
                    with LOCAL_HTTP.open(url + 'api/identity', timeout=2) as response:
                        existing = json.load(response)
                    if existing.get('project_id') != hashlib.sha256(str((root/'thesis').resolve()).encode()).hexdigest():
                        raise AssistantError('该项目端口已被其他程序占用，请关闭占用程序后重试。')
                except URLError:
                    log = root / 'assistant.log'
                    with log.open('a', encoding='utf-8') as output:
                        subprocess.Popen([sys.executable, '-X', 'utf8', str(ASSISTANT_DIR/'app.py'), '--project-dir', str(root), '--no-browser'], stdout=output, stderr=output, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                    for attempt in range(30):
                        time.sleep(.2)
                        try:
                            with LOCAL_HTTP.open(url + 'api/identity', timeout=1) as response:
                                ready = json.load(response)
                            if ready.get('project_directory') == str(root):
                                break
                        except URLError:
                            continue
                    else:
                        raise AssistantError(f'项目已保存，但未能打开页面。请检查 {log}')
                projects.remember(root)
                self.send_json({'ok': True, 'url': url, 'path': str(root)}); return
            if self.path == '/api/preview':
                self.send_json(run_preview());return
            if self.path == '/api/compatibility':
                if body.get('action') == 'diagnose':
                    self.send_json({'ok': True, 'output': compatibility.diagnose()})
                    return
                if body.get('action') != 'install':
                    raise AssistantError('不支持的环境操作。')
                if not BUILD_LOCK.acquire(blocking=False):
                    raise AssistantError('正在编译，请稍后补装宏包。')
                try:
                    self.send_json(compatibility.install_package(str(body.get('name', ''))))
                finally:
                    BUILD_LOCK.release()
                return
            if self.path == '/api/backups':
                if not BUILD_LOCK.acquire(blocking=False):
                    raise AssistantError('正在编译，请等编译结束后再备份或恢复。')
                try:
                    with WRITE_LOCK:
                        store = backup_directory()
                        if body.get('action') == 'create':
                            result = backups.create(THESIS_DIR, store, body.get('name', ''))
                        elif body.get('action') == 'restore':
                            result = backups.restore(THESIS_DIR, store, str(body.get('id', '')), str(body.get('revision', '')))
                            BUILD_PDF.unlink(missing_ok=True)
                            for name in ('latest.pdf', 'latest-map.json'):
                                (preview_directory() / name).unlink(missing_ok=True)
                            self.state.token = secrets.token_urlsafe(24)
                        else:
                            raise AssistantError('不支持的备份操作。')
                    self.send_json({'ok': True, **result})
                finally:
                    BUILD_LOCK.release()
                return
            if self.path == '/api/chapters':
                relative = manage_chapter(body)
                self.send_json({'ok': True, 'path': relative})
                return
            if self.path == '/api/import-references':
                self.send_json({'ok': True, 'count': import_references(str(body.get('text', '')))})
                return
            if self.path == '/api/reference':
                self.send_json({'ok': True, 'key': add_reference(body)})
                return
            if self.path == '/api/restore':
                relative = str(body.get('path', ''))
                path, folder = history_path(relative)
                revision = str(body.get('id', ''))
                if not re.fullmatch(r'\d+', revision) or not (folder / (revision + '.txt')).is_file():
                    raise AssistantError('历史版本不存在。')
                with WRITE_LOCK:
                    safe_write(path, (folder / (revision + '.txt')).read_text(encoding='utf-8'))
                self.send_json({'ok': True})
                return
            if self.path == "/api/metadata":
                with WRITE_LOCK:
                    save_metadata(body.get("metadata", {}))
                self.send_json({"ok": True, "message": "基本信息已保存。"})
                return
            if self.path == "/api/file":
                relative = str(body.get('path', ''))
                with WRITE_LOCK:
                    current = read_content(relative)
                    if body.get('revision') and body['revision'] != hashlib.sha256(current.encode()).hexdigest():
                        raise AssistantError('此文件已被其他页面或程序修改。为避免覆盖，保存已停止；请先复制当前文字到安全位置，再重新载入文件。')
                    save_content(relative, body.get('text', ''))
                    revision = hashlib.sha256(read_content(relative).encode()).hexdigest()
                self.send_json({"ok": True, "message": "正文已保存。", 'revision': revision})
                return
            if self.path == "/api/upload":
                relative = save_image(str(body.get("name", "")), str(body.get("data", "")))
                self.send_json({"ok": True, "path": relative})
                return
            if self.path == "/api/action":
                self.send_json(run_action(str(body.get("action", ""))))
                return
            if self.path == "/api/shutdown":
                self.send_json({"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except AssistantError as exc:
            self.send_json({"ok": False, "error": str(exc)}, 400)
        except subprocess.TimeoutExpired:
            self.send_json({"ok": False, "error": "操作超过 5 分钟，已停止。请查看编译环境。"}, 500)
        except Exception as exc:
            self.send_json({"ok": False, "error": f"操作失败：{exc}"}, 500)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="启动厦门工学院 Markdown 论文助手")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--port", type=int, default=None, help="监听端口；默认按项目路径固定，0 表示临时随机端口")
    parser.add_argument('--project', choices=('thesis', 'ai'), default='thesis', help='独立普通项目或 AI 教学项目')
    parser.add_argument('--project-dir', help='独立论文文件夹（包含 project.yaml）')
    parser.add_argument('--legacy', action='store_true', help='直接编辑旧版程序内的论文，仅用于迁移前恢复草稿')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    select_project(args.project)
    if args.project_dir:
        select_external_project(args.project_dir)
    elif not args.legacy:
        home = projects.data_home()
        marker = home / ('default-' + args.project + '.txt')
        if marker.exists():
            root = Path(marker.read_text(encoding='utf-8'))
        else:
            root = projects.create(THESIS_DIR, template_path(), 'AI 教学练习' if args.project == 'ai' else '我的毕业论文', args.project)
            marker.write_text(str(root), encoding='utf-8')
        select_external_project(root)
    port = args.port if args.port is not None else project_port(THESIS_DIR)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), AssistantHandler)
    except OSError as error:
        try:
            with LOCAL_HTTP.open(f'http://127.0.0.1:{port}/api/identity', timeout=2) as response:
                existing = json.load(response)
            if existing.get('project_id') == hashlib.sha256(str(THESIS_DIR.resolve()).encode()).hexdigest():
                if not args.no_browser:
                    webbrowser.open(f'http://127.0.0.1:{port}/')
                print('已打开正在运行的论文助手。')
                return 0
        except (URLError, ValueError, TimeoutError):
            pass
        raise SystemExit(f'无法打开本机端口 {port}，请先关闭同一项目的旧助手再重试。为保留草稿访问地址，不自动切换端口。详细信息：{error}')
    if PROJECT_DIR:
        try:
            projects.daily_backup(PROJECT_DIR)
        except (OSError, ValueError):
            server.server_close()
            raise
    server.state = ServerState(token=secrets.token_urlsafe(24))  # type: ignore[attr-defined]
    url = f"http://127.0.0.1:{server.server_port}/"
    print("=" * 54)
    print("厦门工学院 Markdown 论文助手已启动")
    print(f"页面地址：{url}")
    print("使用期间请保留这个窗口；关闭窗口会停止论文助手。")
    print("=" * 54)
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    print("论文助手已关闭。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
