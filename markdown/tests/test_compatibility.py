import sys
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import compatibility,portable_fonts


class CompatibilityTests(unittest.TestCase):
    def test_install_rejects_commands_and_filenames(self):
        with patch.object(compatibility.subprocess,'run') as run:
            for value in ('x & whoami','../x','--all','abc.sty','pkg other','$(cmd)',''):
                with self.assertRaises(ValueError):compatibility.install_package(value)
            run.assert_not_called()

    def test_install_is_scoped(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(compatibility, 'ROOT', Path(directory)), patch.object(compatibility.subprocess,'run') as run:
            manager = Path(directory) / 'runtime/TinyTeX/bin/windows/tlmgr.bat'
            manager.parent.mkdir(parents=True)
            manager.touch()
            run.return_value.returncode=0;run.return_value.stdout='installed';run.return_value.stderr=''
            self.assertTrue(compatibility.install_package('siunitx')['ok'])
            command=run.call_args.args[0]
            self.assertEqual(command[-2:],['install','siunitx'])
            self.assertIn('runtime',command[-3])

    def test_fonts_require_all_variants(self):
        with patch.object(portable_fonts.Path,'is_file',return_value=False):
            self.assertFalse(portable_fonts.exact_fonts_available())
