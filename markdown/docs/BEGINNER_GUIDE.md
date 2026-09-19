# 新手完整教程

> 0.4.0 Windows 完整包已内置 Python、Pandoc 和 TinyTeX，直接运行根目录 BAT。优先阅读[新版入门](../../新手先看.md)。本页后面的手动环境安装步骤仅适用于源码版、其他系统或运行环境被移除的情况。

这份教程假设你以前没有使用过 LaTeX，也不要求你理解 Pandoc、Biber 或 LaTeX 宏包。

## 最简单的使用方式

Windows 用户先返回项目根目录，双击：

```text
启动论文助手.bat
```

浏览器打开后，按左侧四步操作即可。论文助手会代替你编辑 `metadata.yaml`、寻找章节文件和输入编译命令。

- “填写资料”：用普通表单填写封面信息；
- “写论文”：切换摘要、章节、总结、谢辞和附录；
- 编辑器上方按钮：快捷插入公式、表格、引用、代码和图片；
- “检查与导出”：检查论文、生成 PDF 或进行定稿检查。

生成结果可以直接点击页面中的“打开生成的 PDF”。使用期间不要关闭启动时出现的黑色窗口。

下面的目录和命令说明主要用于安装环境、排错和高级操作。日常写作可以只使用论文助手页面。

## 1. 先理解三个目录

你日常主要接触：

```text
thesis/        你的论文源文件，应该提交 Git
build/         自动生成结果，可以删除，不需要提交 Git
tools/         构建程序，普通写作不要修改
```

最重要的原则：**只把论文内容写进 `thesis/`。**

## 2. 第一次检查电脑

Windows 双击：

```text
00-first-check.bat
```

其他系统：

```bash
python3 tools/doctor.py
```

你会看到：

```text
[OK] Python
[OK] PyYAML
[OK] 原 LaTeX 模板 ZIP
[OK] pandoc
[OK] xelatex
[OK] biber
```

如果 PyYAML 缺失：

```bash
python -m pip install -r requirements.txt
```

Windows 完整包已附带 Pandoc，正常应显示“随包内置”。如果仍提示缺失，先检查是否完整解压，以及根目录 `runtime/pandoc/pandoc.exe` 是否存在；不要只复制启动脚本或 `markdown/` 文件夹。

### 安装编译环境

