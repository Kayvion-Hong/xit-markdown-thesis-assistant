import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import source_map
import build


class SourceMapTests(unittest.TestCase):
    def test_pandoc_preserves_figure_and_code_locations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'example.md'
            source.write_text('# 标题\n\n![测试示意图](figures/example.png){#fig:test}\n\n'
                              '```python {#code:test caption="代码示例"}\nprint(42)\n```\n', encoding='utf-8')
            build.SOURCE_MAP['anchors'].clear()
            latex = build.pandoc_to_tex(source, root)
            entries = build.SOURCE_MAP['anchors']
            self.assertEqual([item['kind'] for item in entries], ['Header', 'Figure', 'CodeBlock'])
            for entry in entries[1:]:
                self.assertIn('\\hypertarget{' + entry['anchor'] + '}{}', latex)

    def test_repeated_paragraphs_keep_source_order(self):
        text = '# 标题\n\n相同的一段内容。\n\n另一段。\n\n相同的一段内容。\n'
        records = [{'anchor': str(i), 'kind': 'Para', 'text': t} for i, t in
                   enumerate(['标题', '相同的一段内容。', '另一段。', '相同的一段内容。'])]
        result = source_map.align(text, 'chapters/a.md', records)
        self.assertEqual([r['start'] for r in result], [1, 3, 5, 7])

    def test_markdown_constructs_and_multiline_block(self):
        text = '# 标题\n\n这是 **加粗** 和 [链接](https://example.com)。\n下一行文字。\n\n```python\nprint(42)\n```\n'
        records = [
            {'anchor': 'h', 'kind': 'Header', 'text': '标题'},
            {'anchor': 'p', 'kind': 'Para', 'text': '这是加粗和链接。 下一行文字。'},
            {'anchor': 'c', 'kind': 'CodeBlock', 'text': 'print(42)'},
        ]
        result = source_map.align(text, 'a.md', records)
        self.assertEqual([(r['start'], r['end']) for r in result], [(1, 1), (3, 4), (7, 7)])
        self.assertEqual(source_map.align('abc', 'a.md', [{'anchor':'x','kind':'Para','text':'不存在的内容'}]), [])

    def test_heading_destination_with_nested_title(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'source-map.json').write_text(json.dumps({'anchors': [
                {'kind':'Header','anchor':'test'}, {'kind':'Para','anchor':'p'}]}))
            (root / 'main.aux').write_text(r'\newlabel{test}{{1}{3}{A \textbf{bold} title}{chapter.1}{}}')
            source_map.resolve_headers(root)
            result = json.loads((root / 'source-map.json').read_text())
            self.assertEqual(result['anchors'][0]['destination'], 'chapter.1')
            self.assertNotIn('destination', result['anchors'][1])


if __name__ == '__main__':
    unittest.main()
