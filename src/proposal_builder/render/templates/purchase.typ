#import "common.typ": *
#let d = json("data.json")
#show: setup.with(title: "Purchase List " + d.proposal.number)

#letterhead(d.company, "Purchase List")
#info(d.client, d.proposal, extra: (("Printed:", d.printed),))
#v(4pt)
#text(8.5pt, fill: muted)[Internal. Base lines of Rev #d.proposal.revision, totaled across the project and rounded up to whole units. Estimated cost uses the current price references.]

#for g in d.groups {
  heading-bar(g.title)
  table(
    columns: (1fr, 1.15in, 0.75in, 0.85in, 0.7in, 0.8in, 0.75in), inset: (x: 3pt, y: 3.5pt),
    stroke: (x, y) => (bottom: if y == 0 { 0.8pt + ink } else { 0.4pt + rule-c }),
    table.header(..([Item], [Part no. / Supplier], align(right)[Needed], align(right)[Buy], align(right)[Unit cost],
      align(right)[Est. cost], [Lines]).map(c => text(8pt, weight: "bold", c))),
    ..g.rows.map(r => (
      text(9pt)[#r.name#if r.date != "" [ #linebreak() #text(7pt, fill: muted)[priced #r.date]]],
      text(8pt)[#r.part#if r.part != "" and r.supplier != "" { linebreak() }#r.supplier],
      align(right, text(9pt, r.needed)), align(right, text(9pt, weight: "bold", r.buy)),
      align(right, text(9pt, r.unit_cost)), align(right, text(9pt, r.cost)), text(8pt, r.lines),
    )).flatten(),
    [], [], [], [], align(right, text(8.5pt, weight: "bold")[Total]), align(right, text(9pt, weight: "bold", g.total)), [],
  )
}

#v(8pt)
#amount-table((("Estimated materials total", d.total, "total"),))
#if d.skipped != "" {
  v(6pt)
  text(8.5pt, fill: muted)[Lines with no build sheet (not in this list): #d.skipped]
}
