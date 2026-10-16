#import "common.typ": *
#let d = json("data.json")
#show: setup.with(title: "Final Project Ledger " + d.proposal.number)

#letterhead(d.company, "Final Project Ledger")
#info(d.client, d.proposal, extra: (("Ledger Date:", d.date),))

#heading-bar[1. Contract Summary]
#amount-table(d.contract.map(r => (r.label, r.amount, r.style)))

#heading-bar[2. Approved Change Orders]
#if d.cos.len() == 0 [No change orders were approved.] else {
  table(
    columns: (0.85in, 1fr, 0.8in, 0.95in, 0.95in, 0.95in, 0.95in), inset: (x: 4pt, y: 4pt),
    stroke: (x, y) => (bottom: if y == 0 { 0.8pt + ink } else { 0.4pt + rule-c }),
    table.header(..([CO \#], [Description], [Approved], [Funding], align(right)[Price], align(right)[Contingency],
      align(right)[Billed]).map(c => text(8.5pt, weight: "bold", c))),
    ..d.cos.map(c => (text(9pt, c.number), text(9pt, c.title), text(9pt, c.approved), text(9pt, c.funding),
      text(9pt, money(c.price)), text(9pt, money(c.contingency)), text(9pt, money(c.billed)))).flatten(),
  )
}
#v(4pt)
#amount-table(d.co_summary.map(r => (r.label, r.amount, r.style)))

#heading-bar[3. Line Reconciliation]
#if d.lines.len() == 0 [All lines are carried at their contract amounts.] else {
  table(
    columns: (0.5in, 1fr, 0.95in, 0.95in, 0.95in), inset: (x: 4pt, y: 4pt),
    stroke: (x, y) => (bottom: if y == 0 { 0.8pt + ink } else { 0.4pt + rule-c }),
    table.header(..([Line], [Item], align(right)[Budgeted], align(right)[Actual], align(right)[Variance])
      .map(c => text(8.5pt, weight: "bold", c))),
    ..d.lines.map(l => (text(9pt, l.id), text(9pt)[#l.title#if l.note != "" [ #text(7.5pt, fill: muted)[(#l.note)]]],
      text(9pt, money(l.budget)), text(9pt, money(l.actual)), text(9pt, money(l.variance)))).flatten(),
  )
  text(8.5pt, fill: muted)[Lines not listed are carried at their contract amounts.]
}
#v(4pt)
#amount-table(d.variance_summary.map(r => (r.label, r.amount, r.style)))

#heading-bar[4. Payments Received]
#if d.payments.len() == 0 [No payments recorded.] else {
  table(
    columns: (0.9in, 1fr, 1in, 1.2in), inset: (x: 4pt, y: 4pt),
    stroke: (x, y) => (bottom: if y == 0 { 0.8pt + ink } else { 0.4pt + rule-c }),
    table.header(..([Draw], [Milestone], [Date Received], align(right)[Amount]).map(c => text(8.5pt, weight: "bold", c))),
    ..d.payments.map(p => (text(9pt, p.draw), text(9pt, p.milestone), text(9pt, p.date), text(9pt, money(p.amount)))).flatten(),
  )
}

#block(breakable: false)[
  #heading-bar[5. Final Reconciliation]
  #amount-table(d.final.map(r => (r.label, r.amount, r.style)))
  #v(8pt)
  #text(9pt, style: "italic", d.note)
]
