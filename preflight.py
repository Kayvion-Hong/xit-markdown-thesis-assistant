"""Read-only checks before the UI starts, no administrator privileges required."""
from pathlib import Path
import os
import sys
import tempfile

root=Path(__file__).resolve().parent
errors=[]
if os.name=='nt' and sys.getwindowsversion().build<10240:
    errors.append('This package requires Windows 10/11 x64. Windows 11 ARM64 may use x64 emulation; it is not hardware-verified.')
if sys.maxsize<=2**32:
    errors.append('This package requires a 64-bit runtime.')
for relative in ('runtime/pandoc/pandoc.exe','runtime/TinyTeX/bin/windows/xelatex.exe','runtime/TinyTeX/bin/windows/biber.exe','markdown/assistant/app.py'):
    if not (root/relative).is_file(): errors.append('Missing: '+relative+'; extract the FULL ZIP. Check security quarantine history if it disappeared.')
try:
    with tempfile.NamedTemporaryFile(dir=root,prefix='.xit-start-test-'):pass
except OSError:
    errors.append('This folder is not writable. Extract to a folder you own, such as D:\\XIT. Contact your administrator on managed computers.')
if len(str(root))>70:
    print('NOTE: Long extraction path. Use D:\\XIT or C:\\XIT before starting new work. Restore and save browser drafts before moving existing projects.')
for message in errors: print('ERROR: '+message)
if errors: print('Do not disable antivirus or bypass school computer policies. See the compatibility guide in the ZIP.')
raise SystemExit(1 if errors else 0)
