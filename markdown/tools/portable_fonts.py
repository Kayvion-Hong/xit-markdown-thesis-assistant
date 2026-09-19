"""Use redistributable TeX fonts only in the generated project, never the original ZIP."""
from pathlib import Path
import os

WINDOWS_FONTS = ('simsun.ttc','simhei.ttf','times.ttf','timesbd.ttf','timesi.ttf','timesbi.ttf',
                 'consola.ttf','consolab.ttf','consolai.ttf','consolaz.ttf')


def exact_fonts_available():
    # The upstream class uses this literal location, so test that same location.
    return all((Path('C:/Windows/Fonts')/name).is_file() for name in WINDOWS_FONTS)


def configure(project):
    if os.environ.get('XIT_PORTABLE_FONTS') != '1' and exact_fonts_available():
        return None
    path=project/'xitthesis.cls'
    source=path.read_text(encoding='utf-8')
    start=source.index(r'\newcommand{\xit@setfonts}')
    end=source.index('\n\\xit@setfonts',start)
    setup=r'''\newcommand{\xit@setfonts}{%
  \xitexactfontsfalse
  \setmainfont{FandolSong-Regular.otf}[BoldFont=FandolHei-Regular.otf]
  \setsansfont{FandolHei-Regular.otf}[BoldFont=FandolHei-Bold.otf]
  \setmonofont{lmmono10-regular.otf}
  \setCJKmainfont{FandolSong-Regular.otf}[BoldFont=FandolHei-Regular.otf]
  \setCJKfamilyfont{song}{FandolSong-Regular.otf}[BoldFont=FandolHei-Regular.otf]
  \setCJKsansfont{FandolHei-Regular.otf}[BoldFont=FandolHei-Bold.otf]
  \setCJKfamilyfont{hei}{FandolHei-Regular.otf}[BoldFont=FandolHei-Bold.otf]
  \setCJKmonofont{FandolFang-Regular.otf}
  \setCJKfamilyfont{fang}{FandolFang-Regular.otf}
  \setCJKfamilyfont{kai}{FandolKai-Regular.otf}
  \newfontfamily\xitenglishfont{texgyretermes-regular.otf}[BoldFont=texgyretermes-bold.otf,ItalicFont=texgyretermes-italic.otf,BoldItalicFont=texgyretermes-bolditalic.otf]
}
'''
    path.write_text(source[:start]+setup+source[end:],encoding='utf-8')
    return '使用随包开源替代字体（Fandol / TeX Gyre Termes / Latin Modern）。字体与原模板不同，分页可能改变；仅作写作预览，定稿请核对学校要求。'
