// Proposal layout for both companies. Data comes from data.json written by render/document.py.
// Pagination rules (spec 11):
//  - section title + column header never sit alone at a page bottom (table header orphan control)
//  - the first two lines travel with the header; a line never splits; the last line travels with the totals
//  - the column header repeats on continuation pages
//  - block sub-headings stay with their first paragraph (sticky); totals and signature never split

#let d = json("data.json")

#let ink = rgb("#222B3A")
#let muted = luma(110)
#let rule-c = luma(185)
#let pct-fill = luma(228)
#let alt-fill = (rgb("#DCE8F7"), rgb("#E3F1E8"), rgb("#F6ECDD"))
#let bar-fill = luma(150)

#set document(title: d.proposal.number + " " + d.client.project + " Proposal", author: d.company.name)
#set page(
  paper: "us-letter",
  margin: (x: 0.6in, top: 0.6in, bottom: 0.75in),
  footer: context align(center, text(8pt, fill: muted,
    counter(page).display("1 of 1", both: true))),
)
#set text(font: "Carlito", size: 10pt, fill: ink)
#set par(justify: false, leading: 0.55em, spacing: 0.9em)
#set list(indent: 0.6em, body-indent: 0.5em, spacing: 0.45em)
#set enum(indent: 0.6em, body-indent: 0.5em, spacing: 0.45em)
#set table.cell(breakable: false)

#let md(s) = if s == none or s == "" { [] } else { eval(s, mode: "markup") }

#let altfill(n) = if n > 0 and n <= 3 { alt-fill.at(n - 1) } else if n < 0 { luma(235) } else { none }

// accounting style money: "$" left, number right
#let money(s, bold: false) = {
  let w = if bold { "bold" } else { "regular" }
  if s == "" { [] } else if s == "-" {
    grid(columns: (auto, 1fr), text(weight: w)[\$], align(right, text(weight: w)[-]))
  } else {
    grid(columns: (auto, 1fr), text(weight: w)[\$], align(right, text(weight: w, s)))
  }
}

#let section-heading(t) = block(sticky: true, above: 1.4em, below: 0.6em,
  text(14pt, weight: "bold", t))
#let sub-heading(t) = block(sticky: true, above: 1.1em, below: 0.45em,
  text(11pt, weight: "bold", t))

#let text-block(b) = {
  if b.title != "" { sub-heading(b.title) }
  if b.kind == "units" {
    block(breakable: false, table(
      columns: (0.7in, 1.8in),
      stroke: (x, y) => (bottom: 0.4pt + rule-c),
      inset: (x: 4pt, y: 3pt),
      table.header(text(weight: "bold")[Unit], text(weight: "bold")[Description]),
      ..b.units.flatten().map(x => text(9pt, x)),
    ))
  } else if b.kind == "rates" {
    if b.before != "" { md(b.before) }
    block(breakable: false, table(
      columns: (2.6in, 1.6in, 1in),
      stroke: (x, y) => (bottom: 0.4pt + rule-c),
      inset: (x: 4pt, y: 3pt),
      table.header(text(weight: "bold")[Work], text(weight: "bold")[Performed by],
                   align(right, text(weight: "bold")[Rate])),
      ..b.rows.map(r => (text(9pt, r.at(0)), text(9pt, r.at(1)), align(right, text(9pt, r.at(2))))).flatten(),
    ))
    if b.after != "" { md(b.after) }
  } else {
    md(b.body)
  }
}

// ------------------------------------------------------------------ line table

#let cols = (1.25in, 1fr, 0.42in, 0.42in, 0.92in, 0.92in)

#let col-head = grid(
  columns: cols, inset: (x: 4pt, y: 3pt), stroke: (bottom: 0.8pt + ink),
  text(8.5pt, weight: "bold")[Items], text(8.5pt, weight: "bold")[Description],
  align(center, text(8.5pt, weight: "bold")[Unit]), align(center, text(8.5pt, weight: "bold")[Qty]),
  align(center, text(8.5pt, weight: "bold")[Unit Price]), align(right, text(8.5pt, weight: "bold")[Cost]),
)

#let line-cells(r) = (
  [#text(8.5pt, r.title) #if r.code != "" { linebreak(); text(6.5pt, fill: muted, r.code + "  |  " + r.id) } else { linebreak(); text(6.5pt, fill: muted, r.id) }],
  text(8.5pt, md(r.body)),
  align(center, text(8.5pt, r.unit)),
  align(center, text(8.5pt, r.qty)),
  if r.price_money { text(8.5pt, money(r.price)) } else { align(right, text(8.5pt, r.price)) },
  if r.at("excluded", default: false) { align(right, text(8.5pt, "Not included")) }
  else if r.at("owner", default: false) { text(8.5pt, fill: muted, money("(" + r.cost + ")")) }
  else { text(8.5pt, money(r.cost)) },
)

