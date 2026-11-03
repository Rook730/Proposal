// Convenient Enterprises estimate (render/ce_document.py): the proposal's cost section as an itemized document
// for the client's records and PO. Options are listed under the total, never in it.
#import "common.typ": *
#let d = json("data.json")
#show: setup.with(title: "Estimate " + d.estimate.number)
#set text(size: 9.5pt)

#align(right, text(9pt, font: head-font)[#d.company.legal \ #d.company.address \ #d.company.phone | #d.company.email])
#v(8pt)
#block(width: 100%, stroke: (bottom: 1.6pt + luma(185)), inset: (left: 0.25in, bottom: 6pt), spaced("Estimate", size: 20pt))
#v(6pt)
#grid(columns: (1fr, auto), column-gutter: 20pt,
  pad(left: 0.25in)[#text(weight: "bold", underline[Bill to:]) \
    #d.client.name
    #if d.client.attention != "" [ \ ATTN: #d.client.attention ]
    #if d.client.address != "" [ \ #d.client.address ]
    #if d.client.po != "" [ \ PO \#: #d.client.po ]],
  grid(columns: (auto, auto), column-gutter: 8pt, row-gutter: 5pt,
    ..(("Estimate #:", d.estimate.number + "  Rev " + d.estimate.revision), ("Estimate date:", d.estimate.date),
       ("Valid until:", d.estimate.valid), ("Total (USD):", d.estimate.total),
       ..if d.estimate.deposit != "$0.00" { (("Deposit requested:", d.estimate.deposit),) } else { () })
      .map(p => (align(right, text(weight: "bold", p.at(0))), p.at(1))).flatten()),
)
#v(4pt)
#text(11pt, weight: "bold", d.estimate.title)

#let cols = (1fr, 0.5in, 0.45in, 0.85in, 0.95in)
#let row(r) = (
  [#text(weight: "medium", r.title) #if r.body != "" { linebreak(); text(8.5pt, fill: muted, md(r.body)) }],
  align(right, r.qty), align(center, r.unit), align(right, r.rate), align(right, r.amount),
)

#for g in d.cost.groups {
  block(breakable: false, above: 0.8em, {
    grid(columns: (1fr, auto), text(weight: "bold", g.name), text(8.5pt, fill: muted, style: "italic", g.label))
    v(2pt)
    grid(columns: cols, inset: (x: 4pt, y: 3pt), stroke: (x, y) => (bottom: if y == 0 { 0.8pt + ink } else { 0.4pt + rule-c }),
      ..([Item], align(right)[Qty], align(center)[Unit], align(right)[Price], align(right)[Amount]).map(x => text(8.5pt, weight: "bold", x)),
      ..g.rows.map(row).flatten(),
      grid.cell(colspan: 4, align(right, text(weight: "bold")[Subtotal])), align(right, text(weight: "bold", g.subtotal)),
    )
  })
}

#block(breakable: false, above: 1.2em, grid(columns: (1fr, 1.3in), inset: (x: 4pt, y: 5pt),
  stroke: (x, y) => (bottom: 0.4pt + rule-c),
  fill: (x, y) => if d.cost.totals.at(y).style == "total" { band } else { none },
  ..d.cost.totals.map(t => {
    let w = if t.style == "total" { "bold" } else { "regular" }
    (text(weight: w, t.label), align(right, text(weight: w, t.amount)))
  }).flatten(),
))

#if d.cost.options.len() > 0 {
  block(breakable: false, above: 1.4em, {
    text(weight: "bold")[Optional items (not included in the total)]
    v(2pt)
    grid(columns: (1fr, 1.3in, 1.3in), inset: (x: 4pt, y: 4pt), stroke: (x, y) => (bottom: 0.4pt + rule-c),
      ..([Option], align(right)[Adds], align(right)[Total with option]).map(x => text(8.5pt, weight: "bold", x)),
      ..d.cost.options.map(o => (
        [#text(weight: "medium", o.name) #if o.text != "" { linebreak(); text(8.5pt, fill: muted, md(o.text)) }],
        align(right, o.amount), align(right, o.total_with))).flatten(),
    )
  })
}

#if d.note != "" { v(1em); text(7.5pt, fill: muted, d.note) }
