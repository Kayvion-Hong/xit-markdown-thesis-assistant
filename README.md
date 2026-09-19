# XIT Markdown 毕业论文助手

在左侧用 Markdown 写论文，在右侧查看 LaTeX 编译后的 PDF。这个本地写作工具基于厦门工学院毕业论文模板，提供资料填写、章节管理、图表和文献插入、自动保存及备份恢复，适合希望少接触 LaTeX 源码的同学。

本项目由学生根据厦门工学院本科毕业论文（设计）的 Word 格式要求独立实现。正式提交前，请以学校、学院和指导教师当年发布的要求为准。

![第二章的 Markdown 与 PDF 左右对照](docs/images/03-live-preview.png)

## 第一次使用，从这里开始

**Windows 新手请下载完整运行包。** 前往 [Releases 下载页面](https://github.com/Kayvion-Hong/xit-markdown-thesis-assistant/releases)，在版本的 Assets 中选择 `xit-v0.5.0-live-preview-windows.zip`。GitHub 自动提供的 `Source code (zip)` 只有源码，不包含运行环境。

1. 将完整 ZIP 全部解压到较短的路径，例如 `D:\XIT`。不要在压缩包窗口里直接运行。
2. 打开解压出的 `XIT` 文件夹，双击 `启动AI示例教学.bat`，先熟悉操作。
3. 保持启动窗口打开。在浏览器的“检查与导出”中点击“生成 PDF”，确认示例能编译。
4. 按页面“AI 示例教学”的练习修改姓名、一段正文和一张表。
5. 练习后点击“关闭助手”，再双击 `启动论文助手.bat`，开始自己的论文。

完整操作见 **[新手图文指南](docs/GETTING_STARTED.md)**。遇到启动、字体或编译问题，查阅 [常见问题](docs/TROUBLESHOOTING.md)。

## 可以做什么

| 写作任务 | 对应操作 |
| --- | --- |
| 填写封面、关键词 | 表单填写，不必手改 YAML |
| 增减和调整章节 | 新增、改名、排序、移出和恢复，五章只是示例 |
| 边写边看 | 停止输入后自动编译，也可手动编译；整篇 PDF 连续滚动 |
| 查找对应位置 | 双击正文，在 Markdown 和 PDF 之间按段落或内容块定位 |
| 调整阅读大小 | 适合宽度、适合整页、25% 至 300% 缩放、大字阅读 |
| 插入图表和引用 | 图片上传、三线表、编号公式、文献选择和 BibTeX 导入 |
| 找回修改 | 自动保存、本地草稿恢复、撤销重做、文件历史和整篇备份 |

预览需要完成编译后才会更新。它不是逐字即时排版，也不提供多人云端协作。复杂数学公式仍需基本 LaTeX 语法。

## 完整包与源码的区别

| | Windows 完整包 | 本仓库源码 |
| --- | --- | --- |
| 适用对象 | 直接写论文的同学 | 开发者、自行配置环境的用户 |
| 获取方式 | Releases 中的命名 ZIP | Git clone 或 Source code |
| Python、Pandoc、TeX | 随包提供 | 自行安装，见[开发说明](docs/DEVELOPMENT.md) |
| 使用入口 | 双击 BAT | Python 命令启动 |

完整包面向 Windows 10/11 x64；不能保证兼容所有 Windows 版本、ARM 设备和受限机房环境。常规编辑和使用已有宏包编译可以离线进行。下载更新、安装额外宏包和查找文献需要网络。

原模板字体依赖本机授权安装的字体。包内提供开源替代字体以便预览，但替换后字形和分页可能变化，不能据此保证与原模板完全一致。详见 [Windows 兼容与环境修复](Windows兼容与环境修复.md)。

## 跟着 AI 示例练习

随包教学项目为《基于 STM32 的智能照明系统设计》，与普通论文使用不同目录。建议一次只改一处，保存、编译，再观察变化。

![AI 示例教学入口及分步练习](docs/images/07-ai-tutorial.png)

示例中的数据、图表、结论和部分文献用于排版教学，未经真实研究验证，不应直接作为研究成果提交。教程包括封面、正文、图片、表格、公式、文献、章节增减和代码附录。详见 [AI 示例教学手册](AI示例教学手册.md)。

## 保存和恢复

正文停止输入约 1.2 秒后自动保存，基本资料约 1.6 秒后保存。以页面“内容已同步”为准；保存失败时应先处理提示。`Ctrl+S` 可以立即保存，`Ctrl+Z` 撤销，`Ctrl+Y` 或 `Ctrl+Shift+Z` 重做。

未同步的修改还会尝试保存在浏览器本地草稿中。恢复依赖原浏览器、访问地址和项目位置；清理浏览器数据、移动项目或磁盘故障可能使恢复失效。请定期把整篇备份另存到其他磁盘。具体区别见[图文指南](docs/GETTING_STARTED.md)。

## 项目结构

```text
XIT/
├── 启动论文助手.bat
├── 启动AI示例教学.bat
├── 厦门工学院毕业设计论文模板.zip
├── markdown/
│   ├── thesis/             自己的论文内容
│   ├── examples/           AI 教学项目及原示例
│   ├── assistant/          本地网页助手
│   ├── tools/              检查与编译工具
│   └── tests/              自动测试
├── docs/                   图文教程、开发说明和截图
└── runtime/                完整包的运行环境；源码仓库仅保留说明
```

## 验证与问题反馈

v0.5.0 的既有验证包括 32 项 Python 测试、撤销和草稿 JavaScript 测试、29 页 AI 示例编译及浏览器中的连续预览和内容块定位。测试范围及未覆盖情况见 [验证记录](VALIDATION.md)。这些结果不代表所有设备或任意新增论文内容均已验证。

有问题可在 [Issues](https://github.com/Kayvion-Hong/xit-markdown-thesis-assistant/issues) 中提供版本号、操作步骤和最先出现的错误。提交日志或截图前，请删除姓名、学号及未公开论文内容。

## 许可与来源

除另有说明外，作者原创的源代码、编译脚本和说明文档采用 [MIT License](LICENSE)。使用、修改和分发时请保留版权声明和许可文本。

学校名称、校徽、Logo、字体及其他第三方素材不自动纳入 MIT License，相关权利仍归原权利人所有。第三方运行环境继续遵循各自许可，详见 [NOTICE.md](NOTICE.md)、[运行环境许可说明](runtime/THIRD_PARTY.md) 和 [截图来源](docs/IMAGE_SOURCES.md)。

原 LaTeX 模板：[GitHub](https://github.com/Kayvion-Hong/xit-bachelor-thesis-latex-template) · [Gitee](https://gitee.com/G1257314839/xit-bachelor-thesis-latex-template)。
