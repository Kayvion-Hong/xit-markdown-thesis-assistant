# 随包运行程序

`pandoc/` 包含 Pandoc 3.11 官方 Windows x86-64 便携程序。程序未修改，供论文助手作为独立进程调用。

- 原始发布包：https://github.com/jgm/pandoc/releases/download/3.11/pandoc-3.11-windows-x86_64.zip
- 版本源代码：https://github.com/jgm/pandoc/tree/3.11
- 上游源代码发布包：https://hackage.haskell.org/package/pandoc-3.11/pandoc-3.11.tar.gz
- 原始许可与版权：`pandoc/COPYING.rtf`、`pandoc/COPYRIGHT.txt`
- pandoc.exe SHA-256：`e0057eaf640d08ba028b70721d4f7b63a685c30430de9db89aea84de2d4a1912`

Pandoc 按其 GPL v2 或后续版本及附带第三方声明分发，不适用本项目作者原创代码的 MIT License。Windows 完整包内请保留此目录。macOS/Linux 用户需安装对应系统版本。
# 0.4.0 补充

新版除下述 Pandoc 外，还内置独立 Python 及 TinyTeX/TeX Live。来源、版本和许可证位置见 [THIRD_PARTY.md](THIRD_PARTY.md)。Windows 新手不需要手动配置软件 PATH；字体仍使用本机字体。
