#import "common.typ": *
#let d = json("data.json")
#show: setup.with(title: "Request for Quote " + d.project.number)

#letterhead(d.company, "Request for Quote")
#grid(
  columns: (1fr, auto), column-gutter: 16pt,
  grid(columns: (0.75in, 1fr), row-gutter: 4pt,
    text(weight: "bold")[To:], d.to.company,
    ..if d.to.contact != "" { (text(weight: "bold")[Attn:], d.to.contact) } else { () },
    ..if d.to.email != "" or d.to.phone != "" {
      (text(weight: "bold")[Contact:], (d.to.phone, d.to.email).filter(x => x != "").join("  |  ")) } else { () },
  ),
  grid(columns: (auto, auto), column-gutter: 8pt, row-gutter: 4pt,
    ..(("Project #:", d.project.number), ("Project:", d.project.name), ("Site:", d.project.address),
       ("Date:", d.project.date), ("From:", d.project.from))
      .map(p => (align(right, text(weight: "bold", p.at(0))), p.at(1))).flatten()),
)

#v(6pt)
#text(9.5pt, md(d.note))

#heading-bar[Scope]
#table(
  columns: (0.5in, 1.5in, 1fr, 0.45in, 0.55in), inset: (x: 4pt, y: 4pt),
  stroke: (x, y) => (bottom: if y == 0 { 0.8pt + ink } else { 0.4pt + rule-c }),
  table.header(..([ID], [Item], [Description], align(center)[Unit], align(right)[Qty])
    .map(c => text(8.5pt, weight: "bold", c))),
  ..d.lines.map(l => (
    text(9pt, l.id),
    text(9pt)[#l.title#if l.alt != "" [ #linebreak() #text(7.5pt, fill: muted, l.alt)]],
    text(9pt, md(l.body)),
    align(center, text(9pt, l.unit)),
    align(right, text(9pt, l.qty)),
  )).flatten(),
)

#v(1.2em)
#block(breakable: false)[
  #heading-bar[Quote]
  #grid(columns: (1.6in, 1fr), row-gutter: 14pt, inset: (y: 2pt),
    text(weight: "bold")[Total price:], line(length: 100%, stroke: 0.5pt + rule-c),
    text(weight: "bold")[Valid until:], line(length: 100%, stroke: 0.5pt + rule-c),
    text(weight: "bold")[Lead time:], line(length: 100%, stroke: 0.5pt + rule-c),
    text(weight: "bold")[Exclusions / notes:], line(length: 100%, stroke: 0.5pt + rule-c),
    [], line(length: 100%, stroke: 0.5pt + rule-c),
  )
]