1. 安装 Python 3.10 或更高版本；Windows 安装时勾选加入 PATH。
2. 在 `markdown/` 目录执行 `python -m pip install -r requirements.txt`。
3. 使用 Windows 完整包时跳过 Pandoc 安装。其他系统或不含 `runtime/` 的源码包，按 [Pandoc 官方安装说明](https://pandoc.org/installing.html)安装 Pandoc 3.1 或更高版本。附带的 Windows 程序不能在 macOS/Linux 上直接运行。
4. 安装 TeX Live（macOS 可使用 MacTeX），应包含 XeLaTeX、Biber、中文支持、`biblatex-gb7714-2015`、`listings`、TikZ 和 `siunitx`。精简 TeX 安装可能需要继续补充宏包。
5. 运行 `python xit.py doctor` 检查命令是否可用，然后用 `python xit.py pdf` 完成实际编译。环境自检不能替代实际编译验证。

Linux 使用原模板的回退字体时，还需要 Liberation Serif、Noto Sans Mono 和 TeX Live 的 Fandol 字体。Windows 本次验证使用系统宋体、黑体与 Times New Roman；不同系统字体可能造成细微分页差异。

### 使用 LoongTeX / Overleaf

在线 LaTeX 项目不能直接把这些 Markdown 文件当作 `main.tex` 编译。先在装有 Python、PyYAML 和 Pandoc 的电脑上运行 `python xit.py tex`，把生成的 `build/project/` **里面的全部文件**打包为 ZIP，再导入 LoongTeX 或 Overleaf。选择 XeLaTeX，主文件选择 `main.tex`；文献使用 Biber。

初学者可以优先尝试 LoongTeX，也可根据自己的访问体验选择 Overleaf。每次修改 Markdown 后，需要重新生成并上传 LaTeX 工程。不要只修改临时工程后忘记同步论文源文件。

如果 XeLaTeX 或 Biber 缺失，你仍然可以检查 Markdown、生成 `.tex`，但不能在本机得到最终 PDF。完整 PDF 构建需要一个带 XeLaTeX 和 Biber 的 TeX 环境，例如 TeX Live；macOS 通常使用 MacTeX。

## 3. 先填写论文基本信息

不熟悉 YAML 时直接运行：

```bash
python xit.py setup
```

Windows 也可以双击 `01-fill-info.bat`。向导会询问题目、姓名、学号、专业、年级、指导教师、日期和关键词，并保留一份 `metadata.yaml.bak` 初始备份。

如果你愿意手工编辑，也可以直接打开：

```text
thesis/metadata.yaml
```

只替换冒号后面的内容，不要随意改左侧字段名：

```yaml
title: 你的中文论文题目
english_title: Your English Thesis Title
author: 张三
student_id: "2023000000"
major: 软件工程
grade: "2023"
supervisor: 李老师
date: 2027年5月
```

学号、年级建议保留引号，以免 YAML 把它们当数字处理。

原 LaTeX 模板的封面题目栏按单行排版。填写较长题目后务必打开 PDF 检查是否与“题目”标签重叠，不能只看编译成功提示；需要多行题目时，应按学院要求调整原模板的封面排版。

关键词：

```yaml
keywords_cn:
  - 深度学习
  - 图像识别
  - 嵌入式系统
```

不要手工写成 `关键词：……`，LaTeX 模板会自动排版。

## 4. 写第一章

打开：

```text
thesis/chapters/01-introduction.md
```

每章必须只有一个 `#` 一级标题：

```markdown
# 绪论

## 研究背景与意义

正文第一段。

正文第二段。

## 国内外研究现状

### 国外研究现状

正文……
```

不要手写：

```text
第1章
1.1
1.1.1
```

这些编号由原 LaTeX 模板自动生成。

## 5. 写完一小段就检查一次

Windows：

```text
02-check-thesis.bat
```

终端：

```bash
python xit.py check
```

建议在下面这些操作后立即检查：

- 新增章节；
- 新增图片；
- 新增一个参考文献；
- 新增公式标签；
- 修改 `metadata.yaml`。

这样错误通常只来自刚刚修改的几行。

## 6. 生成 PDF

Windows：

```text
03-build-pdf.bat
```

终端：

```bash
python xit.py pdf
```

成功后：

```text
build/thesis.pdf
```

同时会生成：

```text
build/build-report.txt
build/logs/
build/project/
```

普通用户一般只需要看 `thesis.pdf` 和 `build-report.txt`。

`build/project/` 是自动生成的 LaTeX 临时工程，用于排错和高级检查，不要在那里正式写论文，因为下一次构建可能覆盖它。

## 7. 图片怎么放

把自己的图片放进：

```text
thesis/figures/
```

建议文件名：

```text
system_architecture.png
experiment_result_01.pdf
workflow.jpg
```

正文：

```markdown
系统总体架构如[图](#fig:architecture)所示。

![系统总体架构](figures/system_architecture.png){#fig:architecture width=90%}
```

标签建议：

```text
fig:xxx   图片
tab:xxx   表格
eq:xxx    公式
code:xxx  代码
```

标签不要重复，也不要手工写“图 2-1”。

## 8. 参考文献怎么写

文献数据库：

```text
thesis/references.bib
```

正文引用：

```markdown
已有研究采用了类似方法 [@zhang2026]。
```

这里的 `zhang2026` 必须和 `references.bib` 中的 BibTeX key 完全一致。

不要在正文手工写 `[1]`，编号由 Biber 和原 LaTeX 模板生成。

## 9. 摘要、总结、谢辞为什么不能写标题

这些文件：

```text
abstract-cn.md
abstract-en.md
conclusion.md
acknowledgements.md
appendices/*.md
```

只写正文，不要加 `# 摘要`、`# 总结`、`# 谢辞`。

原因是原 `xitthesis.cls` 已经负责这些特殊标题和目录项。构建程序会生成模板原生的 `cnabstract`、`XITConclusion`、`XITAcknowledgement`、`XITAppendix` 等结构。

## 10. 定稿前严格检查

Windows：

```text
04-final-check.bat
```

终端：

```bash
python xit.py final-check
```

普通 `check` 允许“请输入姓名”等占位内容作为提醒，方便你先测试流程；`final-check` 会把这些提醒当作未通过。

严格检查通过后再重新：

```bash
python xit.py pdf
```

最后仍然必须人工打开 PDF 检查分页、字体、图片清晰度和学校当年要求。

## 11. 什么时候需要 LaTeX

绝大多数正文、标题、图片、普通表格、公式、代码和引用不需要手写 LaTeX。

只有特殊宽表、复杂合并单元格、特殊数学环境或学院临时格式要求可能需要局部 raw LaTeX。遇到这种情况再查 LaTeX，不需要在开始写论文前先学完整的 LaTeX。
