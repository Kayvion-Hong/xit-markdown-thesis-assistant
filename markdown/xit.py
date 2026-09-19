#!/usr/bin/env python3
"""Small beginner-facing command wrapper.

Examples:
    python xit.py doctor
    python xit.py check
    python xit.py tex
    python xit.py pdf
    python xit.py final-check
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable

COMMANDS = {
    "doctor": [PYTHON, str(ROOT / "tools" / "doctor.py")],
    "setup": [PYTHON, str(ROOT / "tools" / "setup_metadata.py")],
    "check": [PYTHON, str(ROOT / "tools" / "build.py"), "--validate-only"],
    "tex": [PYTHON, str(ROOT / "tools" / "build.py"), "--tex-only"],
    "pdf": [PYTHON, str(ROOT / "tools" / "build.py")],
    "final-check": [PYTHON, str(ROOT / "tools" / "build.py"), "--validate-only", "--strict"],
}


def help_text() -> str:
    return """厦门工学院 Markdown 论文助手

最常用的 3 个命令：
  python xit.py doctor       第一次使用：检查电脑环境
  python xit.py setup        第一次使用：交互填写姓名、学号、题目等
  python xit.py check        写作过程中：检查论文是否有明显错误
  python xit.py pdf          生成 build/thesis.pdf

定稿前：
  python xit.py final-check  把占位文字等提醒也视为错误

高级用法：
  python xit.py tex          只生成 LaTeX，不生成 PDF

写论文时主要只修改 thesis/ 目录。详细说明见 docs/BEGINNER_GUIDE.md。
"""


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] in {"-h", "--help", "help"}:
        print(help_text())
        return 0 if len(sys.argv) == 2 else 1
    command = sys.argv[1]
    if command not in COMMANDS:
        print(f"未知命令：{command}\n")
        print(help_text())
        return 2
    result = subprocess.run(COMMANDS[command], cwd=ROOT)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
