# Git 与 AI 使用建议

## Git 提交粒度

推荐按“一个明确修改”提交，而不是一天结束才提交所有变化。

例如：

```text
docs: complete research background
docs: add system architecture figure
docs: revise experiment results
docs: add references for chapter 2
```

不要提交：

```text
build/
```

因为它是自动生成产物。

## AI 修改时的推荐指令

让 AI 明确知道修改范围：

```text
只修改 thesis/chapters/04-testing.md。
保留所有 {#fig:...}、{#tab:...}、{#eq:...} 和 [@...] 引用键。
不要修改 metadata.yaml、references.bib 或其他章节。
完成后说明修改点。
```

然后检查：

```bash
git diff
python xit.py check
```

## 为什么标签和引用键不要随便让 AI 改

以下内容相当于论文内部“接口”：

```text
#fig:system
#tab:test
#eq:model
@zhang2026
```

正文和对象之间靠它们连接。改一处忘记改另一处会造成引用失效。

## 推荐流程

```text
修改 Markdown
   ↓
git diff
   ↓
python xit.py check
   ↓
python xit.py pdf
   ↓
检查 PDF
   ↓
git commit
```

这样每一次提交都能对应一个可验证的论文状态。
