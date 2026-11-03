// URS/RFQ package and Response Form (Convenient Enterprises, ce-requirements 8.2 and 8.5).
// data.json: render/urs_document.py build_package() (kind "urs") or build_response_form() (kind "response").
#let d = json("data.json")
#let blue = rgb("#1F4ED8")
#let rule-c = luma(150)
#let head-fill = luma(217)

#let run(r) = {
  let t = r.text
  let body = if r.at("b", default: false) and r.at("i", default: false) { strong(emph(t)) }
    else if r.at("b", default: false) { strong(t) }
    else if r.at("i", default: false) { emph(t) } else { t }
  if r.at("note", default: false) or r.at("blank", default: false) { text(fill: blue, body) } else { body }
}
#let runs(rs) = for r in rs { run(r) }

#let grid-table(rows, header: true, columns: auto) = {
  let n = calc.max(..rows.map(r => r.len()))
  let cols = if columns == auto { (auto,) * n } else { columns }
  table(columns: cols, stroke: 0.5pt + rule-c, inset: 4pt,
    fill: (x, y) => if header and y == 0 { head-fill } else { none },
    ..rows.enumerate().map(((i, row)) => row.map(c => {
      let content = if type(c) == str { c } else { runs(c) }
      if header and i == 0 { strong(content) } else { content }
    }) + ((""),) * (n - row.len())).flatten())
  v(4pt)
}

#let block-item(b) = {
  if b.t == "p" { par(runs(b.runs)) }
  else if b.t == "li" {
    pad(left: 0.25in * b.level, list(marker: ([•], [◦], [▪]).at(calc.min(b.level, 2)), runs(b.runs)))
  }
  else if b.t == "table" { grid-table(b.rows, header: b.at("header", default: true)) }
  else if b.t == "form" {
    for row in b.rows {
      if row.len() == 1 {
        grid(columns: (1.8in, 1fr), align: bottom, row.at(0), line(length: 100%, stroke: 0.5pt))
      } else {
        grid(columns: (auto, 1fr, auto, 1.3in), column-gutter: 6pt, align: bottom,
          row.at(0) + ":", line(length: 100%, stroke: 0.5pt), row.at(1) + ":", line(length: 100%, stroke: 0.5pt))
      }
      v(10pt)
    }
  }
}

#let doc-control(dc) = {
  text(12pt, weight: "bold")[Document Version History and Approvals]
  v(4pt)
  grid-table((("Approver", "Role", "Signature", "Date"),) + dc.approvers.map(a => a + ("", "")),
    columns: (1.4fr, 1.6fr, 1.6fr, 1fr))
  grid-table((("Version", "Issue Date", "Revised Section", "Revisions"),) + dc.versions,
    columns: (0.8fr, 1fr, 1.2fr, 2fr))
}

#set document(title: if d.kind == "urs" { d.title } else { "URS/RFQ Response Form" })
#set page(paper: "us-letter", margin: (x: 1in, top: 0.9in, bottom: 1in),
  header: align(left, text(9pt, weight: "bold", d.client)),
  footer: context {
    set text(8.5pt)
    grid(columns: (1fr, 1fr), [Revision: #d.revision],
      align(right)[Page #counter(page).display("1 of 1", both: true)])
    grid(columns: (1fr, auto), align: bottom,
      text(7.5pt, fill: luma(90))[Author: #d.author #linebreak() Document Number: #d.document_number],
      text(6.5pt, fill: luma(150), d.at("prepared_by", default: "")))
  })
#set text(font: "Carlito", size: 11pt)
#set par(justify: false, leading: 0.55em, spacing: 0.75em)
#set list(indent: 0.15in, body-indent: 0.4em, spacing: 0.45em)
#show heading: set text(font: "Carlito", weight: "bold")
#show heading.where(level: 1): it => { v(14pt); text(14pt, it.body); v(6pt) }
#show heading.where(level: 2): it => { v(10pt); text(12pt, it.body); v(4pt) }
#show heading.where(level: 3): it => { v(6pt); text(11pt, it.body); v(2pt) }

#if d.kind == "urs" {
  if d.instructions.len() > 0 {
    strong(d.client)
    v(6pt)
    for b in d.instructions { block-item(b) }
    pagebreak()
  }
  if d.doc_control != none { doc-control(d.doc_control); pagebreak() }
  // cover
  align(center, {
    text(20pt, weight: "bold", d.client)
    for a in d.address { linebreak(); text(12pt, a) }
    v(0.5in)
    text(26pt, weight: "bold", d.title)
    if d.subtitle != "" { linebreak(); text(16pt, weight: "bold", d.subtitle) }
    v(0.5in)
    text(16pt)[User Requirements Summary (URS) \ & \ Request For Quotation (RFQ)]
    v(0.4in)
    [Revision: #d.revision \ #d.month_year]
    if d.revision_note.len() > 0 { parbreak(); runs(d.revision_note) }
    v(0.3in)
    [Issued for Quotation: #d.issued \ Quotation Response Due: #d.due]
  })
  v(1fr)
  strong[Confidential Information:]
  par(text(9pt, runs(d.confidentiality)))
  pagebreak()
  text(12pt, weight: "bold")[URS/RFQ Revision History]
  v(4pt)
  grid-table((("Revision #", "Issue Date", "Revised Section", "Revisions Made"),) + d.history,
    columns: (0.9fr, 1fr, 1.2fr, 2fr))
  v(8pt)
  outline(title: text(14pt)[Table of Contents], indent: 1.2em, depth: 3)
  pagebreak()
  for s in d.sections {
    if s.pagebreak { pagebreak() }
    let t = if s.numbered { s.number + ".  " + s.heading } else { s.heading }
    heading(level: s.level, outlined: true, t)
    for b in s.blocks { block-item(b) }
  }
} else {
  if d.doc_control != none { doc-control(d.doc_control) }
  text(16pt, weight: "bold")[URS/RFQ Response Form]
  v(6pt)
  grid-table(d.fields, header: false, columns: (2.4in, 1fr))
  par(d.instructions)
  grid-table((("Section #", "Proposed Deviation or Correction"),) + d.rows, columns: (1.1in, 1fr))
}
