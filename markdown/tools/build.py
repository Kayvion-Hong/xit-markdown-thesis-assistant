#!/usr/bin/env python3
"""Build an XIT thesis authored in Markdown using the original LaTeX template.

The original template ZIP is treated as immutable input. All modifications happen in
markdown/build/project, so the repository's original LaTeX distribution is never edited.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import source_map
import os
import re
import shutil
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path
from typing import Any
import portable_fonts
import windows_compile

try:
    import yaml
except ImportError as exc:  # pragma: no cover - friendly CLI path
    raise SystemExit(
        "缺少 PyYAML。请在 markdown/ 目录运行：python -m pip install -r requirements.txt"
    ) from exc


MARKDOWN_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MARKDOWN_ROOT.parent
DEFAULT_SOURCE_DIR = MARKDOWN_ROOT / "thesis"
DEFAULT_BUILD_DIR = MARKDOWN_ROOT / "build"
DEFAULT_TEMPLATE_ZIP = REPO_ROOT / "厦门工学院毕业设计论文模板.zip"
SOURCE_MAP = {'files': {}, 'anchors': []}
FILTER_PATH = MARKDOWN_ROOT / "filters" / "xit.lua"
PANDOC_FROM = (
    "markdown+raw_tex+tex_math_dollars+fenced_divs+bracketed_spans+"
    "link_attributes+pipe_tables+table_captions+citations"
)


class BuildError(RuntimeError):
    pass


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def resolve_source_path(source_dir: Path, relative: str, label: str) -> Path:
    path = (source_dir / relative).resolve()
    if not within(path, source_dir):
        raise BuildError(f"{label} escapes thesis source directory: {relative}")
    if not path.is_file():
        raise BuildError(f"{label} does not exist: {relative}")
    return path


def load_config(source_dir: Path) -> dict[str, Any]:
    config_path = source_dir / "metadata.yaml"
    if not config_path.is_file():
        raise BuildError(f"Missing metadata file: {config_path}")
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise BuildError(f"Invalid YAML in {config_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise BuildError("metadata.yaml must contain a YAML mapping/object")
    return data


def as_nonempty_text(value: Any, key: str) -> str:
    if value is None:
        raise BuildError(f"metadata.yaml is missing required field: {key}")
    text = str(value).strip()
    if not text:
        raise BuildError(f"metadata field cannot be empty: {key}")
    return text


def keyword_text(value: Any, key: str, separator: str) -> str:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        if not items:
            raise BuildError(f"metadata field cannot be empty: {key}")
        return separator.join(items)
    return as_nonempty_text(value, key)


def validate_config(config: dict[str, Any], source_dir: Path) -> dict[str, Any]:
    normalized: dict[str, Any] = dict(config)
    for key in (
        "title",
        "english_title",
        "author",
        "student_id",
        "major",
        "grade",
        "supervisor",
        "date",
    ):
        normalized[key] = as_nonempty_text(config.get(key), key)

    normalized["school"] = str(config.get("school", "厦门工学院")).strip() or "厦门工学院"
    normalized["thesis_name"] = (
        str(config.get("thesis_name", "本科毕业论文（设计）")).strip()
        or "本科毕业论文（设计）"
    )
    normalized["keywords_cn"] = keyword_text(config.get("keywords_cn"), "keywords_cn", "；")
    normalized["keywords_en"] = keyword_text(config.get("keywords_en"), "keywords_en", "; ")

    for key, default in (
        ("abstract_cn", "abstract-cn.md"),
        ("abstract_en", "abstract-en.md"),
        ("conclusion", "conclusion.md"),
        ("acknowledgements", "acknowledgements.md"),
        ("bibliography", "references.bib"),
    ):
        normalized[key] = str(config.get(key, default)).strip()
        resolve_source_path(source_dir, normalized[key], key)

    chapters = config.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        raise BuildError("metadata field 'chapters' must be a non-empty list of Markdown files")
    normalized_chapters: list[str] = []
    for index, item in enumerate(chapters, 1):
        rel = as_nonempty_text(item, f"chapters[{index}]")
        resolve_source_path(source_dir, rel, f"chapters[{index}]")
        normalized_chapters.append(rel)
    normalized["chapters"] = normalized_chapters

    appendices = config.get("appendices", [])
    if appendices is None:
        appendices = []
    if not isinstance(appendices, list):
        raise BuildError("metadata field 'appendices' must be a list")
    if len(appendices) > 2:
        raise BuildError(
            "The original template provides appendixA.tex and appendixB.tex; "
            "the Markdown frontend currently supports at most two appendices."
        )
    normalized_appendices: list[dict[str, str]] = []
    for index, item in enumerate(appendices, 1):
        if not isinstance(item, dict):
            raise BuildError(f"appendices[{index}] must be an object with title and source")
        title = as_nonempty_text(item.get("title"), f"appendices[{index}].title")
        source = as_nonempty_text(item.get("source"), f"appendices[{index}].source")
        resolve_source_path(source_dir, source, f"appendices[{index}].source")
        normalized_appendices.append({"title": title, "source": source})
    normalized["appendices"] = normalized_appendices

    logo = config.get("logo")
    if logo:
        logo = as_nonempty_text(logo, "logo")
        resolve_source_path(source_dir, logo, "logo")
        normalized["logo"] = logo

    return normalized


def markdown_sources(config: dict[str, Any], source_dir: Path) -> list[Path]:
    rels = [
        config["abstract_cn"],
        config["abstract_en"],
        *config["chapters"],
        config["conclusion"],
        config["acknowledgements"],
        *[item["source"] for item in config["appendices"]],
    ]
    return [resolve_source_path(source_dir, rel, "Markdown source") for rel in rels]


def strip_fenced_code(text: str, preserve_attributes: bool = False) -> str:
    """Remove fenced code bodies for lightweight structural validation."""
    output: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        stripped = line.lstrip()
        marker = None
        if stripped.startswith("```"):
            marker = "```"
        elif stripped.startswith("~~~"):
            marker = "~~~"
        if marker:
            if fence is None:
                fence = marker
                if preserve_attributes:
                    attrs = re.search(r"\{[^\n]*\}", stripped)
                    output.append(attrs.group(0) if attrs else "")
                    continue
            elif fence == marker:
                fence = None
            output.append("")
            continue
        output.append(line if fence is None else "")
    return "\n".join(output)


def strip_inline_code(text: str) -> str:
    return re.sub(r"`+[^`\n]*`+", "", text)


def find_level1_headings(text: str) -> list[str]:
    return re.findall(r"(?m)^#(?!#)\s+(.+?)\s*$", strip_fenced_code(text))


def bib_keys(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    return set(re.findall(r"(?im)@\w+\s*\{\s*([^,\s]+)\s*,", text))


def line_number_at(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def source_ref(path: Path, line: int | None = None) -> str:
    try:
        rel = path.relative_to(DEFAULT_SOURCE_DIR)
    except ValueError:
        rel = path
    return f"{rel}:{line}" if line else str(rel)


def validate_sources(config: dict[str, Any], source_dir: Path) -> list[str]:
    """Validate the beginner-facing Markdown source and return non-fatal warnings."""
    warnings: list[str] = []
    sources = markdown_sources(config, source_dir)

    chapter_paths = {
        resolve_source_path(source_dir, rel, "chapter") for rel in config["chapters"]
    }
    body_only = {
        resolve_source_path(source_dir, config["abstract_cn"], "abstract_cn"),
        resolve_source_path(source_dir, config["abstract_en"], "abstract_en"),
        resolve_source_path(source_dir, config["conclusion"], "conclusion"),
        resolve_source_path(source_dir, config["acknowledgements"], "acknowledgements"),
        *{
            resolve_source_path(source_dir, item["source"], "appendix")
            for item in config["appendices"]
        },
    }

    defined_labels: dict[str, tuple[Path, int]] = {}
    cited_locations: dict[str, list[tuple[Path, int]]] = {}
    internal_refs: list[tuple[str, Path, int]] = []

    image_pattern = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\)")
    label_pattern = re.compile(r"\{#((?:fig|tab|eq|code):[A-Za-z0-9_.:-]+)(?:\s+[^}]*)?\}")
    cite_pattern = re.compile(r"(?<![A-Za-z0-9_])@([A-Za-z0-9_:.+\-/]+)")
    internal_ref_pattern = re.compile(r"\[[^\]]+\]\(#((?:fig|tab|eq|code):[A-Za-z0-9_.:-]+)\)")
    placeholder_pattern = re.compile(r"请输入|这里填写|请填写|TODO|TBD", re.IGNORECASE)

    for path in sources:
        text = path.read_text(encoding="utf-8")
        structural_text = strip_inline_code(strip_fenced_code(text, preserve_attributes=True))
        if "\\documentclass" in structural_text or "\\begin{document}" in structural_text or "\\end{document}" in structural_text:
            raise BuildError(
                f"{source_ref(path)} 中出现了完整 LaTeX 文档命令。Markdown 文件只写论文内容，"
                "不要写 \\documentclass / \\begin{document} / \\end{document}。"
            )

        headings = find_level1_headings(text)
        if path in chapter_paths:
            if len(headings) != 1:
                raise BuildError(
                    f"{source_ref(path)} 必须且只能有一个一级标题（以 '# ' 开头）。"
                    f"当前检测到 {len(headings)} 个。示例：# 绪论"
                )
        elif path in body_only and headings:
            raise BuildError(
                f"{source_ref(path)} 不要写一级标题。摘要、总结、谢辞和附录标题由原 LaTeX 模板自动生成。"
            )

        for match in label_pattern.finditer(structural_text):
            label = match.group(1)
            line = line_number_at(structural_text, match.start())
            previous = defined_labels.get(label)
            if previous:
                raise BuildError(
                    f"标签重复：{label}。第一次在 {source_ref(previous[0], previous[1])}，"
                    f"再次出现在 {source_ref(path, line)}。每个图/表/公式/代码标签必须唯一。"
                )
            defined_labels[label] = (path, line)

        for match in cite_pattern.finditer(structural_text):
            key = match.group(1)
            cited_locations.setdefault(key, []).append(
                (path, line_number_at(structural_text, match.start()))
            )

        for match in internal_ref_pattern.finditer(structural_text):
            internal_refs.append(
                (match.group(1), path, line_number_at(structural_text, match.start()))
            )

        for match in image_pattern.finditer(structural_text):
            target = match.group(1).strip("<>")
            line = line_number_at(structural_text, match.start())
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", target):
                raise BuildError(
                    f"{source_ref(path, line)} 使用了网络图片 {target}。请先下载到 thesis/figures/，"
                    "再使用本地相对路径，避免以后链接失效。"
                )
            image_path = (source_dir / target).resolve()
            if not within(image_path, source_dir):
                raise BuildError(f"{source_ref(path, line)} 的图片路径超出了 thesis/ 目录：{target}")
            if not image_path.is_file():
                raise BuildError(
                    f"{source_ref(path, line)} 找不到图片：{target}。"
                    "请检查文件是否放进 thesis/figures/，以及文件名大小写是否一致。"
                )

        for match in placeholder_pattern.finditer(structural_text):
            warnings.append(
                f"仍有占位文字：{source_ref(path, line_number_at(structural_text, match.start()))} -> {match.group(0)}"
            )

    for label, path, line in internal_refs:
        if label not in defined_labels:
            raise BuildError(
                f"{source_ref(path, line)} 引用了不存在的标签 #{label}。"
                "请检查图/表/公式/代码是否定义了完全相同的 {#...} 标签。"
            )

    bibliography = resolve_source_path(source_dir, config["bibliography"], "bibliography")
    available = bib_keys(bibliography)
    missing = sorted(key for key in cited_locations if key not in available)
    if missing:
        details = []
        for key in missing:
            path, line = cited_locations[key][0]
            details.append(f"@{key}（首次出现：{source_ref(path, line)}）")
        raise BuildError(
            "正文引用了 references.bib 中不存在的文献键：" + "、".join(details)
            + "。请补充 BibTeX 条目或修正 @key。"
        )

    if not cited_locations:
        warnings.append("没有检测到 [@key] 文献引用；如果论文需要参考文献，请检查正文是否已添加引用。")

    metadata_placeholders = []
    for key in ("title", "english_title", "author", "student_id", "major", "grade", "supervisor", "date"):
        value = str(config.get(key, ""))
        if re.search(r"请输入|请填写|TODO|TBD", value, re.IGNORECASE):
            metadata_placeholders.append(key)
    if metadata_placeholders:
        warnings.append(
            "metadata.yaml 仍有未填写字段：" + ", ".join(metadata_placeholders)
            + "。初次试编译可以保留，正式提交前必须替换。"
        )

    return warnings

def safe_extract_zip(zip_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        root = destination.resolve()
        for info in archive.infolist():
            target = (destination / info.filename).resolve()
            if not within(target, root):
                raise BuildError(f"Unsafe path inside template ZIP: {info.filename}")
            unix_mode = (info.external_attr >> 16) & 0o170000
            if unix_mode == 0o120000:
                raise BuildError(f"Symlinks are not allowed inside template ZIP: {info.filename}")
        archive.extractall(destination)


def locate_project_root(extract_dir: Path) -> Path:
    candidates: list[Path] = []
    for main_tex in extract_dir.rglob("main.tex"):
        parent = main_tex.parent
        if (parent / "xitthesis.cls").is_file():
            candidates.append(parent)
    if len(candidates) != 1:
        raise BuildError(
            "Could not uniquely locate main.tex + xitthesis.cls in template ZIP; "
            f"found {len(candidates)} candidate(s)."
        )
    return candidates[0]


def latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "%": r"\%",
        "#": r"\#",
        "&": r"\&",
        "_": r"\_",
        "$": r"\$",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in value)


def patch_macro(text: str, macro: str, value: str) -> str:
    pattern = re.compile(rf"^([ \t]*\\{re.escape(macro)}\{{)(.*?)(\}})", re.MULTILINE)
    if not pattern.search(text):
        raise BuildError(f"Original template main.tex does not contain \\{macro}{{...}}")
    return pattern.sub(lambda m: m.group(1) + latex_escape(value) + m.group(3), text, count=1)


def patch_macro_raw(text: str, macro: str, value: str) -> str:
    if any(ch in value for ch in "{}\\"):
        raise BuildError(f"Unsafe raw value for \\{macro}: {value}")
    pattern = re.compile(rf"^([ \t]*\\{re.escape(macro)}\{{)(.*?)(\}})", re.MULTILINE)
    if not pattern.search(text):
        raise BuildError(f"Original template main.tex does not contain \\{macro}{{...}}")
    return pattern.sub(lambda m: m.group(1) + value + m.group(3), text, count=1)


def patch_numbered_includes(main_tex: str, chapter_count: int) -> str:
    lines = main_tex.splitlines()
    chapter_re = re.compile(r"^\s*%?\s*\\include\{chap/chapter(\d+)\}\s*$")
    existing: dict[int, int] = {}
    conclusion_index: int | None = None
    for idx, line in enumerate(lines):
        match = chapter_re.match(line)
        if match:
            existing[int(match.group(1))] = idx
        if re.match(r"^\s*%?\s*\\include\{chap/conclusion\}\s*$", line):
            conclusion_index = idx

    if not existing or conclusion_index is None:
        raise BuildError("Could not locate the original chapter include block in main.tex")

    for number, idx in existing.items():
        command = f"\\include{{chap/chapter{number}}}"
        lines[idx] = command if number <= chapter_count else "% " + command

    max_existing = max(existing)
    if chapter_count > max_existing:
        additions = [
            f"\\include{{chap/chapter{number}}}"
            for number in range(max_existing + 1, chapter_count + 1)
        ]
        # Re-find conclusion because line list has not changed length yet.
        lines[conclusion_index:conclusion_index] = additions

    return "\n".join(lines) + "\n"


def patch_appendix_includes(main_tex: str, appendix_count: int) -> str:
    lines = main_tex.splitlines()
    found = 0
    for letter_index, letter in enumerate(("A", "B"), start=1):
        pattern = re.compile(rf"^\s*%?\s*\\include\{{chap/appendix{letter}\}}\s*$")
        for idx, line in enumerate(lines):
            if pattern.match(line):
                command = f"\\include{{chap/appendix{letter}}}"
                lines[idx] = command if letter_index <= appendix_count else "% " + command
                found += 1
                break
    if appendix_count and found < appendix_count:
        raise BuildError("Configured appendices are not present as include entries in original main.tex")
    return "\n".join(lines) + "\n"


def require_executable(name: str) -> str:
    override = os.environ.get(f"XIT_{name.upper()}")
    path = override if override and Path(override).is_file() else shutil.which(name)
    bundled = REPO_ROOT / "runtime" / "pandoc" / "pandoc.exe"
    if name == "pandoc" and os.name == "nt" and bundled.is_file() and not override:
        path = str(bundled)
    if path:
        return path
    hints = {
        "pandoc": "缺少 Pandoc：只能检查 Markdown，暂时不能生成 LaTeX。请先运行 python tools/doctor.py 查看安装提示。",
        "xelatex": "缺少 XeLaTeX：可以生成 LaTeX，但不能生成 PDF。请先运行 python tools/doctor.py。",
        "biber": "缺少 Biber：参考文献无法完成编译。请先运行 python tools/doctor.py。",
    }
    raise BuildError(hints.get(name, f"系统找不到所需程序：{name}"))

def pandoc_to_tex(source: Path, source_dir: Path) -> str:
    pandoc = require_executable("pandoc")
    command = [
        pandoc,
        str(source.relative_to(source_dir)),
        "--from",
        PANDOC_FROM + '-auto_identifiers',
        "--to",
        "latex",
        "--top-level-division=chapter",
        "--biblatex",
        "--wrap=preserve",
        "--lua-filter",
        str(MARKDOWN_ROOT / 'filters/source-anchors.lua'),
        '--lua-filter',
        str(FILTER_PATH),
    ]
    relative = source.relative_to(source_dir).as_posix()
    original = source.read_text(encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='xit-map-') as temporary:
        mapping = Path(temporary) / 'blocks.json'
        env = dict(os.environ, XIT_ANCHOR_PREFIX='xit-src-' + hashlib.sha256(relative.encode()).hexdigest()[:16],
                   XIT_ANCHOR_OUTPUT=str(mapping))
        result = subprocess.run(command, cwd=source_dir, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, encoding='utf-8', errors='replace', env=env)
        if result.returncode == 0 and mapping.is_file():
            records = json.loads(mapping.read_text(encoding='utf-8'))
            SOURCE_MAP['files'][relative] = source_map.digest(original)
            SOURCE_MAP['anchors'].extend(source_map.align(original, relative, records))
    if result.returncode != 0:
        raise BuildError(
            f"Pandoc failed for {source}:\n" + textwrap.indent(result.stderr[-6000:], "  ")
        )
    if result.stderr.strip():
        eprint(result.stderr.strip())
    text = result.stdout
    # Pandoc emits \tightlist for compact Markdown lists; the original template
    # does not need that helper, so remove it from fragments.
    text = re.sub(r"(?m)^\\tightlist\s*$\n?", "", text)
    return text.rstrip() + "\n"


def write_generated_sources(
    config: dict[str, Any], source_dir: Path, project_dir: Path
) -> None:
    SOURCE_MAP['files'].clear()
    SOURCE_MAP['anchors'].clear()
    chap_dir = project_dir / "chap"
    if not chap_dir.is_dir():
        raise BuildError("Original template is missing chap/ directory")

    for index, relative in enumerate(config["chapters"], 1):
        source = resolve_source_path(source_dir, relative, f"chapter {index}")
        generated = pandoc_to_tex(source, source_dir)
        (chap_dir / f"chapter{index}.tex").write_text(generated, encoding="utf-8")

    cn = pandoc_to_tex(resolve_source_path(source_dir, config["abstract_cn"], "abstract_cn"), source_dir)
    en = pandoc_to_tex(resolve_source_path(source_dir, config["abstract_en"], "abstract_en"), source_dir)
    abstract_tex = (
        "\\begin{cnabstract}\n"
        + cn.rstrip()
        + "\n\\end{cnabstract}\n\n"
        + "\\begin{enabstract}\n"
        + en.rstrip()
        + "\n\\end{enabstract}\n"
    )
    (chap_dir / "abstract.tex").write_text(abstract_tex, encoding="utf-8")

    conclusion = pandoc_to_tex(
        resolve_source_path(source_dir, config["conclusion"], "conclusion"), source_dir
    )
    (chap_dir / "conclusion.tex").write_text(
        "\\XITConclusion\n\n" + conclusion, encoding="utf-8"
    )

    acknowledgements = pandoc_to_tex(
        resolve_source_path(source_dir, config["acknowledgements"], "acknowledgements"),
        source_dir,
    )
    (chap_dir / "acknowledgements.tex").write_text(
        "\\XITAcknowledgement\n\n" + acknowledgements, encoding="utf-8"
    )

    for index, appendix in enumerate(config["appendices"]):
        letter = chr(ord("A") + index)
        body = pandoc_to_tex(
            resolve_source_path(source_dir, appendix["source"], f"appendix {letter}"), source_dir
        )
        title = latex_escape(appendix["title"])
        # The template resets appendix counters without changing chapter.
        # Give PDF destinations an appendix namespace to prevent links landing in chapter 5.
        anchor_setup = ''.join(
            f"\\providecommand{{\\theH{counter}}}{{}}\n"
            f"\\renewcommand{{\\theH{counter}}}{{xitappendix.\\arabic{{xitappendix}}.\\arabic{{{counter}}}}}\n"
            for counter in ('section', 'figure', 'table', 'equation', 'lstlisting')
        )
        (chap_dir / f"appendix{letter}.tex").write_text(
            f"\\XITAppendix{{{title}}}\n" + anchor_setup + '\n' + body, encoding="utf-8"
        )

    (project_dir / 'source-map.json').write_text(json.dumps(SOURCE_MAP, ensure_ascii=False), encoding='utf-8')

    bibliography = resolve_source_path(source_dir, config["bibliography"], "bibliography")
    shutil.copy2(bibliography, project_dir / "ref.bib")

    figures = source_dir / "figures"
    if figures.is_dir():
        shutil.copytree(figures, project_dir / "figures", dirs_exist_ok=True)


def patch_main_tex(config: dict[str, Any], project_dir: Path) -> None:
    main_path = project_dir / "main.tex"
    if not main_path.is_file():
        raise BuildError("Original template is missing main.tex")
    text = main_path.read_text(encoding="utf-8")

    mapping = {
        "XITSchool": config["school"],
        "XITThesisName": config["thesis_name"],
        "XITTitle": config["title"],
        "XITEnglishTitle": config["english_title"],
        "XITAuthor": config["author"],
        "XITStudentID": config["student_id"],
        "XITMajor": config["major"],
        "XITGrade": config["grade"],
        "XITSupervisor": config["supervisor"],
        "XITDate": config["date"],
        "XITChineseKeywords": config["keywords_cn"],
        "XITEnglishKeywords": config["keywords_en"],
    }
    for macro, value in mapping.items():
        text = patch_macro(text, macro, value)

    if config.get("logo"):
        text = patch_macro_raw(text, "XITLogo", config["logo"])

    text = patch_numbered_includes(text, len(config["chapters"]))
    text = patch_appendix_includes(text, len(config["appendices"]))
    # Measure in the original cover font/size; preserve the template layout.
    title_guard = r"""
