"""Isolate native TeX tools from non-ASCII/long installation and build paths."""
from contextlib import contextmanager
from pathlib import Path
import os
import shutil
import tempfile


def ascii_temp_root():
    root = Path(tempfile.gettempdir())
    if str(root).isascii() and len(str(root)) < 100:
        return root
    import ctypes
    buffer = ctypes.create_unicode_buffer(32768)
    length = ctypes.windll.kernel32.GetShortPathNameW(str(root), buffer, len(buffer))
    if length and length < len(buffer) and buffer.value.isascii():
        return Path(buffer.value)
    raise RuntimeError('无法找到可用的英文临时目录。请把 TEMP/TMP 设置为可写的英文短路径后重启助手；论文文件不需要移动。')


@contextmanager
def native_workspace(project, tex_root):
    env = dict(os.environ)
    if os.name != 'nt' or not (tex_root / 'bin/windows/xelatex.exe').is_file():
        yield project, None, env
        return
    # Keep the alias as written: resolve() would turn it back into the Unicode target.
    with tempfile.TemporaryDirectory(prefix='xit-', dir=ascii_temp_root()) as temporary:
        base = Path(temporary)
        alias = base / 'tex'
        import _winapi
        _winapi.CreateJunction(str(tex_root.resolve()), str(alias))
        try:
            staged = base / 'project'
            shutil.copytree(project, staged)
            binary = alias / 'bin/windows'
            env['PATH'] = str(binary) + os.pathsep + env.get('PATH', '')
            env['TEXMFCNF'] = alias.as_posix() + ';' + (alias / 'texmf-dist/web2c').as_posix()
            # Pin format lookup to the bundled engine instead of rebuilding formats.
            env['TEXFORMATS'] = (alias / 'texmf-var/web2c/xetex').as_posix() + ';'
            env['TEMP'] = env['TMP'] = str(base.parent)
            try:
                yield staged, binary, env
            finally:
                # Preserve generated files for diagnostics and exported LaTeX projects.
                shutil.copytree(staged, project, dirs_exist_ok=True)
        finally:
            # Remove only this directory junction, never recurse into the TeX runtime.
            os.rmdir(alias)
