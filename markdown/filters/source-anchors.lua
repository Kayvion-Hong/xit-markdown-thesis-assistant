-- Invisible PDF destinations plus block text for Markdown paragraph navigation.
-- Runs before xit.lua so figures/tables can place destinations inside their floats.
function Pandoc(doc)
  local prefix = os.getenv('XIT_ANCHOR_PREFIX')
  local output = os.getenv('XIT_ANCHOR_OUTPUT')
  if not prefix or not output then return doc end
  local records, blocks = {}, pandoc.List()
  for index, block in ipairs(doc.blocks) do
    local text = pandoc.utils.stringify(block)
    if block.t == 'CodeBlock' then text = block.text end
    if block.t == 'Figure' then text = pandoc.utils.stringify(block.caption.long) end
    if text ~= '' then
      local anchor = prefix .. '-' .. index
      local marker = '\\hypertarget{' .. anchor .. '}{}'
      if block.t == 'Header' then
        if block.identifier == '' then block.identifier = anchor end
        anchor = block.identifier
      elseif block.t == 'Para' or block.t == 'Plain' then
        block.content:insert(1, pandoc.RawInline('latex', marker))
      elseif block.t == 'Figure' or block.t == 'Table' or block.t == 'CodeBlock' then
        block.attributes['data-xit-anchor'] = anchor
      elseif block.t == 'Div' and block.classes:includes('equation') then
        block.attributes['data-xit-anchor'] = anchor
      else
        blocks:insert(pandoc.RawBlock('latex', marker))
      end
      records[#records+1] = {anchor=anchor, text=text, kind=block.t}
    end
    blocks:insert(block)
  end
  local file = assert(io.open(output, 'w'))
  file:write(pandoc.json.encode(records)); file:close()
  doc.blocks = blocks
  return doc
end
