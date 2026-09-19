"""Portable Windows diagnostics and narrowly scoped TeX package installation."""
from pathlib import Path
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def diagnose():
    messages = [f'系统：{platform.platform()}；架构：{os.environ.get("PROCESSOR_ARCHITEW6432", platform.machine())}',
                f'项目目录：{ROOT}']
    if os.name == 'nt':
        if sys.getwindowsversion().build < 10240:
            messages.append('不支持此旧版 Windows。请使用 Windows 10/11 x64；ARM 仅可在 Windows 11 上尝试 x64 仿真。')
        if 'ARM' in os.environ.get('PROCESSOR_ARCHITEW6432', platform.machine()).upper():
            messages.append('ARM 设备：当前是 x64 仿真运行，不等于已验证 ARM 原生兼容。请生成示例 PDF 检查。')
    try:
        with tempfile.NamedTemporaryFile(dir=ROOT, prefix='.xit-write-test-'):
            pass
        messages.append('目录写入：正常，不需要管理员权限。')
    except OSError as error:
        messages.append(f'目录不能写入：{error}。请完整解压到本人可写目录，例如 D:\\XIT。')
    longest = max((len(str(path)) for path in (ROOT/'runtime').rglob('*')), default=len(str(ROOT)))
    messages.append(f'随包文件最长路径：{longest} 字符。')
    if longest > 240:
        messages.append('路径偏长：建议在第一次写作前解压到 D:\\XIT 或 C:\\XIT；已有草稿先恢复保存再搬迁。')
    for relative in ('runtime/python/python.exe','runtime/pandoc/pandoc.exe','runtime/TinyTeX/bin/windows/xelatex.exe','runtime/TinyTeX/bin/windows/biber.exe'):
        path=ROOT/relative
        messages.append(('存在：' if path.is_file() else '缺失：')+relative)
    messages.append('如程序被拦截：查看 Windows 安全中心保护历史或联系机房管理员；不要关闭安全软件或自行绕过组织策略。')
    free=shutil.disk_usage(ROOT).free//(1024**2)
    messages.append(f'所在磁盘剩余空间：{free} MB；建议至少留出 2 GB 供编译和备份。')
    return '\n'.join(messages)


def install_package(name):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}',name):
        raise ValueError('请输入一个 TeX Live 宏包名称（小写英文、数字、短横线），不是 .sty 文件名或命令。')
    manager=ROOT/'runtime/TinyTeX/bin/windows/tlmgr.bat'
    if not manager.is_file(): raise ValueError('随包 tlmgr 缺失，请重新完整解压。')
    # Only this fixed command and a validated package name reach cmd.exe.
    command=[os.environ.get('COMSPEC','cmd.exe'),'/d','/c',str(manager),'install',name]
    result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
    return {'ok':result.returncode==0,'output':(result.stdout+'\n'+result.stderr).strip()}


if __name__=='__main__':
    print(diagnose())
