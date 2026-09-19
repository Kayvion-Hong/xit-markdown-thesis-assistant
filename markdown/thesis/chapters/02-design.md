# 总体设计

## 内容层与排版层分离

论文内容按章节拆分为 Markdown 文件，姓名、学号、题目和关键词等信息保存在 `metadata.yaml`。构建时，这些字段会映射到原模板的 `\XITTitle`、`\XITAuthor` 等命令。

## 公式

编号公式使用带标签的 `equation` fenced div：

::: {#eq:state .equation}
$$
x(t+1)=Ax(t)+Bu(t)
$$
:::

后续可以写“由[式](#eq:state)可知”，编号由 LaTeX 自动生成。
