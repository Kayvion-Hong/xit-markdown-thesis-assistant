# 绪论

## 研究背景

毕业论文通常经历多轮修改。将正文保存为 Markdown 可以直接使用 Git 进行提交、差分、回滚与审阅，而最终格式仍交给学校既有 LaTeX 模板处理。

## 本项目目标

本项目遵循“Markdown 负责内容、LaTeX 负责版式、PDF 负责交付”的原则。Markdown 版本不修改原有 `xitthesis.cls`，而是在构建目录中复用原模板。

参考文献可以使用 Pandoc citation 语法，例如该示例引用 Pandoc 官方用户指南 [@pandoc-manual]。
