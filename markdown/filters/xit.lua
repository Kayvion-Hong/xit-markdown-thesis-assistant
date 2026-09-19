-- XIT Markdown -> LaTeX compatibility filter.
-- Keeps Markdown authoring simple while emitting constructs already used by xitthesis.cls.

local function source_anchor(el)
  local id = el.attributes and el.attributes['data-xit-anchor']
  return id and ('\\hypertarget{' .. id .. '}{}') or ''
end

local function trim(s)
  return (s:gsub('^%s+', ''):gsub('%s+$', ''))
end

local function escape_tex(s)
  local replacements = {
    ['\\'] = '\\textbackslash{}', ['%'] = '\\%', ['#'] = '\\#',
    ['&'] = '\\&', ['_'] = '\\_', ['$'] = '\\$',
    ['{'] = '\\{', ['}'] = '\\}',
    ['~'] = '\\textasciitilde{}', ['^'] = '\\textasciicircum{}'
  }
  return (s:gsub('.', function(ch) return replacements[ch] or ch end))
end

local function blocks_to_latex(blocks)
  if not blocks or #blocks == 0 then
    return ''
  end
  local text = pandoc.write(pandoc.Pandoc(blocks), 'latex', { wrap_text = 'none' })
  text = trim(text)
  text = text:gsub('\n\n+', ' ')
  return text
end

local function inlines_to_latex(inlines)
  if not inlines or #inlines == 0 then
    return ''
  end
  return blocks_to_latex({ pandoc.Plain(inlines) })
end

