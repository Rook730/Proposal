// Shared look for change orders, the project ledger and the other company documents. The company's brand
// (Settings > Company > Brand) comes in data.json as company.brand; documents without one keep the classic look.
#let company-data = json("data.json").at("company", default: (:))
#let brand = {
  let c = company-data
  let b = c.at("brand", default: none)
  let base = (layout: "classic", ink: "#222B3A", accent: "#1F3A5F", header_fill: "#C8C7CB", font: "Carlito",
              heading_font: "", spaced_headings: false, logo_width_in: 3.1, footer: "")
  if b == none { base } else { base + b }
}
#let ink = rgb(brand.ink)
#let muted = luma(110)
#let rule-c = luma(185)
#let band = luma(235)
#let accent = rgb(brand.accent)
#let head-font = if brand.heading_font != "" { brand.heading_font } else { brand.font }
#let banded = brand.layout == "band"

// letter-spaced capitals for brands that use them (S C O P E)
#let spaced(t, size: 13pt, weight: "medium") = if brand.spaced_headings {
  text(font: head-font, size: size, weight: weight, tracking: 0.28em, upper(t))
} else { text(font: head-font, size: size, weight: "bold", t) }

// Header band (layout "band"): gray band across the top of every page, logo at left, angled stripes at right
#let band-header(logo, height: 0.78in) = {
  place(top + left, dx: -0.6in, dy: 0pt, block(width: 8.5in, height: height, fill: rgb(brand.header_fill), {
    if logo != "" { place(left + horizon, dx: 0.3in, image(logo, height: height * 0.66)) }
    for (i, x) in (6.55in, 6.95in, 7.35in).enumerate() {
      place(top + left, dx: x, polygon(fill: white,
        (0.16in, 0pt), (0.30in, 0pt), (0.14in, height), (0pt, height)))
    }
  }))
}

#let page-footer = context {
  let label = counter(page).display("1 of 1", both: true)
  if banded {
    grid(columns: (1fr, auto), align(left, text(7.5pt, fill: muted, brand.footer)),
         text(8pt, fill: muted, font: head-font)[Page #label])
  } else {
    align(center, text(8pt, fill: muted, label))
    if brand.footer != "" { align(center, text(7.5pt, fill: muted, brand.footer)) }
  }
}

#let setup(doc, title: "", logo: auto) = {
  let logo = if logo == auto { company-data.at("logo", default: "") } else { logo }
  set document(title: title)
  set page(paper: "us-letter",
    margin: if banded { (x: 0.6in, top: 1.15in, bottom: 0.75in) } else { (x: 0.6in, top: 0.6in, bottom: 0.75in) },
    header: if banded { band-header(logo) } else { none }, header-ascent: 0pt,
    footer: page-footer)
  set text(font: brand.font, size: 10pt, fill: ink)
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
  if banded {
    // the logo is in the page header; contact line and a spaced title under it
    align(right, text(8.5pt, fill: muted, font: head-font)[#c.address #h(0.6em) | #h(0.6em) #c.phone #h(0.6em) | #h(0.6em) #c.email])
    v(6pt)
    block(width: 100%, stroke: (bottom: 1.2pt + luma(185)), inset: (bottom: 5pt), spaced(title, size: 17pt))
    v(6pt)
    return
  }
  if c.logo != "" { align(center, image(c.logo, width: 2.6in)) } else { align(center, text(22pt, weight: "bold", c.name)) }
  v(2pt)
  align(center, text(9pt, fill: muted)[#c.address #h(1em) | #h(1em) Phone: #c.phone #h(1em) | #h(1em) Email: #c.email])
  v(8pt)
  let band-c = if c.at("accent", default: "") != "" { rgb(c.accent) } else { accent }
  block(width: 100%, fill: band-c, inset: (x: 8pt, y: 6pt), text(13pt, weight: "bold", fill: white, upper(title)))
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

#let heading-bar(t) = if brand.spaced_headings {
  block(sticky: true, above: 1.4em, below: 0.6em, width: 100%, stroke: (bottom: 1.2pt + luma(185)),
        inset: (left: 0.15in, bottom: 4pt), spaced(t, size: 11.5pt))
} else {
  block(sticky: true, above: 1.2em, below: 0.5em, width: 100%,
    stroke: (bottom: 0.8pt + ink), inset: (bottom: 3pt), text(11.5pt, weight: "bold", t))
}

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
