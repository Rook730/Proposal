#import "common.typ": *
#let d = json("data.json")
#show: setup.with(title: "Change Order " + d.co.number)

#letterhead(d.company, "Change Order")
#info(d.client, d.proposal, extra: (("Change Order No.:", d.co.number), ("Requested Date:", d.co.requested),
  ..if d.co.approved != "" { (("Approved:", d.co.approved),) } else { () }))
#if d.co.title != "" { v(6pt); text(11pt, weight: "bold", d.co.title) }

#heading-bar[Itemized Changes]
#table(
  columns: (1fr, 0.75in, 1fr, 0.95in, 0.95in), inset: (x: 4pt, y: 4pt),
  stroke: (x, y) => (bottom: if y == 0 { 0.8pt + ink } else { 0.4pt + rule-c }),
  table.header(..([Description], [Action], [Change], align(right)[Original Cost], align(right)[Final Cost])
    .map(c => text(8.5pt, weight: "bold", c))),
  ..d.co.items.map(i => (
    text(9pt, md(i.description)), text(9pt, i.action), text(9pt)[#md(i.change)#if i.lines != "" [ #linebreak() #text(7.5pt, fill: muted)[Lines: #i.lines]]],
    text(9pt, money(i.original)), text(9pt, money(i.final)),
  )).flatten(),
)

#heading-bar[Pricing]
#amount-table(d.co.pricing.map(r => (r.label, r.amount, r.style)))

#for s in d.co.sections {
  heading-bar(s.title)
  md(s.body)
}

#v(1.4em)
#block(breakable: false, signatures(((("Recommended by", d.co.recommended_by)), ("Accepted and Approved by", d.co.approved_by))))
