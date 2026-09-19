#!/usr/bin/env python3
"""Beginner-friendly environment check for the Markdown thesis frontend.

This script intentionally uses only the Python standard library so it can run before
PyYAML or other project dependencies are installed.
"""
from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
TEMPLATE = REPO_ROOT / "厦门工学院毕业设计论文模板.zip"


def first_line(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        return (result.stdout.splitlines() or [""])[0].strip()
    except Exception:
        return ""


def mark(ok: bool) -> str:
    return "[OK]" if ok else "[缺少]"


def main() -> int:
    print("厦门工学院 Markdown 论文环境检查")
    print("=" * 38)
    print(f"系统：{platform.system()} {platform.release()}")
    print()

    py_ok = sys.version_info >= (3, 10)
    print(f"{mark(py_ok)} Python {platform.python_version()}（需要 3.10+）")

    yaml_ok = importlib.util.find_spec("yaml") is not None
    print(f"{mark(yaml_ok)} PyYAML（读取 metadata.yaml）")
    if not yaml_ok:
        print("       安装：python -m pip install -r requirements.txt")

    template_ok = TEMPLATE.is_file()
    print(f"{mark(template_ok)} 原 LaTeX 模板 ZIP")
    if template_ok:
        print(f"       {TEMPLATE}")
    else:
        print("       应位于仓库根目录，并与 markdown/ 目录同级。")

    programs: dict[str, tuple[bool, str]] = {}
    for name, args, purpose in (
        ("pandoc", ["pandoc", "--version"], "Markdown → LaTeX"),
        ("xelatex", ["xelatex", "--version"], "生成 PDF"),
        ("biber", ["biber", "--version"], "参考文献"),
    ):
        override = os.environ.get(f"XIT_{name.upper()}")
        exe = override if override and Path(override).is_file() else shutil.which(name)
        bundled = REPO_ROOT / "runtime" / "pandoc" / "pandoc.exe"
        if name == "pandoc" and os.name == "nt" and bundled.is_file() and not override:
            exe = str(bundled)
        ok = exe is not None
        version = first_line([exe, *args[1:]]) if ok else ""
        programs[name] = (ok, version)
        suffix = f"；{version}" if version else ""
        print(f"{mark(ok)} {name}（{purpose}）{suffix}")

    print()
    base_ok = py_ok and yaml_ok and template_ok
    tex_ok = base_ok and programs["pandoc"][0]
    pdf_ok = tex_ok and programs["xelatex"][0] and programs["biber"][0]

    print("可用能力：")
    print(f"  {mark(base_ok)} 检查 Markdown / metadata")
    print(f"  {mark(tex_ok)} 生成 LaTeX")
    print(f"  {mark(pdf_ok)} 直接生成最终 PDF")
    print()

    if pdf_ok:
        print("环境已准备好。第一次使用建议下一步：python xit.py setup")
        return 0

    print("当前环境还没有完全准备好。")
    if not yaml_ok:
        print("1. 先执行：python -m pip install -r requirements.txt")
    if not programs["pandoc"][0]:
        print("2. 安装 Pandoc。安装方法见 docs/BEGINNER_GUIDE.md。")
    if not programs["xelatex"][0] or not programs["biber"][0]:
        print("3. 若要本地生成 PDF，请安装带 XeLaTeX 和 Biber 的 TeX Live / MacTeX。")
        print("   如果只想先写论文，可以先完成 Markdown，或使用学校现有在线 LaTeX 环境生成 PDF。")
    if not template_ok:
        print("4. 确认原模板 ZIP 仍保留在仓库根目录，文件名不要改。")
    print("\n详细说明：docs/BEGINNER_GUIDE.md")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
