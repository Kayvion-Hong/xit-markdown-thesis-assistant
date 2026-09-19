# 转换实现

## Markdown 到 LaTeX

构建脚本调用 Pandoc 把每章 Markdown 转成 LaTeX 片段，并通过 Lua filter 把常用论文对象映射为原模板已经支持的环境。

## 三线表

普通 Markdown 表格会转换为三线表。

表题末尾使用 `{#tab:features}` 定义标签。

| 内容 | Markdown 输入 | LaTeX 输出 |
| --- | --- | --- |
| 章节 | `# 标题` | `\\chapter{标题}` |
| 公式 | equation fenced div | `equation` 环境 |
| 代码 | fenced code | `lstlisting` 环境 |

: Markdown 与 LaTeX 的主要映射 {#tab:features}

正文可写“如[表](#tab:features)所示”。
