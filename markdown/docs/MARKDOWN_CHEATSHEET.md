# Markdown 论文写作速查表

## 标题

```markdown
# 章标题
## 节标题
### 小节标题
```

每个 `chapters/*.md` 只能有一个 `#`。

## 段落与强调

```markdown
第一段。

第二段。

**加粗文字**
*强调文字*
```

## 列表

```markdown
- 项目一
- 项目二

1. 第一步
2. 第二步
```

## 行内公式

```markdown
系统功率为 $P=UI$。
```

## 编号公式

```markdown
::: {#eq:current .equation}
$$
I = k(U_{adc}-U_0)
$$
:::

由[式](#eq:current)可知……
```

## 图片

```markdown
系统架构如[图](#fig:system)所示。

![系统总体架构](figures/system.png){#fig:system width=90%}
```

## 三线表

```markdown
| 指标 | 结果 | 目标 |
| --- | --- | --- |
| 准确率 | 96.5% | ≥95% |
| 延迟 | 35 ms | ≤50 ms |

: 系统测试结果 {#tab:test}
```

正文：

```markdown
测试结果见[表](#tab:test)。
```

## 代码

````markdown
```c {#code:main caption="主程序示例"}
int main(void) {
    return 0;
}
```
````

引用：

```markdown
实现见[代码](#code:main)。
```

## 参考文献

```markdown
已有研究提出…… [@zhang2026]。
```

多篇：

```markdown
已有多项研究讨论该问题 [@zhang2026; @li2025]。
```

## 不建议这样写

```text
第 2 章 系统设计       ← 不要手工编号
图 3-1               ← 不要手工编号
[1] 张三……            ← 不要手工维护参考文献编号
连续空格对齐           ← 不要
连续回车推图片到下一页   ← 不要
```

让 LaTeX 模板负责编号和排版。