#let row-fill(r) = if r.kind == "pct" { pct-fill } else if r.kind == "alt" { altfill(r.alt) } else { none }

#let line-grid(rows) = grid(
  columns: cols, inset: (x: 4pt, y: 4pt),
  stroke: (x, y) => (bottom: 0.4pt + rule-c),
  fill: (x, y) => row-fill(rows.at(y)),
  ..rows.map(line-cells).flatten(),
)

#let totals-grid(totals) = grid(
  columns: (1fr, 0.92in, 0.92in), inset: (x: 4pt, y: 4pt),
  fill: (x, y) => if totals.at(y).at("alt", default: 0) > 0 { altfill(totals.at(y).alt) } else { none },
  ..totals.map(t => (
    grid.cell(colspan: 2, text(9.5pt, weight: "bold", t.label)),
    text(9.5pt, money(t.amount, bold: true)),
  )).flatten(),
)

#let section(s) = {
  let rows = s.rows
  let n = rows.len()
  // chunks: first two lines | one line each | last line + totals
  let chunks = ()
  if n <= 3 {
    chunks.push((rows: rows, totals: true))
  } else {
    chunks.push((rows: rows.slice(0, 2), totals: false))
    for r in rows.slice(2, n - 1) { chunks.push((rows: (r,), totals: false)) }
    chunks.push((rows: (rows.at(n - 1),), totals: true))
  }
  table(
    columns: (1fr), inset: 0pt, stroke: none,
    table.header(
      block(above: 0pt, below: 8pt, inset: (x: 4pt), text(12.5pt, weight: "bold", s.name)),
      col-head,
    ),
    ..chunks.map(c => {
      line-grid(c.rows)
      if c.totals {
        v(6pt)
        totals-grid(s.totals)
      }
    }),
  )
  v(4pt)
  rect(width: 100%, height: 5pt, fill: bar-fill, stroke: none)
  v(10pt)
}

// ------------------------------------------------------------------ page 1

