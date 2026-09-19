from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "build.py"
spec = importlib.util.spec_from_file_location("xit_markdown_build", MODULE_PATH)
build = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(build)


class BuildUnitTests(unittest.TestCase):
    def test_build_directory_cannot_erase_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "thesis"
            for target in (root, source, source / "build"):
                with self.assertRaises(build.BuildError):
                    build.validate_build_directory(target, source, root / "template.zip")
            build.validate_build_directory(root / "build", source, root / "template.zip")

    def test_code_label_survives_validation_but_body_does_not(self) -> None:
        text = '```python {#code:demo caption="示例"}\n# ignored\n[@fake]\n```\n'
        stripped = build.strip_fenced_code(text, preserve_attributes=True)
        self.assertIn('{#code:demo caption="示例"}', stripped)
        self.assertNotIn('@fake', stripped)
        self.assertEqual(build.find_level1_headings(text), [])

    def test_latex_escape_metadata(self) -> None:
        self.assertEqual(build.latex_escape("A&B_5%"), r"A\&B\_5\%")

    def test_patch_macro(self) -> None:
        source = r"\XITTitle{old}"
        patched = build.patch_macro(source, "XITTitle", "A&B")
        self.assertEqual(patched, r"\XITTitle{A\&B}")

    def test_patch_macro_ignores_commented_examples(self) -> None:
        source = '% Example: \\XITTitle{example}\n\\XITTitle{old} % title\n'
        patched = build.patch_macro(source, 'XITTitle', 'Actual title')
        self.assertIn('% Example: \\XITTitle{example}', patched)
        self.assertIn('\\XITTitle{Actual title} % title', patched)
        logo = '% Example: \\XITLogo{old.png}\n\\XITLogo{default.png}\n'
        self.assertIn('\\XITLogo{new.png}\n', build.patch_macro_raw(logo, 'XITLogo', 'new.png'))

    def test_patch_chapter_includes_can_disable_and_extend(self) -> None:
        source = "\n".join(
            [
                r"\include{chap/chapter1}",
                r"\include{chap/chapter2}",
                r"\include{chap/conclusion}",
            ]
        )
        disabled = build.patch_numbered_includes(source, 1)
        self.assertIn(r"% \include{chap/chapter2}", disabled)
        extended = build.patch_numbered_includes(source, 4)
        self.assertIn(r"\include{chap/chapter3}", extended)
        self.assertIn(r"\include{chap/chapter4}", extended)
        self.assertLess(
            extended.index(r"\include{chap/chapter4}"),
            extended.index(r"\include{chap/conclusion}"),
        )

    def test_safe_extract_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "bad.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("../escape.txt", "bad")
            with self.assertRaises(build.BuildError):
                build.safe_extract_zip(archive, root / "out")

    def test_pandoc_filter_emits_template_native_constructs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_dir = Path(tmp)
            md = source_dir / "chapter.md"
            md.write_text(
                "# 测试\n\n"
                "见[式](#eq:test)、[表](#tab:test)、[图](#fig:test)和[代码](#code:test)。\n\n"
                "![测试图片](figures/test.png){#fig:test width=80%}\n\n"
                "::: {#eq:test .equation}\n$$\nx=y+1\n$$\n:::\n\n"
                "| A | B |\n|---|---|\n| 1 | 2 |\n\n: 测试表 {#tab:test}\n\n"
                "```c {#code:test caption=\"测试代码\"}\nint x = 1;\n```\n\n"
                "## 本章小结\n\n```tex\n\\section{示例}\n```\n",
                encoding="utf-8",
            )
            tex = build.pandoc_to_tex(md, source_dir)
            self.assertIn(r"\begin{equation}", tex)
            self.assertIn(r"\label{eq:test}", tex)
            self.assertIn(r"\begin{table}[htbp]", tex)
            self.assertIn(r"\toprule", tex)
            self.assertIn(r"\label{tab:test}", tex)
            self.assertIn(r"\begin{lstlisting}", tex)
            self.assertIn("label={code:test}", tex)
            self.assertIn('language={[LaTeX]TeX}', tex)
            self.assertNotIn('ux672cux7ae0ux5c0fux7ed3', tex)
            self.assertIn(r"\eqref{eq:test}", tex)
            self.assertIn(r"\label{fig:test}", tex)
            self.assertIn(r"width=0.8\textwidth", tex)

    def test_missing_cross_reference_reports_location(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "chapters").mkdir()
            (root / "appendices").mkdir()
            (root / "chapter.md").write_text("# 测试\n\n见[图](#fig:missing)。\n", encoding="utf-8")
            for name in ("abstract-cn.md", "abstract-en.md", "conclusion.md", "acknowledgements.md"):
                (root / name).write_text("正文。\n", encoding="utf-8")
            (root / "references.bib").write_text("", encoding="utf-8")
            config = {
                "title": "题目", "english_title": "Title", "author": "张三",
                "student_id": "1", "major": "软件工程", "grade": "2023",
                "supervisor": "李老师", "date": "2027年5月",
                "keywords_cn": ["测试"], "keywords_en": ["test"],
                "abstract_cn": "abstract-cn.md", "abstract_en": "abstract-en.md",
                "bibliography": "references.bib", "chapters": ["chapter.md"],
                "conclusion": "conclusion.md", "acknowledgements": "acknowledgements.md",
                "appendices": [],
            }
            normalized = build.validate_config(config, root)
            with self.assertRaises(build.BuildError) as cm:
                build.validate_sources(normalized, root)
            self.assertIn("fig:missing", str(cm.exception))
            self.assertIn(":3", str(cm.exception))

    def test_metadata_placeholders_are_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "chapter.md").write_text("# 测试\n\n正文。\n", encoding="utf-8")
            for name in ("abstract-cn.md", "abstract-en.md", "conclusion.md", "acknowledgements.md"):
                (root / name).write_text("正文。\n", encoding="utf-8")
            (root / "references.bib").write_text("", encoding="utf-8")
            config = {
                "title": "题目", "english_title": "Title", "author": "请输入姓名",
                "student_id": "请输入学号", "major": "软件工程", "grade": "2023",
                "supervisor": "李老师", "date": "2027年5月",
                "keywords_cn": ["测试"], "keywords_en": ["test"],
                "abstract_cn": "abstract-cn.md", "abstract_en": "abstract-en.md",
                "bibliography": "references.bib", "chapters": ["chapter.md"],
                "conclusion": "conclusion.md", "acknowledgements": "acknowledgements.md",
                "appendices": [],
            }
            normalized = build.validate_config(config, root)
            warnings = build.validate_sources(normalized, root)
            self.assertTrue(any("metadata.yaml" in item for item in warnings))


if __name__ == "__main__":
    unittest.main()
