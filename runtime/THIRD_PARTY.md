# 随包运行环境 0.4.0

这些组件遵循各自许可证，不纳入本项目的 MIT 授权。

* CPython 3.12.7 Windows x86-64 官方嵌入式发行版：https://www.python.org/ftp/python/3.12.7/python-3.12.7-embed-amd64.zip 。保留 `python/LICENSE.txt`。这是锁定用于复现的版本，不宣称是最新安全版本；仅用于本机论文助手。
* PyYAML 6.0.2、BibTeXParser 1.4.3、PyParsing 3.2.3：从 PyPI 下载，许可证保留在 `python/Lib/site-packages/*dist-info/`。BibTeXParser 由源码构建纯 Python wheel。
* Pandoc 3.11：来源及许可证见本目录 README 和 pandoc 子目录。
* TinyTeX / TeX Live 2026：复制自本次验证使用的本地 TinyTeX 安装，保留 LICENSE.TL、LICENSE.CTAN、tlpkg 包元数据以及各宏包文档/许可证。项目：https://yihui.org/tinytex/ ，TeX Live：https://tug.org/texlive/ 。这是本次项目环境快照，不代表完整 TeX Live。

未复制 C:/Windows/Fonts 中的字体。Windows 字体权利属于其原权利人；使用原模板的系统字体选择规则。

SHA256.json 记录随包运行文件的哈希，用于交付内容核对。许可证、源代码获取与发行条件请参照各组件原始声明。
