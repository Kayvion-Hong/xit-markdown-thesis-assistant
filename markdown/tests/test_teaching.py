import unittest
from pathlib import Path
from unittest.mock import patch
import test_assistant

app = test_assistant.assistant


class TeachingTests(unittest.TestCase):
    def test_project_selection_has_independent_source_and_output(self):
        with patch.object(app, 'THESIS_DIR'), patch.object(app, 'METADATA_PATH'), patch.object(app, 'BUILD_PDF'), patch.object(app, 'PROJECT_MODE'):
            app.select_project('ai')
            self.assertEqual(app.THESIS_DIR, app.MARKDOWN_ROOT / 'examples/ai/thesis')
            self.assertEqual(app.BUILD_PDF.parent.name, 'build-ai')
            self.assertEqual(app.writing_issues(), [])
            self.assertEqual(len(app.load_metadata()['chapters']), 5)
            app.select_project('thesis')
            self.assertEqual(app.THESIS_DIR, app.MARKDOWN_ROOT / 'thesis')
            self.assertEqual(app.BUILD_PDF.parent.name, 'build')
            with self.assertRaises(app.AssistantError):
                app.select_project('../outside')
