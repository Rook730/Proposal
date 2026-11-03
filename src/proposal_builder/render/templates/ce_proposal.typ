// Convenient Enterprises proposal (render/ce_document.py). Narrative modules with spaced headings, the fee
// lines as a cost table, both parties' signatures. The look comes from the company brand (common.typ).
#import "common.typ": *
#let d = json("data.json")
#show: setup.with(title: d.proposal.number + " " + d.client.project + " Proposal")
#set par(justify: false, leading: 0.6em, spacing: 1em)
#set list(indent: 0.15in, body-indent: 0.6em, spacing: 0.75em)
#set enum(indent: 0.15in, body-indent: 0.6em, spacing: 0.75em)
#set text(size: 9.5pt)

#let sub-head(t) = block(sticky: true, above: 1.1em, below: 0.6em, text(weight: "bold", t))

// ------------------------------------------------------------------ cost table

#let cost-row(r, fill: none) = (
  grid.cell(fill: fill, [#text(weight: "medium", r.title) #if r.body != "" { linebreak(); text(8.5pt, fill: muted, md(r.body)) }]),
  grid.cell(fill: fill, align(right, r.qty)), grid.cell(fill: fill, align(center, r.unit)),
  grid.cell(fill: fill, align(right, r.rate)), grid.cell(fill: fill, align(right, r.amount)),
)
#let cols = (1fr, 0.5in, 0.45in, 0.85in, 0.95in)

#let cost-table(c) = {
  for g in c.groups {
    block(breakable: false, above: 1em, {
      grid(columns: (1fr, auto), text(weight: "bold", g.name), text(8.5pt, fill: muted, style: "italic", g.label))
      v(2pt)
      grid(columns: cols, inset: (x: 4pt, y: 4pt), stroke: (x, y) => (bottom: if y == 0 { 0.8pt + ink } else { 0.4pt + rule-c }),
        ..([Item], align(right)[Qty], align(center)[Unit], align(right)[Rate], align(right)[Amount]).map(x => text(8.5pt, weight: "bold", x)),
        ..g.rows.map(r => cost-row(r)).flatten(),
        grid.cell(colspan: 4, align(right, text(weight: "bold")[Subtotal])), align(right, text(weight: "bold", g.subtotal)),
      )
    })
  }
  block(breakable: false, above: 1.2em, grid(columns: (1fr, 1.3in), inset: (x: 4pt, y: 5pt),
    stroke: (x, y) => (bottom: 0.4pt + rule-c),
    fill: (x, y) => if c.totals.at(y).style == "total" { band } else { none },
    ..c.totals.map(t => {
      let w = if t.style == "total" { "bold" } else { "regular" }
      let s = if t.style == "total" { 11pt } else { 9.5pt }
      (text(s, weight: w, style: if t.style == "note" { "italic" } else { "normal" }, t.label), align(right, text(s, weight: w, t.amount)))
    }).flatten(),
  ))
  if c.options.len() > 0 {
    block(breakable: false, above: 1.2em, {
      text(weight: "bold")[Options] + h(0.6em) + text(8.5pt, fill: muted, style: "italic")[Not included in the total above. Add any option at approval.]
      v(2pt)
      for o in c.options {
        block(fill: band, inset: 6pt, width: 100%, below: 4pt, {
          grid(columns: (1fr, auto), text(weight: "bold", o.name),
               text(weight: "bold")[#o.amount #h(0.8em) #text(weight: "regular", fill: muted)[Total with option: #o.total_with]])
          if o.text != "" { v(2pt); text(8.5pt, md(o.text)) }
          if o.rows.len() > 0 {
            v(3pt)
            grid(columns: cols, inset: (x: 4pt, y: 3pt), ..o.rows.map(r => cost-row(r)).flatten())
          }
        })
      }
    })
  }
}

// ------------------------------------------------------------------ Detailed depth tables

#let small-head(..cells) = cells.pos().map(x => text(8.5pt, weight: "bold", x))
#let rules = (x, y) => (bottom: if y == 0 { 0.8pt + ink } else { 0.4pt + rule-c })

#let bom-table(rows) = if rows.len() == 0 { text(fill: muted, style: "italic")[No items listed.] } else {
  grid(columns: (1fr, 1.05in, 0.45in, 0.95in, 0.75in, 0.8in), inset: (x: 4pt, y: 4pt), stroke: rules,
    ..small-head([Item], [Part number], align(right)[Qty], [Supplier], [Lead time], [Bought by]),
    ..rows.map(r => (
      [#r.item #if r.description != "" { linebreak(); text(8.5pt, fill: muted, r.description) }],
      text(8.5pt, r.pn), align(right, r.qty + " " + r.unit), text(8.5pt, r.supplier), text(8.5pt, r.lead),
      text(8.5pt, r.buyer))).flatten())
}

#let milestone-table(m) = block(breakable: false, grid(columns: (1.6in, 1fr, 0.6in, 1in), inset: (x: 4pt, y: 4pt),
  stroke: rules,
  ..small-head([Invoice], [When], align(right)[Share], align(right)[Amount]),
  ..m.rows.map(r => (text(weight: "medium", r.name), text(8.5pt, r.trigger), align(right, r.pct),
                     align(right, r.amount))).flatten(),
  grid.cell(colspan: 3, align(right, text(weight: "bold")[Fixed fee])), align(right, text(weight: "bold", m.fixed)),
))

