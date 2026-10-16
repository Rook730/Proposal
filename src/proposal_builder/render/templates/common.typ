// Shared look for change orders and the project ledger (proposal.typ keeps its own copy).
#let ink = rgb("#222B3A")
#let muted = luma(110)
#let rule-c = luma(185)
#let band = luma(235)
#let accent = rgb("#1F3A5F")

#let setup(doc, title: "") = {
  set document(title: title)
  set page(paper: "us-letter", margin: (x: 0.6in, top: 0.6in, bottom: 0.75in),
    footer: context align(center, text(8pt, fill: muted, counter(page).display("1 of 1", both: true))))
  set text(font: "Carlito", size: 10pt, fill: ink)
  set par(leading: 0.55em, spacing: 0.9em)
  set list(indent: 0.6em, body-indent: 0.5em)
  set table.cell(breakable: false)
  doc
}

#let md(s) = if s == none or s == "" { [] } else { eval(s, mode: "markup") }

#let money(s, bold: false) = {
  let w = if bold { "bold" } else { "regular" }
  if s == "" { [] } else {
    grid(columns: (auto, 1fr), text(weight: w)[\$], align(right, text(weight: w, s)))
  }
}

#let letterhead(c, title) = {
  if c.logo != "" { align(center, image(c.logo, width: 2.6in)) } else { align(center, text(22pt, weight: "bold", c.name)) }
  v(2pt)
  align(center, text(9pt, fill: muted)[#c.address #h(1em) | #h(1em) Phone: #c.phone #h(1em) | #h(1em) Email: #c.email])
  v(8pt)
  block(width: 100%, fill: accent, inset: (x: 8pt, y: 6pt), text(13pt, weight: "bold", fill: white, upper(title)))
  v(6pt)
}

#let info(client, proposal, extra: ()) = grid(
  columns: (1fr, auto), column-gutter: 16pt,
  grid(columns: (0.75in, 1fr), row-gutter: 4pt,
    text(weight: "bold")[Client:], client.name,
    text(weight: "bold")[Address:], client.address,
    text(weight: "bold")[Project:], client.project),
  grid(columns: (auto, auto), column-gutter: 8pt, row-gutter: 4pt,
    ..(("Proposal #:", proposal.number), ("Proposal Date:", proposal.date), ("Proposal Revision:", proposal.revision),
       ..extra).map(p => (align(right, text(weight: "bold", p.at(0))), p.at(1))).flatten()),
)

#let heading-bar(t) = block(sticky: true, above: 1.2em, below: 0.5em, width: 100%,
  stroke: (bottom: 0.8pt + ink), inset: (bottom: 3pt), text(11.5pt, weight: "bold", t))

// rows: array of (label, amount, style) with style "", "bold", "total"
#let amount-table(rows, label-w: 1fr) = grid(
  columns: (label-w, 1.3in), inset: (x: 4pt, y: 4pt),
  stroke: (x, y) => (bottom: 0.4pt + rule-c),
  fill: (x, y) => if rows.at(y).at(2) == "total" { band } else { none },
  ..rows.map(r => {
    let b = r.at(2) != ""
    let big = r.at(2) == "total"
    (text(if big { 11pt } else { 10pt }, weight: if b { "bold" } else { "regular" }, r.at(0)),
     text(if big { 11pt } else { 10pt }, money(r.at(1), bold: b)))
  }).flatten(),
)

#let signatures(rows) = table(
  columns: (1.6in, 1.8in, 1.6in, 1fr), stroke: 0.6pt + ink, inset: 5pt,
  [], align(center, text(8.5pt, weight: "bold")[Name]), align(center, text(8.5pt, weight: "bold")[Signature]),
  align(center, text(8.5pt, weight: "bold")[Date]),
  ..rows.map(r => (text(9pt, weight: "bold", r.at(0)), text(9pt, r.at(1)), [], [])).flatten().map(c => box(height: 0.35in, c)),
)
