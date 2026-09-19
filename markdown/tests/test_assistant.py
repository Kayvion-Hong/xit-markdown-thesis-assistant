from __future__ import annotations

import base64
import importlib.util
import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

import yaml

MODULE_PATH = Path(__file__).resolve().parents[1] / "assistant" / "app.py"
spec = importlib.util.spec_from_file_location("xit_thesis_assistant", MODULE_PATH)
assistant = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = assistant
spec.loader.exec_module(assistant)


class AssistantTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, Path]:
        thesis = root / "thesis"
        (thesis / "chapters").mkdir(parents=True)
        metadata = thesis / "metadata.yaml"
        metadata.write_text(
            yaml.safe_dump(
                {
                    "title": "旧题目", "author": "请输入姓名",
                    "keywords_cn": ["旧关键词"], "keywords_en": ["old"],
                    "abstract_cn": "abstract-cn.md", "abstract_en": "abstract-en.md",
                    "chapters": ["chapters/01.md"], "conclusion": "conclusion.md",
                    "acknowledgements": "acknowledgements.md", "bibliography": "references.bib",
                    "appendices": [], "custom_setting": "must-survive",
                },
                allow_unicode=True, sort_keys=False,
            ),
            encoding="utf-8",
        )
        for relative in ("abstract-cn.md", "abstract-en.md", "chapters/01.md", "conclusion.md", "acknowledgements.md", "references.bib"):
            path = thesis / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("原内容\n", encoding="utf-8")
        return thesis, metadata

    def test_metadata_form_preserves_structural_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            thesis, metadata = self.fixture(Path(tmp))
            with patch.object(assistant, "THESIS_DIR", thesis), patch.object(assistant, "METADATA_PATH", metadata):
                assistant.save_metadata({"title": "新题目", "keywords_cn": "人工智能，排版"})
                saved = assistant.load_metadata()
            self.assertEqual(saved["title"], "新题目")
            self.assertEqual(saved["keywords_cn"], ["人工智能", "排版"])
            self.assertEqual(saved["custom_setting"], "must-survive")
            self.assertEqual(saved["chapters"], ["chapters/01.md"])

    def test_editor_allows_only_configured_thesis_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            thesis, metadata = self.fixture(Path(tmp))
            with patch.object(assistant, "THESIS_DIR", thesis), patch.object(assistant, "METADATA_PATH", metadata):
                assistant.save_content("chapters/01.md", "# 新章节\n")
                self.assertEqual(assistant.read_content("chapters/01.md"), "# 新章节\n")
                with self.assertRaises(assistant.AssistantError):
                    assistant.save_content("../README.md", "bad")

    def test_image_upload_sanitizes_name_and_avoids_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            thesis, metadata = self.fixture(Path(tmp))
            payload = base64.b64encode(b"small-image-fixture").decode("ascii")
            with patch.object(assistant, "THESIS_DIR", thesis), patch.object(assistant, "METADATA_PATH", metadata):
                first = assistant.save_image("figure.png", payload)
                second = assistant.save_image("figure.png", payload)
                with self.assertRaises(assistant.AssistantError):
                    assistant.save_image("../escape.png", payload)
                with self.assertRaises(assistant.AssistantError):
                    assistant.save_image("vector.svg", payload)
            self.assertEqual(first, "figures/figure.png")
            self.assertEqual(second, "figures/figure-2.png")


if __name__ == "__main__":
    unittest.main()
