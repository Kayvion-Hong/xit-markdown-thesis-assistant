# 从源码运行

本页面向愿意配置环境的开发者。希望直接写论文的 Windows 用户，请下载 Releases 完整包，阅读[新手图文指南](GETTING_STARTED.md)。源码仓库不提交整套运行时。

## 环境

- Python 3.10 或更高版本。完整包使用 3.12.7。
- Pandoc 3.11；请勿使用过旧的系统仓库版本。
- XeLaTeX、Biber 及原模板所需 TeX 宏包。
- 合法安装的原模板字体；替代字体会改变排版。
- Node.js 仅运行 JavaScript 测试时需要，日常写作不需要。

```powershell
git clone https://github.com/Kayvion-Hong/xit-markdown-thesis-assistant.git
cd xit-markdown-thesis-assistant
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r markdown/requirements.txt
.\.venv\Scripts\python.exe markdown/assistant/app.py
```

以上命令在 Windows PowerShell 中执行。先将 Pandoc、XeLaTeX、Biber 配置到 PATH。需要 AI 教学项目时，在最后一个命令末尾加 `--project ai`。页面只监听 `127.0.0.1`。

仓库里的 BAT 面向完整运行包，包含对随包工具的预检查；源码环境请直接执行 Python 启动命令。

## 命令行编译

激活已安装依赖的 Python 环境后：

```text
cd markdown
python xit.py doctor
python xit.py check
python xit.py tex
python xit.py pdf
python xit.py final-check
```

`tex` 生成临时 LaTeX 工程；`pdf` 调用完整编译流程；`final-check` 将占位字段等提醒作为问题处理。常规论文输出为 `markdown/build/thesis.pdf`。

## 运行测试

在仓库根目录执行：

```text
python scripts/run_tests.py
node markdown/tests/test_undo.cjs
node markdown/tests/test_drafts.cjs
```

Python 测试需要已安装 requirements 中的依赖；涉及转换的测试需要 Pandoc。自动测试不替代真实 PDF 的人工排版检查。

## 发布约定

源码、教程、原模板和教学素材进入 Git；运行时、个人论文备份、缓存和编译中间文件不进入 Git。完整 Windows ZIP 作为 Release 附件上传，同时提供 SHA256。

发布前检查 ZIP 未混入个人论文、浏览器草稿、私钥或其他凭据。MIT 只覆盖作者有权许可的内容；打包的 Python、Pandoc、TeX、字体和 PDF.js 保留各自许可和来源说明。
