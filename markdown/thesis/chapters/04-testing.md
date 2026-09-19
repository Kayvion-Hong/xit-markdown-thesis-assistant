# 构建与验证

## 构建命令

在 `markdown/` 目录执行：

```bash {#code:build caption="Markdown 论文构建命令"}
python tools/build.py
```

构建程序会先验证元数据、章节结构、图片路径、标签和参考文献键，再解压原始 LaTeX 模板到 `build/project/`。原 ZIP 只读使用，并在构建前后计算 SHA-256 以确认没有被修改。

## 版本控制

推荐只提交 `thesis/`、`tools/`、`filters/` 和配置文件，不提交 `build/` 中的中间产物。
