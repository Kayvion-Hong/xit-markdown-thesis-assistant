# 这里是你真正写论文的地方

第一次使用建议按这个顺序：

1. 修改 `metadata.yaml`；
2. 修改 `abstract-cn.md` / `abstract-en.md`；
3. 从 `chapters/01-introduction.md` 开始写正文；
4. 图片全部放到 `figures/`；
5. 文献放到 `references.bib`；
6. 每写一段就回到 `markdown/` 运行 `python xit.py check`。

不要在 `build/project/` 中长期编辑，因为那里是自动生成的临时 LaTeX 工程。