#if d.company.logo != "" {
  align(center, image(d.company.logo, width: 3.1in))
} else {
  align(center, text(24pt, weight: "bold", d.company.name))
}
#v(4pt)
#align(center, text(9pt, fill: muted)[
  #d.company.address #h(1em) | #h(1em) Phone: #d.company.phone #h(1em) | #h(1em) Email: #d.company.email
])
#v(10pt)
#align(right, grid(
  columns: (auto, 0.9in), column-gutter: 8pt, row-gutter: 5pt,
  align(right, text(weight: "bold")[Proposal \#:]), d.proposal.number,
  align(right, text(weight: "bold")[Proposal Date:]), d.proposal.date,
  align(right, text(weight: "bold")[Proposal Revision:]), d.proposal.revision,
))
#v(6pt)
#text(12pt, weight: "bold")[Proposal for:]
#v(2pt)
#grid(columns: (0.75in, 1fr), row-gutter: 5pt,
  [Client:], d.client.name,
  ..if d.client.at("attention", default: "") != "" { ([Attn:], d.client.attention) } else { () },
  [Address:], d.client.address,
  [Project:], d.client.project,
  ..if d.client.at("po", default: "") != "" { ([PO \#:], d.client.po) } else { () },
)
#v(14pt)
#for (i, b) in d.intro.enumerate() {
  if b.title == "" and b.body.starts-with("As a reminder") {
    v(6pt)
    line(length: 100%, stroke: 0.6pt + rule-c)
    text(9.5pt, style: "italic", md(b.body))
    line(length: 100%, stroke: 0.6pt + rule-c)
  } else {
    if i > 0 { parbreak() }      // separate intro blocks (e.g. a cover letter and an about paragraph)
    text-block(b)
  }
}

// ------------------------------------------------------------------ changes from previous revision

#if d.changes != none {
  pagebreak(weak: true)
  section-heading[Changes from Rev #d.changes.from]
  line(length: 100%, stroke: 0.8pt + ink)
  if d.changes.notes.len() > 0 {
    for n in d.changes.notes [- #eval(n, mode: "markup")]
    v(4pt)
  }
  if d.changes.rows.len() > 0 {
    table(
      columns: (0.5in, 1.5in, 0.65in, 1fr, 0.85in, 0.85in),
      inset: (x: 4pt, y: 4pt), stroke: (x, y) => (bottom: if y == 0 { 0.8pt + ink } else { 0.4pt + rule-c }),
      table.header(..([Line], [Item], [Change], [Detail], align(right)[Before], align(right)[After])
        .map(c => text(8.5pt, weight: "bold", c))),
      ..d.changes.rows.map(r => (
        text(8.5pt, r.id), text(8.5pt, r.title), text(8.5pt, r.kind), text(8.5pt, md(r.details)),
        text(8.5pt, money(r.before)), text(8.5pt, money(r.after)),
      )).flatten(),
    )
  }
  block(breakable: false, above: 1em, grid(
    columns: (1fr, 1.2in, 1.2in), inset: (x: 4pt, y: 4pt), stroke: (x, y) => (bottom: 0.4pt + rule-c),
    text(9pt, weight: "bold")[], align(right, text(9pt, weight: "bold")[Rev #d.changes.from]),
    align(right, text(9pt, weight: "bold")[Rev #d.proposal.revision]),
    ..d.changes.summary.map(r => (text(9.5pt, weight: "bold", r.label), money(r.before), money(r.after, bold: true))).flatten(),
    text(9.5pt, weight: "bold")[Change], [], align(right, text(9.5pt, weight: "bold", d.changes.change)),
  ))
}

// ------------------------------------------------------------------ how to read

#if d.how_to_read.len() > 0 {
  pagebreak(weak: true)
  section-heading[How to read this proposal]
  for b in d.how_to_read { text-block(b) }
}

// ------------------------------------------------------------------ sections

#pagebreak(weak: true)
#for s in d.sections { section(s) }

// ------------------------------------------------------------------ schedule of values

#if d.sov != none {
  block(breakable: false, above: 1em)[
    #text(14pt, weight: "bold")[Schedule of Values]
    #v(2pt)
    #line(length: 100%, stroke: 0.8pt + ink)
    #grid(
      columns: (1fr, 1.3in, 0.8in), inset: (x: 4pt, y: 4pt),
      stroke: (x, y) => (bottom: 0.4pt + rule-c),
      fill: (x, y) => if y < d.sov.rows.len() and d.sov.rows.at(y).at("pctline", default: false) { pct-fill } else { none },
      ..d.sov.rows.map(r => (text(9.5pt, r.label), text(9.5pt, money(r.amount)), align(right, text(9.5pt, r.pct)))).flatten(),
      text(10pt, weight: "bold")[Total Price], money(d.sov.total, bold: true), align(right, text(10pt, weight: "bold")[100%]),
    )
  ]
}

// ------------------------------------------------------------------ totals + signature

#block(breakable: false, above: 1em)[
  #text(14pt, weight: "bold")[Total Proposed Costs]
  #v(2pt)
  #line(length: 100%, stroke: 0.8pt + ink)
  #grid(
    columns: (1fr, 1.3in), inset: (x: 4pt, y: 4pt),
    stroke: (x, y) => (bottom: 0.4pt + rule-c),
    fill: (x, y) => {
      let t = d.totals.at(y)
      if t.at("alt", default: 0) != 0 { altfill(t.alt) } else if t.style == "sub" { luma(242) } else { none }
    },
    ..d.totals.map(t => {
      let size = if t.style == "total" { 13pt } else if t.style == "incl" { 11pt } else { 10pt }
      (text(size, weight: "bold", t.label), text(size, money(t.amount, bold: true)))
    }).flatten(),
  )
  #if d.alternates.len() > 0 {
    v(6pt)
    for a in d.alternates {
      block(fill: altfill(a.n), inset: 6pt, radius: 2pt, width: 100%, text(9pt)[
        *#a.name.* #md(a.text)])
    }
  }
  #for b in d.totals_note { text(9.5pt, text-block(b)) }
]

#let sig-row(who) = table(
  columns: (2fr, 1.4fr, 1fr), rows: (0.55in, auto), stroke: 0.6pt + ink, inset: 4pt,
  [], [], [],
  align(center, text(8.5pt, who)), align(center, text(8.5pt)[Name]), align(center, text(8.5pt)[Date]),
)

#block(breakable: false, above: 1.5em)[
  #for b in d.signature {
    if b.body.starts-with("I confirm") {
      v(10pt)
      align(center, text(9pt, style: "italic", md(b.body)))
    } else { text-block(b) }
  }
  #v(6pt)
  #sig-row[Client Signature]
  #if d.at("company_signature", default: true) {
    v(8pt)
    sig-row(d.company.name)
  }
]

// ------------------------------------------------------------------ boilerplate groups

#for (i, g) in d.groups.enumerate() {
  // Kept Spec starts each group on a new page; compact documents (Convenient Woodworking) run them on
  if i == 0 or not d.at("compact_terms", default: false) { pagebreak(weak: true) }
  section-heading(g.heading)
  line(length: 100%, stroke: 0.8pt + ink)
  if g.payments.len() > 0 {
    block(breakable: false, grid(
      columns: (1fr, 1.3in), inset: (x: 4pt, y: 4pt),
      stroke: (x, y) => (bottom: 0.4pt + rule-c),
      ..g.payments.map(p => {
        let b = p.at("style", default: "") == "total"
        (text(weight: if b { "bold" } else { "regular" }, p.label), money(p.amount, bold: b))
      }).flatten(),
    ))
  }
  for b in g.blocks { text-block(b) }
}