\makeatletter
\AtBeginDocument{%
  \begingroup
  \setbox0=\hbox{{\heiti\mdseries\zihao{3}\xit@title}}%
  \ifdim\wd0>\xit@coverfieldwidth
    \PackageError{xit-assistant}{XIT-TITLE-TOO-WIDE}{Shorten the title to fit the original cover field.}%
  \fi
  \endgroup
}
\makeatother
"""
    text = text.replace(r"\begin{document}", title_guard + "\n" + r"\begin{document}", 1)
    main_path.write_text(text, encoding="utf-8")


def first_latex_error(output: str) -> str:
    lines = output.splitlines()
    patterns = (
        "! LaTeX Error:",
        "! Package ",
        "! Undefined control sequence",
        "fontspec error",
        "Emergency stop",
        "Fatal error",
    )
    for idx, line in enumerate(lines):
        if any(token.lower() in line.lower() for token in patterns):
            return "\n".join(lines[max(0, idx - 2): min(len(lines), idx + 8)])
    return "\n".join(lines[-30:])


def run_logged(command: list[str], cwd: Path, log_path: Path, env=None) -> None:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
    )
    log_path.write_text(result.stdout, encoding="utf-8")
    if result.returncode != 0:
        excerpt = first_latex_error(result.stdout)
        raise BuildError(
            f"编译命令失败：{' '.join(Path(x).name if i == 0 else x for i, x in enumerate(command))}\n"
            f"完整日志：{log_path}\n最先检测到的关键错误：\n"
            + textwrap.indent(excerpt, "  ")
        )


def analyze_final_latex_log(log_path: Path) -> list[str]:
    if not log_path.is_file():
        return []
    text = log_path.read_text(encoding="utf-8", errors="replace")
    warnings: list[str] = []
    undefined = re.findall(r"LaTeX Warning: (?:Reference|Citation) `([^']+)'[^\n]*undefined", text)
    if undefined:
        warnings.append("仍有未解析的引用：" + ", ".join(sorted(set(undefined))))
    if "There were undefined references" in text:
        warnings.append("LaTeX 报告仍存在未解析的交叉引用；请检查标签后重新构建。")
    overfull = len(re.findall(r"Overfull \\hbox", text))
    if overfull:
        warnings.append(f"检测到 {overfull} 处 Overfull \\hbox；PDF 已生成，但请检查是否有文字或表格越出页边。")
    return warnings


def write_build_report(build_dir: Path, config: dict[str, Any], warnings: list[str], pdf: Path | None) -> Path:
    report = build_dir / "build-report.txt"
    lines = [
        "厦门工学院 Markdown 论文构建报告",
        "=" * 36,
        f"章节数：{len(config['chapters'])}",
        f"附录数：{len(config['appendices'])}",
        f"PDF：{pdf if pdf else '未生成（仅检查/仅生成 LaTeX）'}",
        "",
        "警告：",
    ]
    if warnings:
        lines.extend(f"- {item}" for item in warnings)
    else:
        lines.append("- 无")
    lines += [
        "",
        "正式提交前仍需人工检查：封面、摘要、目录、图表、公式、参考文献、分页与字体。",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def compile_pdf(project_dir: Path, build_dir: Path) -> tuple[Path, list[str]]:
    tex_root = REPO_ROOT / 'runtime/TinyTeX'
    override = os.environ.get('XIT_XELATEX')
    if override:
        candidate = Path(override).resolve().parent.parent.parent
        if (candidate / 'texmf-dist').is_dir():
            tex_root = candidate
    try:
        with windows_compile.native_workspace(project_dir, tex_root) as (staged, binary, env):
            if binary:
                print('[路径兼容] 使用英文临时编译目录，论文仍保存在原位置。')
            return compile_pdf_native(staged, build_dir, binary, env)
    except OSError as exc:
        raise BuildError('无法创建或使用临时编译目录：' + str(exc)) from exc
    except RuntimeError as exc:
        raise BuildError(str(exc)) from exc


def compile_pdf_native(project_dir, build_dir, binary, env):
    xelatex = str(binary / 'xelatex.exe') if binary else require_executable('xelatex')
    biber = str(binary / 'biber.exe') if binary else require_executable('biber')
    logs = build_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)

    common = [xelatex, "-interaction=nonstopmode", "-halt-on-error", "main.tex"]
    print("[3/4] XeLaTeX 第 1 遍：生成辅助信息")
    run_logged(common, project_dir, logs / "xelatex-1.txt", env)
    print("      Biber：处理参考文献")
    run_logged([biber, "main"], project_dir, logs / "biber.txt", env)
    print("      XeLaTeX 第 2、3 遍：更新目录、编号和引用")
    run_logged(common, project_dir, logs / "xelatex-2.txt", env)
    run_logged(common, project_dir, logs / "xelatex-3.txt", env)

    source_map.resolve_headers(project_dir)
    pdf = project_dir / "main.pdf"
    if not pdf.is_file():
        raise BuildError("XeLaTeX 没有生成 main.pdf。请查看 build/logs/ 下的日志。")
    output = build_dir / "thesis.pdf"
    shutil.copy2(pdf, output)
    return output, analyze_final_latex_log(logs / "xelatex-3.txt")

def clean_stale_template_outputs(project_dir: Path) -> None:
    # The distributed ZIP contains preview/main PDFs. They are useful to LaTeX users
    # but misleading inside a generated Markdown build tree, so remove stale outputs.
    names = {
        "main.pdf", "preview.pdf", "main.aux", "main.bbl", "main.bcf",
        "main.blg", "main.log", "main.out", "main.run.xml", "main.toc",
        "main.lof", "main.lot",
    }
    for name in names:
        path = project_dir / name
        if path.exists() and path.is_file():
            path.unlink()


def prepare_project(template_zip: Path, build_dir: Path) -> Path:
    extract_dir = build_dir / "_extract"
    project_dir = build_dir / "project"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    if project_dir.exists():
        shutil.rmtree(project_dir)
    safe_extract_zip(template_zip, extract_dir)
    root = locate_project_root(extract_dir)
    shutil.copytree(root, project_dir)
    clean_stale_template_outputs(project_dir)
    shutil.rmtree(extract_dir)
    return project_dir


def validate_build_directory(build_dir: Path, source_dir: Path, template_zip: Path) -> None:
    """Refuse cleanup of source trees or directories containing template inputs."""
    protected = (source_dir, MARKDOWN_ROOT, template_zip, FILTER_PATH)
    if any(within(path, build_dir) for path in protected) or within(build_dir, source_dir):
        raise BuildError("构建目录不能是论文源目录、程序目录或它们的上级目录。请使用独立的 build/ 目录。")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the Markdown thesis through the original XIT LaTeX template."
    )
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD_DIR)
    parser.add_argument("--template-zip", type=Path, default=DEFAULT_TEMPLATE_ZIP)
    parser.add_argument(
        "--tex-only",
        action="store_true",
        help="Generate the temporary LaTeX project but do not run XeLaTeX/Biber.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate metadata and Markdown sources without generating LaTeX.",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not delete the previous build directory before generating output.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat beginner-facing warnings (such as placeholders) as errors.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_dir = args.source_dir.resolve()
    build_dir = args.build_dir.resolve()
    template_zip = args.template_zip.resolve()

    try:
        print("[1/4] 检查论文源文件")
        if not source_dir.is_dir():
            raise BuildError(f"找不到论文源目录：{source_dir}")
        if not template_zip.is_file():
            raise BuildError(
                f"找不到原 LaTeX 模板：{template_zip}\n"
                "请确认 markdown/ 与 ‘厦门工学院毕业设计论文模板.zip’ 位于同一个仓库中。"
            )
        if not FILTER_PATH.is_file():
            raise BuildError(f"缺少 Pandoc 转换规则：{FILTER_PATH}")

        config = validate_config(load_config(source_dir), source_dir)
        warnings = validate_sources(config, source_dir)
        for warning in warnings:
            print(f"  [提醒] {warning}")
        if args.strict and warnings:
            raise BuildError(
                "严格检查未通过：仍有需要处理的提醒。请先修正上面的项目，再重新运行。"
            )

        template_hash_before = sha256_file(template_zip)
        print(f"      章节 {len(config['chapters'])} 个，附录 {len(config['appendices'])} 个")
        print("      Markdown 结构检查通过")

        if args.validate_only:
            print("\n[OK] 检查完成：没有阻断构建的问题。")
            if warnings:
                print("  仍有提醒；初稿可继续，正式提交前建议使用 --strict 再检查一次。")
            return 0

        print("[2/4] 生成临时 LaTeX 工程（原模板只读，不会被修改）")
        require_executable("pandoc")
        validate_build_directory(build_dir, source_dir, template_zip)
        if not args.no_clean and build_dir.exists():
            shutil.rmtree(build_dir)
        build_dir.mkdir(parents=True, exist_ok=True)

        project_dir = prepare_project(template_zip, build_dir)
        write_generated_sources(config, source_dir, project_dir)
        patch_main_tex(config, project_dir)
        font_warning = portable_fonts.configure(project_dir)
        if font_warning:
            warnings.append(font_warning)
            print('[字体提示] ' + font_warning)

        template_hash_after = sha256_file(template_zip)
        if template_hash_after != template_hash_before:
            raise BuildError("检测到原 LaTeX 模板 ZIP 在构建过程中发生变化，已停止。")

        print(f"      已生成：{project_dir}")
        if args.tex_only:
            report = write_build_report(build_dir, config, warnings, None)
            print("\n[OK] LaTeX 生成完成。")
            print(f"  构建报告：{report}")
            return 0

        pdf, latex_warnings = compile_pdf(project_dir, build_dir)
        all_warnings = warnings + latex_warnings
        print("[4/4] 完成并整理构建结果")
        report = write_build_report(build_dir, config, all_warnings, pdf)
        print(f"\n[OK] PDF 已生成：{pdf}")
        print(f"  构建报告：{report}")
        if latex_warnings:
            for item in latex_warnings:
                print(f"  [版面提醒] {item}")
        print("  正式提交前请按 docs/FINAL_CHECKLIST.md 人工核对最终 PDF。")
        return 0
    except BuildError as exc:
        eprint("\n[ERROR] 构建没有完成")
        eprint(textwrap.indent(str(exc), "  "))
        eprint("\n建议：先运行 `python tools/doctor.py` 检查环境，再查看 docs/TROUBLESHOOTING.md。")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
