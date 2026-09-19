# 厦门工学院本科毕业论文 Markdown 写作助手

> **Windows 新手请返回项目根目录，双击 `启动论文助手.bat`。**
>
> 浏览器页面可以填写资料、编辑章节、插入图片、检查并生成 PDF。下面的命令行方式供高级用户和排错使用。

## Windows 图形界面

完整解压项目后，双击根目录的：

```text
启动论文助手.bat
```

浏览器会自动打开。左侧只有四个主要步骤：

1. 首页确认环境状态；
2. 在表单中填写题目、姓名、学号等；
3. 在统一编辑器中切换摘要、章节、总结和谢辞；
4. 点击检查或生成 PDF。

正文自动保存到 `thesis/`，PDF 生成到 `build/thesis.pdf`。使用期间保留启动时出现的黑色窗口；在页面右上角点击“关闭助手”即可结束。

## 命令行方式（高级用户）

### 使用前准备

本目录是原 LaTeX 模板的 Markdown 写作入口。请保留以下结构：

```text
项目目录/
├── 厦门工学院毕业设计论文模板.zip
└── markdown/
    ├── xit.py
    └── thesis/
```

0.4.0 Windows 完整包已内置 Python、Python 依赖、Pandoc 与 TinyTeX，不需要手动安装这些程序。Windows 字体仍由系统提供。请优先阅读根目录[新手先看](../新手先看.md)。下方命令行安装说明适用于源码版及其他系统。

### Windows 旧版批处理入口

按顺序双击：

1. `00-first-check.bat` —— 检查电脑是否具备需要的程序；
2. `01-fill-info.bat` —— 用向导填写姓名、学号、题目等；
3. 修改 `thesis/chapters/*.md` —— 写正文；
4. `02-check-thesis.bat` —— 检查图片、引用、章节结构等；
5. `03-build-pdf.bat` —— 生成并打开 `build/thesis.pdf`。

定稿前再双击 `04-final-check.bat`。

### macOS / Linux / 终端用户

```bash
python3 tools/doctor.py
python3 xit.py setup
python3 xit.py check
python3 xit.py pdf
```

生成结果：

```text
build/thesis.pdf
```

## 你真正需要修改的文件

```text
thesis/
├── metadata.yaml           姓名、学号、题目、专业、关键词、章节顺序
├── abstract-cn.md          中文摘要正文
├── abstract-en.md          英文摘要正文
├── chapters/               正文章节
├── figures/                自己的图片
├── references.bib          参考文献数据库
├── conclusion.md           总结
├── acknowledgements.md     谢辞
└── appendices/             附录
```

一般**不要修改**：

```text
tools/
filters/
build/
```

也不要修改仓库根目录原来的 LaTeX 模板 ZIP。构建程序只会复制它到 `build/` 后再生成临时 `.tex` 文件。

## 最常见的 Markdown 写法

```markdown
# 绪论

## 研究背景

这里写正文。两段之间空一行。

已有研究指出…… [@zhang2026]。
```

图片：

```markdown
系统总体架构如[图](#fig:system)所示。

![系统总体架构](figures/system.png){#fig:system width=90%}
```

编号公式：

```markdown
::: {#eq:model .equation}
$$
y = ax + b
$$
:::

由[式](#eq:model)可知……
```

三线表：

```markdown
| 指标 | 测试值 | 目标值 |
| --- | --- | --- |
| 准确率 | 96.5% | 95% |

: 性能测试结果 {#tab:result}
```

代码：

````markdown
```python {#code:demo caption="示例代码"}
print("hello")
```
````

更多例子见 [写作速查表](docs/MARKDOWN_CHEATSHEET.md)。

## 为什么最终格式仍然可靠

两种写法共享同一套 LaTeX 排版后端：

```text
直接写 LaTeX ───────────────────┐
                                ├─> 原 xitthesis.cls -> XeLaTeX + Biber -> PDF
Markdown -> Pandoc -> 临时 .tex ┘
```

因此 Markdown 版不会重新定义封面、页边距、字体、章节标题、总结、谢辞、附录或参考文献格式。

## 出错时先做什么

先运行：

```bash
python3 tools/doctor.py
```

再运行：

```bash
python3 xit.py check
```

脚本会尽量指出**文件名 + 行号 + 修复方向**，例如：

```text
chapters/02-design.md:37 引用了不存在的标签 #fig:system
```

如果 PDF 编译失败，不要连续重复点击构建；优先处理屏幕显示的第一条关键错误。详细说明见 [故障排查](docs/TROUBLESHOOTING.md)。

## 定稿前

```bash
python3 xit.py final-check
python3 xit.py pdf
```

然后人工按 [最终检查清单](docs/FINAL_CHECKLIST.md) 检查 PDF。

## 详细文档

- [新手完整教程](docs/BEGINNER_GUIDE.md)
- [Markdown 写作速查](docs/MARKDOWN_CHEATSHEET.md)
- [常见错误和解决办法](docs/TROUBLESHOOTING.md)
- [定稿检查清单](docs/FINAL_CHECKLIST.md)
- [Git 与 AI 使用建议](docs/GIT_AI_WORKFLOW.md)

## 高级用户

原入口仍然保留：

```bash
python tools/build.py --validate-only
python tools/build.py --tex-only
python tools/build.py
make validate
make tex
make pdf
```

复杂宽表、特殊数学环境等少数情况允许局部使用 Pandoc raw LaTeX。不要为了 5% 的特殊排版把整篇论文改回手写 LaTeX。