-- Cross-reference syntax:
-- [图](#fig:system), [表](#tab:result), [式](#eq:model), [代码](#code:uart)
function Link(el)
  local id = el.target:match('^#(.+)$')
  if not id then
    return nil
  end

  local command = nil
  if id:match('^fig:') or id:match('^tab:') or id:match('^code:') then
    command = '\\ref'
  elseif id:match('^eq:') then
    command = '\\eqref'
  else
    return nil
  end

  local prefix = el.content
  local out = {}
  for _, inline in ipairs(prefix) do
    table.insert(out, inline)
  end
  table.insert(out, pandoc.RawInline('latex', '~' .. command .. '{' .. id .. '}'))
  return out
end

-- Numbered display equation syntax:
-- ::: {#eq:model .equation}
-- $$ x(t+1)=Ax(t)+Bu(t) $$
-- :::
function Div(el)
  if not el.classes:includes('equation') then
    return nil
  end
  if el.identifier == '' then
    error('XIT equation div requires an identifier such as #eq:model')
  end
  if #el.content ~= 1 then
    error('XIT equation div must contain exactly one display equation')
  end
  local block = el.content[1]
  if block.t ~= 'Para' and block.t ~= 'Plain' then
    error('XIT equation div must contain a display equation paragraph')
  end
  if #block.content ~= 1 or block.content[1].t ~= 'Math' then
    error('XIT equation div must contain exactly one math expression')
  end
  local math = block.content[1]
  if math.mathtype ~= 'DisplayMath' then
    error('XIT equation div requires $$...$$ display math')
  end
  local latex = table.concat({
    '\\begin{equation}',
    source_anchor(el),
    '  ' .. trim(math.text),
    '  \\label{' .. el.identifier .. '}',
    '\\end{equation}'
  }, '\n')
  return pandoc.RawBlock('latex', latex)
end

-- Figures are emitted in the same basic form documented by the original template.
function Figure(el)
  if #el.content ~= 1 then
    return nil
  end
  local block = el.content[1]
  if (block.t ~= 'Plain' and block.t ~= 'Para') or #block.content ~= 1 then
    return nil
  end
  local image = block.content[1]
  if image.t ~= 'Image' then
    return nil
  end

  local path = image.src
  if path:match('^https?://') then
    error('Remote figure URLs are not supported; download the figure into thesis/figures first: ' .. path)
  end
  if path:find('[{}]') then
    error('Figure path cannot contain braces: ' .. path)
  end

  local width = image.attributes.width or '0.90\\textwidth'
  local percent = width:match('^(%d+%.?%d*)%%$')
  if percent then
    width = tostring(tonumber(percent) / 100) .. '\\textwidth'
  elseif width:match('^%d+%.?%d*$') then
    width = width .. '\\textwidth'
  end

  local caption = inlines_to_latex(el.caption.long[1] and el.caption.long[1].content or image.caption)
  if caption == '' then
    caption = inlines_to_latex(image.caption)
  end

  local lines = {
    '\\begin{figure}[htbp]',
    '  \\centering',
    source_anchor(el),
    '  \\includegraphics[width=' .. width .. ']{' .. path .. '}',
  }
  if caption ~= '' then
    table.insert(lines, '  \\caption{' .. caption .. '}')
  end
  if el.identifier ~= '' then
    table.insert(lines, '  \\label{' .. el.identifier .. '}')
  end
  table.insert(lines, '\\end{figure}')
  return pandoc.RawBlock('latex', table.concat(lines, '\n'))
end

local language_map = {
  c = 'C', cpp = 'C++', ['c++'] = 'C++',
  python = 'Python', java = 'Java', javascript = 'JavaScript',
  js = 'JavaScript', matlab = 'Matlab', sql = 'SQL',
  bash = 'bash', sh = 'bash', tex = '[LaTeX]TeX', latex = '[LaTeX]TeX'
}

-- Fenced code blocks become listings, which the original template already supports.
-- ```c {#code:uart caption="串口日志输出示例"}
function CodeBlock(el)
  local lang = nil
  if #el.classes > 0 then
    lang = language_map[el.classes[1]] or el.classes[1]
  end
  local opts = {}
  if lang then
    table.insert(opts, 'language={' .. lang .. '}')
  end
  local caption = el.attributes.caption
  if caption and caption ~= '' then
    table.insert(opts, 'caption={' .. escape_tex(caption) .. '}')
  end
  if el.identifier ~= '' then
    table.insert(opts, 'label={' .. el.identifier .. '}')
  end
  local suffix = #opts > 0 and ('[' .. table.concat(opts, ',') .. ']') or ''
  local latex = source_anchor(el) .. '\n' .. '\\begin{lstlisting}' .. suffix .. '\n' .. el.text .. '\n\\end{lstlisting}'
  return pandoc.RawBlock('latex', latex)
end

local function table_caption_and_label(caption)
  local text = pandoc.utils.stringify(caption.long)
  local label = text:match('%s*{#([%w%._:%-]+)}%s*$')
  if label then
    text = text:gsub('%s*{#[%w%._:%-]+}%s*$', '')
  end
  return text, label
end

local function row_to_latex(row)
  local cells = {}
  for _, cell in ipairs(row.cells) do
    local latex = blocks_to_latex(cell.contents)
    latex = latex:gsub('\n', ' ')
    table.insert(cells, latex)
  end
  return table.concat(cells, ' & ') .. ' \\\\'
end

-- Pipe tables become booktabs three-line tables rather than Pandoc longtable.
-- Add a label at the end of the caption:  : 表题 {#tab:result}
function Table(el)
  local ncols = #el.colspecs
  if ncols == 0 then
    return nil
  end

  local caption, label = table_caption_and_label(el.caption)
  -- Recent Pandoc versions move caption attributes into the Table node.
  if el.identifier and el.identifier ~= '' then
    label = el.identifier
  end
  local width = 0.90 / ncols
  local colspec = '@{}'
  for _ = 1, ncols do
    colspec = colspec .. string.format('p{%.3f\\textwidth}', width)
  end
  colspec = colspec .. '@{}'

  local lines = {
    '\\begin{table}[htbp]',
    '  \\centering',
    source_anchor(el),
  }
  if caption ~= '' then
    table.insert(lines, '  \\caption{' .. escape_tex(caption) .. '}')
  end
  if label then
    table.insert(lines, '  \\label{' .. label .. '}')
  end
  table.insert(lines, '  \\begin{tabular}{' .. colspec .. '}')
  table.insert(lines, '    \\toprule')

  for _, row in ipairs(el.head.rows) do
    table.insert(lines, '    ' .. row_to_latex(row))
  end
  if #el.head.rows > 0 then
    table.insert(lines, '    \\midrule')
  end

  for _, body in ipairs(el.bodies) do
    for _, row in ipairs(body.head) do
      table.insert(lines, '    ' .. row_to_latex(row))
      table.insert(lines, '    \\midrule')
    end
    for _, row in ipairs(body.body) do
      table.insert(lines, '    ' .. row_to_latex(row))
    end
  end

  table.insert(lines, '    \\bottomrule')
  table.insert(lines, '  \\end{tabular}')
  table.insert(lines, '\\end{table}')
  return pandoc.RawBlock('latex', table.concat(lines, '\n'))
end
