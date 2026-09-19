#!/usr/bin/env python3
"""Interactive metadata editor for first-time users."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit(
        "缺少 PyYAML。请先执行：python -m pip install -r requirements.txt"
    )

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "thesis" / "metadata.yaml"
BACKUP = ROOT / "thesis" / "metadata.yaml.bak"

FIELDS = [
    ("title", "中文论文题目"),
    ("english_title", "英文论文题目"),
    ("author", "姓名"),
    ("student_id", "学号"),
    ("major", "专业"),
    ("grade", "年级（如 2023）"),
    ("supervisor", "指导教师"),
    ("date", "日期（如 2027年5月）"),
]


def ask(label: str, current: str) -> str:
    shown = current if current else "未填写"
    value = input(f"{label} [{shown}]：").strip()
    return value if value else current


def parse_keywords(value: str, current: list[str]) -> list[str]:
    value = value.strip()
    if not value:
        return current
    # Chinese/English commas and semicolons are all accepted for novice input.
    for sep in ("，", "；", ";"):
        value = value.replace(sep, ",")
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> int:
    if not PATH.is_file():
        print(f"找不到：{PATH}")
        return 2
    data = yaml.safe_load(PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        print("metadata.yaml 格式不正确，无法使用向导。")
        return 2

    print("厦门工学院毕业论文 - 基本信息填写向导")
    print("=" * 42)
    print("直接按 Enter 会保留当前值。章节顺序等高级设置不会被修改。\n")

    for key, label in FIELDS:
        current = str(data.get(key, "") or "")
        data[key] = ask(label, current)

    current_cn = [str(x) for x in data.get("keywords_cn", []) or []]
    current_en = [str(x) for x in data.get("keywords_en", []) or []]
    print("\n关键词用逗号分隔。直接按 Enter 保留当前关键词。")
    cn = input(f"中文关键词 [{', '.join(current_cn)}]：")
    en = input(f"英文关键词 [{', '.join(current_en)}]：")
    data["keywords_cn"] = parse_keywords(cn, current_cn)
    data["keywords_en"] = parse_keywords(en, current_en)

    print("\n即将写入 metadata.yaml：")
    for key, label in FIELDS:
        print(f"- {label}：{data.get(key, '')}")
    print(f"- 中文关键词：{'；'.join(data.get('keywords_cn', []))}")
    print(f"- 英文关键词：{'; '.join(data.get('keywords_en', []))}")

    answer = input("\n确认保存？[Y/n]：").strip().lower()
    if answer not in {"", "y", "yes"}:
        print("已取消，没有修改文件。")
        return 0

    if not BACKUP.exists():
        shutil.copy2(PATH, BACKUP)
        print(f"已保存初始备份：{BACKUP.name}")

    PATH.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000),
        encoding="utf-8",
    )
    print(f"已更新：{PATH}")
    print("下一步：python xit.py check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