#let compliance-table(rows) = if rows.len() == 0 { text(fill: muted, style: "italic")[No requirements entered.] } else {
  grid(columns: (0.6in, 1fr, 1.45in), inset: (x: 4pt, y: 3pt), stroke: rules,
    ..small-head([Section], [Requirement], [Compliance]),
    ..rows.map(r => (
      text(8.5pt, r.number),
      [#pad(left: (r.level - 1) * 0.12in, text(8.5pt, weight: if r.level == 1 { "medium" } else { "regular" }, r.heading))
       #if r.response != "" { linebreak(); pad(left: (r.level - 1) * 0.12in, text(8pt, fill: muted, r.response)) }],
      text(8.5pt, weight: if r.deviate { "bold" } else { "regular" }, r.status))).flatten())
}

#let commercial-table(c) = {
  block(breakable: false, grid(columns: (1fr, 1.2in), inset: (x: 4pt, y: 4pt), stroke: rules,
    ..small-head([Category], align(right)[Amount]),
    ..c.rows.map(r => (r.label, align(right, r.amount))).flatten(),
    text(weight: "bold")[Total], align(right, text(weight: "bold", c.total))))
  if c.major.len() > 0 {
    v(4pt)
    text(weight: "medium")[Major purchased components (\$10,000 or more)]
    grid(columns: (1fr, 0.8in), inset: (x: 4pt, y: 3pt), stroke: rules,
      ..small-head([Item], align(right)[Qty]),
      ..c.major.map(r => ([#r.item #if r.description != "" { linebreak(); text(8.5pt, fill: muted, r.description) }],
                          align(right, r.qty + " " + r.unit))).flatten())
  }
}

#let timeline-chart(t) = if t.rows.len() == 0 { [] } else {
  let total = calc.max(t.weeks, 1)
  block(breakable: false, grid(columns: (1.9in, 1fr), inset: (x: 4pt, y: 4pt), stroke: rules,
    ..small-head([Phase], [Weeks after approval (#t.label total)]),
    ..t.rows.map(r => (
      [#text(weight: "medium", r.name) \ #text(8pt, fill: muted, r.span)],
      [#box(width: 100%, height: 0.16in, {
         place(left + horizon, dx: r.start / total * 100%,
               rect(width: calc.max(r.weeks / total, 0.01) * 100%, height: 0.16in, fill: luma(150), stroke: none))
       })
       #if r.gate != "" { linebreak(); text(8pt, fill: muted, style: "italic")[Waits on: #r.gate] }],
    )).flatten(),
  ))
}

// ------------------------------------------------------------------ signatures

#let sign-block(who) = block(breakable: false, above: 1.6em, {
  text(weight: "bold", underline(who))
  v(10pt)
  for label in ([Signature:], [Name (print):], [Date:]) {
    block(above: 0pt, below: 12pt, width: 100%, stroke: (bottom: 0.6pt + ink), inset: (bottom: 3pt), label)
  }
})

#let block-item(b) = {
  if b.title != "" { sub-head(b.title) }
  if b.kind == "cost" { cost-table(d.cost) }
  else if b.kind == "bom" { bom-table(d.bom) }
  else if b.kind == "milestones" { milestone-table(d.milestones) }
  else if b.kind == "timeline" { timeline-chart(d.timeline) }
  else if b.kind == "compliance" { compliance-table(d.compliance) }
  else if b.kind == "commercial" { commercial-table(d.commercial) }
  else if b.kind == "signatures" {
    sign-block(d.signatures.client + " (Client):")
    v(10pt)
    sign-block(d.signatures.company + " (Consultant):")
  }
  else { block(above: 0.9em, below: 0.9em, md(b.body)) }
}

// ------------------------------------------------------------------ first page

#align(right, text(9pt, font: head-font)[#d.company.address \ #d.company.phone | #d.company.email])
#v(10pt)
#block(width: 100%, stroke: (bottom: 1.6pt + luma(185)), inset: (left: 0.25in, bottom: 6pt), spaced("Proposal", size: 20pt))
#pad(left: 0.25in, text(9pt, font: head-font, tracking: 0.12em)[#d.proposal.date #h(0.8em) | #h(0.8em) Rev: #d.proposal.revision])
#v(10pt)
#pad(left: 0.25in, grid(columns: (1fr, 1fr), column-gutter: 16pt,
  [#text(weight: "bold", underline[Prepared for:]) \
   #d.client.name
   #if d.client.attention != "" [ \ ATTN: #d.client.attention ]
   #if d.client.address != "" [ \ #d.client.address ]
   #if d.client.po != "" [ \ PO \#: #d.client.po ]],
  [#text(weight: "bold", underline[Project:]) \ #d.client.project],
))
#v(14pt)
#for b in d.intro { block-item(b) }

// ------------------------------------------------------------------ modules

#for m in d.modules {
  heading-bar(m.heading)
  for b in m.blocks { block-item(b) }
}
