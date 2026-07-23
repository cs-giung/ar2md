local referenced_ids = {}
local algorithm_sources = {}

local function has_class(element, class_name)
  for _, class in ipairs(element.classes or {}) do
    if class == class_name then
      return true
    end
  end
  return false
end

local function anchor_block(identifier)
  return pandoc.RawBlock("html", '<a id="' .. identifier .. '"></a>')
end

local function anchor_inline(identifier)
  return pandoc.RawInline("markdown", '<a id="' .. identifier .. '"></a>')
end

local function referenced_anchor_block(identifier)
  if identifier ~= "" and referenced_ids[identifier] then
    return anchor_block(identifier)
  end
end

local function internal_identifier(target)
  local fragment = target:match("^#(.+)$")
  if fragment then
    return fragment
  end
  if target:match("^%a[%w+%.%-]*:") or target:match("^//") then
    return nil
  end
  return target:match("%.html#(.+)$")
end


local function rewrite_link(link)
  if link.target:match("^data:") or link.target:match("^javascript:") then
    return {}
  end

  local identifier = internal_identifier(link.target)
  if identifier then
    referenced_ids[identifier] = true
    link.target = "#" .. identifier
  end

  link.title = ""
  link.identifier = ""
  link.classes = {}
  link.attributes = {}
  return link
end

local function collect_references(document)
  document:walk({
    Link = function(link)
      local identifier = internal_identifier(link.target)
      if identifier then
        referenced_ids[identifier] = true
      end
    end,
  })
end

local function collect_algorithm_sources(document)
  document:walk({
    Figure = function(figure)
      if not figure.identifier:match("^alg%d+$") then
        return
      end

      figure:walk({
        Link = function(link)
          if link.target:match("^data:text/plain") then
            local _, contents = pandoc.mediabag.fetch(link.target)
            if contents then
              algorithm_sources[figure.identifier] = contents
            end
          end
        end,
      })
    end,
  })
end

local function clean_div(div)
  local content = div.content
  local anchor = referenced_anchor_block(div.identifier)
  if anchor then
    table.insert(content, 1, anchor)
  end
  return content
end

local function clean_span(span)
  if has_class(span, "ltx_ERROR") or has_class(span, "ltx_bib_cited") then
    return {}
  end

  if has_class(span, "ltx_role_footnotemark") then
    local mark = pandoc.utils.stringify(span.content):match("%d")
    return pandoc.Superscript({ pandoc.Str(mark or "*") })
  end

  if has_class(span, "ltx_role_footnote") then
    local note_content = span.content
    while note_content[1] and note_content[1].tag == "Superscript" do
      table.remove(note_content, 1)
    end
    if note_content[1] and note_content[1].tag == "Str" and note_content[1].text:match("^%d+$") then
      table.remove(note_content, 1)
    end
    return pandoc.Note({ pandoc.Para(note_content) })
  end

  local content = span.content
  if has_class(span, "ltx_font_bold") then
    content = { pandoc.Strong(content) }
  elseif has_class(span, "ltx_font_italic") then
    content = { pandoc.Emph(content) }
  elseif has_class(span, "ltx_font_typewriter") then
    content = { pandoc.Code(pandoc.utils.stringify(content)) }
  end

  if span.identifier ~= "" and referenced_ids[span.identifier] then
    table.insert(content, 1, anchor_inline(span.identifier))
  end
  return content
end

local function clean_header(header)
  local identifier = header.identifier
  header.identifier = ""
  header.classes = {}
  header.attributes = {}

  local anchor = referenced_anchor_block(identifier)
  if anchor then
    return { anchor, header }
  end
  return header
end

local function clean_code(code)
  code.identifier = ""
  code.classes = {}
  code.attributes = {}
  return code
end

local function clean_code_block(code_block)
  code_block.identifier = ""
  code_block.classes = {}
  code_block.attributes = {}
  return code_block
end

local function clean_figure(figure)
  local blocks = {}
  local caption_text = pandoc.utils.stringify(figure.caption.long)
  if caption_text ~= "" then
    figure = figure:walk({
      Image = function(image)
        local alt_text = pandoc.utils.stringify(image.caption)
        if alt_text == "" or alt_text == "Refer to caption" then
          image.caption = { pandoc.Str(caption_text) }
        end
        return image
      end,
    })
  end
  local anchor = referenced_anchor_block(figure.identifier)
  if anchor then
    table.insert(blocks, anchor)
  end

  local algorithm_source = algorithm_sources[figure.identifier]
  if algorithm_source then
    table.insert(blocks, pandoc.CodeBlock(algorithm_source))
  else
    for _, block in ipairs(figure.content) do
      table.insert(blocks, block)
    end
  end
  for _, block in ipairs(figure.caption.long) do
    table.insert(blocks, block)
  end
  return blocks
end

local function clean_image(image)
  image.identifier = ""
  image.classes = {}
  image.attributes = {}
  image.title = ""

  if image.src:match("^data:image/") then
    return {}
  end
  return image
end

local function clean_table(table_element)
  local identifier = table_element.identifier

  if has_class(table_element, "ltx_equation") then
    local equation
    local equation_number

    table_element:walk({
      Math = function(math)
        equation = equation or math
      end,
      Str = function(text)
        equation_number = equation_number or text.text:match("^%((%d+)%)$")
      end,
    })

    local blocks = {}
    if identifier ~= "" then
      table.insert(blocks, anchor_block(identifier))
    end
    if equation then
      equation.mathtype = "DisplayMath"
      table.insert(blocks, pandoc.Para({ equation }))
    end
    if equation_number then
      table.insert(blocks, pandoc.Para({ pandoc.Str("Equation (" .. equation_number .. ")") }))
    end
    return blocks
  end

  table_element.identifier = ""
  table_element.classes = {}
  table_element.attributes = {}

  local anchor = referenced_anchor_block(identifier)
  if anchor then
    return { anchor, table_element }
  end
  return table_element
end

function Pandoc(document)
  local article_blocks

  document:walk({
    Div = function(div)
      if has_class(div, "ltx_page_content") then
        article_blocks = div.content
      end
    end,
  })

  if not article_blocks then
    error("arXiv article container (.ltx_page_content) not found")
  end

  local article = pandoc.Pandoc(article_blocks, document.meta)
  collect_references(article)
  collect_algorithm_sources(article)

  return article:walk({
    Code = clean_code,
    CodeBlock = clean_code_block,
    Div = clean_div,
    Header = clean_header,
    Figure = clean_figure,
    Image = clean_image,
    Link = rewrite_link,
    Span = clean_span,
    Table = clean_table,
  })
end
