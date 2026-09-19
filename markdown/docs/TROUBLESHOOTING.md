# 常见错误和解决办法

处理错误时只遵循一个原则：**先修复屏幕上最前面的实质错误，再重新构建。** 后面的错误可能只是连锁反应。

## `找不到原 LaTeX 模板 ZIP`

确认目录结构：

```text
仓库根目录/
├── 厦门工学院毕业设计论文模板.zip
└── markdown/
```

不要改 ZIP 文件名。

## `缺少 Pandoc`

先运行：

```bash
python tools/doctor.py
```

Pandoc 缺失时可以继续写 Markdown，但不能生成 `.tex` 或 PDF。

## `缺少 XeLaTeX` / `缺少 Biber`

说明 Markdown 检查和 LaTeX 生成仍可能可用，但本机不能完成 PDF。安装带 XeLaTeX/Biber 的 TeX 环境后再次运行环境检查。

## `必须且只能有一个一级标题`

章节文件应该：

```markdown
# 绪论

## 研究背景
```

常见错误：

```markdown
# 绪论
# 国内外研究现状
```

第二个应改成 `##`。

## `摘要/总结/谢辞不要写一级标题`

删除：

```markdown
# 总结
```

只保留正文，因为标题由原模板生成。

## `找不到图片`

错误会给出文件和行号。确认：

1. 图片真的在 `thesis/figures/`；
2. Markdown 路径从 `thesis/` 开始写，例如 `figures/system.png`；
3. 大小写完全一致；
4. 不要直接引用网络 URL。

## `引用了不存在的标签`

例如：

```text
chapters/02-design.md:37 引用了不存在的标签 #fig:system
```

正文：

```markdown
如[图](#fig:system)所示。
```

图片必须有完全相同的：

```markdown
{#fig:system}
```

## `文献键不存在`

正文：

```markdown
[@zhang2026]
```

则 `references.bib` 必须有：

```bibtex
@article{zhang2026,
  ...
}
```

注意拼写和大小写。

## PDF 能生成，但出现 `Overfull \hbox`

这通常表示某些内容可能越过正文宽度。优先检查：

- 很长的网址或英文单词；
- 特别宽的表格；
- 很长的行内公式；
- 代码行。

它不一定阻止 PDF 生成，但定稿前必须人工检查对应页面。

## 为什么修改 `build/project/*.tex` 后又没了

`build/project/` 是自动生成目录。下一次构建会重新创建它。

正式内容只能改：

```text
thesis/
```

## 为什么 PDF 没有变化

确认打开的是：

```text
markdown/build/thesis.pdf
```

不是原模板 ZIP 中旧的 `preview.pdf` 或 `main.pdf`。

## 还是不知道原因

依次运行：

```bash
python tools/doctor.py
python xit.py check
python xit.py tex
python xit.py pdf
```

这样可以判断问题位于：环境、Markdown、转换层，还是最终 LaTeX 编译层。
