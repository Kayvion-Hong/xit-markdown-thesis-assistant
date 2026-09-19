"""Run the source test suite with the same import roots as the application."""
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[1] / "markdown"
for directory in ("tests", "tools", "assistant"):
    sys.path.insert(0, str(root / directory))
suite = unittest.defaultTestLoader.discover(str(root / "tests"))
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
