#import "common.typ": *
#let d = json("data.json")
#show: setup.with(title: "Quote Comparison " + d.proposal.number)

#letterhead(d.company, "Quote Comparison")
#info(d.client, d.proposal, extra: (("Compared:", d.today),))

#v(6pt)
#text(12pt, weight: "bold", d.scope)
#if d.lines.len() > 0 {
  v(2pt)
  text(9pt, fill: muted)[Proposal lines: #d.lines.map(l => l.id + " " + l.title).join(", ")]
}

#heading-bar[Quotes]
#table(
  columns: (1.7in, 1.1in, 0.8in, 0.8in, 1fr), inset: (x: 4pt, y: 5pt),
  stroke: (x, y) => (bottom: if y == 0 { 0.8pt + ink } else { 0.4pt + rule-c }),
  table.header(..([Contractor], align(right)[Price], [Received], [Valid until], [Notes])
    .map(c => text(8.5pt, weight: "bold", c))),
  ..d.rows.map(r => (
    text(9.5pt, weight: "bold", r.company), text(9.5pt, money(r.amount)),
    text(9pt, r.received), text(9pt, r.valid), text(9pt, md(r.notes)),
  )).flatten(),
)

#v(6pt)
#text(9pt, style: "italic", md(d.note))
