"""Build the data the Typst template prints, and compile it to PDF or PNG pages.

Everything client-facing is decided here: which lines and blocks print, the
section total rows, the totals block and the payment amounts. The template
only lays it out.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from decimal import Decimal
from importlib import resources
from pathlib import Path

from ..calc import Results, calculate, payment_schedule, render, variable_map
from ..models import Boilerplate, Catalog, Performer, PriceSource, Settings
from ..proposal import Line, Project, Revision
from .markup import escape, md_to_typst

PERFORMER_NOTE = {
    Performer.CW: "Performed by Convenient Woodworking.",
    Performer.SUB: "Performed by a licensed subcontractor.",
    Performer.CLIENT: "Owner-furnished.",
}


def fmt_money(v: Decimal | None) -> str:
    if v is None:
        return ""
    if v == 0:
        return "-"
    s = f"{abs(v):,.2f}"
    return f"({s})" if v < 0 else s


def fmt_qty(v: Decimal) -> str:
    v = v.normalize()
    s = f"{v:f}"
    return s


def fmt_pct(v: Decimal) -> str:
    return f"{(v * 100).normalize():f}%"


def _line_body(ln: Line, variables: dict[str, str]) -> str:
    parts = []
    if ln.is_allowance:
        parts.append("*Allowance.*")
    note = PERFORMER_NOTE.get(ln.performer)
    if ln.owner_furnished and note is None:
        note = PERFORMER_NOTE[Performer.CLIENT]          # owner-supplied always says so
    if note and not (ln.notes or "").startswith(note):
        parts.append(f"_{escape(note)}_")
    text = []
    if ln.print_general and ln.general_description:
        text.append(render(ln.general_description, variables))
    if ln.notes:
        text.append(render(ln.notes, variables))
    body = md_to_typst("\n\n".join(text))
    return " ".join(parts + ([body] if body else []))


RATE_PERFORMERS = (Performer.KEPT_SPEC, Performer.CW)


def rates_table(rev: Revision, catalog: Catalog) -> list[list[str]]:
    """Hourly rates billed by Kept Spec Advisors and Convenient Woodworking on this proposal.

    Taken from the proposal's own rate lines (snapshot), not the live catalog, so catalog
    edits never change a saved proposal."""
    seen: dict[tuple, list[str]] = {}
    for ln in sorted(rev.lines, key=lambda l: (l.performer is not Performer.KEPT_SPEC, l.section, l.order)):
        if ln.price_basis is not PriceSource.RATE or ln.performer not in RATE_PERFORMERS or ln.unit_price is None:
            continue
        key = (ln.performer, ln.rate_key, ln.unit_price)
        if key in seen:
            continue
        r = catalog.rate(ln.rate_key or "")
        seen[key] = [r.name if r else (ln.rate_key or ln.title), ln.performer.value,
                     f"${ln.unit_price:,.2f} / {ln.unit}"]
    return list(seen.values())


def document_variables(res: Results, settings: Settings) -> dict[str, str]:
    """Values that exist only once totals are known; usable in boilerplate."""
    ps = payment_schedule(res.base.total, settings)
    return {"total_price": f"${res.base.total:,.2f}", "subtotal": f"${res.base.subtotal:,.2f}",
            "deposit_amount": f"${ps['deposit']:,.2f}", "progress_amount": f"${ps['progress']:,.2f}",
            "retainage_amount": f"${ps['retainage']:,.2f}"}


def _changes(diff) -> dict | None:
    if diff is None or diff.empty:
        return None
    rows = [{"id": c.line_id, "title": c.title, "kind": c.kind.capitalize(), "details": md_to_typst("; ".join(c.details)),
             "before": fmt_money(c.old_cost) if c.old_cost is not None else "",
             "after": fmt_money(c.new_cost) if c.new_cost is not None else ""} for c in diff.changes]
    diffv = diff.total_change
    summary = [
        {"label": "Subtotal (less % items)", "before": fmt_money(diff.old_subtotal), "after": fmt_money(diff.new_subtotal)},
        {"label": "Total Price", "before": fmt_money(diff.old_total), "after": fmt_money(diff.new_total)},
    ]
    return {"from": diff.old_rev, "rows": rows, "notes": [escape(n) for n in diff.notes], "summary": summary,
            "change": (("+" if diffv > 0 else "-") + f"${abs(diffv):,.2f}") if diffv else "no change"}


def _sov(rev: Revision, res: Results, catalog: Catalog) -> dict:
    total = res.base.total
    rows = []
    for sec_num in rev.sections:
        base = res.base.section_base.get(sec_num)
        if base is None:
            continue
        sec = catalog.section(sec_num)
        rows.append({"label": sec.name if sec else str(sec_num), "amount": fmt_money(base),
                     "pct": f"{(base / total * 100):.1f}%" if total else ""})
    for lid, amt in res.base.percent_items.items():
        ln = rev.line(lid)
        rows.append({"label": ln.title if ln else lid, "amount": fmt_money(amt),
                     "pct": f"{(amt / total * 100):.1f}%" if total else "", "pctline": True})
    return {"rows": rows, "total": fmt_money(total)}


def build_document(project: Project, rev: Revision, settings: Settings, catalog: Catalog,
                   boilerplate: Boilerplate, results: Results | None = None, diff=None) -> dict:
    res = results or calculate(rev, settings, catalog.stock_classes, project)
    v = variable_map(project, rev, settings)
    v.update(document_variables(res, settings))
    alt_nums = sorted(res.alternates)

    # ---------------------------------------------------------------- sections
    sections = []
    for sec_num in rev.sections:
        lines = rev.section_lines(sec_num)
        if not lines:
            continue
        sec = catalog.section(sec_num)
        name = sec.name if sec else str(sec_num)
        rows = []
        for ln in lines:
            lr = res.lines[ln.id]
            if ln.is_percent:
                amount = res.base.percent_items.get(ln.id) if ln.alternate is None else None
                price = fmt_pct(lr.unit_price)
            else:
                amount = lr.cost
                price = fmt_money(lr.unit_price) if lr.unit_price else "-"
            kind = "alt" if ln.alternate else ("pct" if ln.is_percent else "base")
            owner = ln.owner_furnished and not ln.is_percent and bool(amount)
            rows.append({
                "id": ln.id, "code": str(ln.code) if ln.code is not None else "", "title": ln.title,
                "body": _line_body(ln, v), "unit": ln.unit, "qty": fmt_qty(lr.qty), "price": price,
                "price_money": not ln.is_percent and bool(lr.unit_price),
                "cost": fmt_money(amount) if amount is not None else "",
                "kind": kind, "alt": ln.alternate or 0, "owner": owner,
            })
        has_pct = any(ln.is_percent for ln in lines)
        alts_here = [n for n in alt_nums
                     if any(ln.alternate == n for ln in lines)
                     or any(rid in rev.alternate(n).removes for rid in (ln.id for ln in lines))]
        totals = []
        base_label = f"{name} Totals"
        if has_pct:
            totals.append({"label": f"{base_label} (Excluding % items):",
                           "amount": fmt_money(res.base.section_total(sec_num, with_pct=False))})
            totals.append({"label": f"{base_label} (Including % items):",
                           "amount": fmt_money(res.base.section_total(sec_num))})
        elif alts_here:
            totals.append({"label": f"{base_label} (Excluding alternate items):",
                           "amount": fmt_money(res.base.section_total(sec_num))})
        else:
            totals.append({"label": f"{base_label}:", "amount": fmt_money(res.base.section_total(sec_num))})
        for n in alts_here:
            totals.append({"label": f"{base_label} (With alternate {n} items):" if len(alt_nums) > 1
                           else f"{base_label} (With alternate items):",
                           "amount": fmt_money(res.alternates[n].section_total(sec_num, with_pct=False)),
                           "alt": n})
        sections.append({"number": sec_num, "name": name, "rows": rows, "totals": totals})

    # ---------------------------------------------------------------- totals block
    single = len(alt_nums) == 1
    alt_label = (lambda n: "*Alternate") if single else (lambda n: f"*Alternate {n}")
    totals = [{"label": "Subtotal (less % items):", "amount": fmt_money(res.base.subtotal), "style": "sub"}]
    for n in alt_nums:
        totals.append({"label": f"Subtotal {alt_label(n)} (less % items):",
                       "amount": fmt_money(res.alternates[n].subtotal), "style": "sub", "alt": n})
    totals.append({"label": "Total Price", "amount": fmt_money(res.base.total), "style": "total"})
    for n in alt_nums:
        totals.append({"label": f"Total Price {alt_label(n)}", "amount": fmt_money(res.alternates[n].total),
                       "style": "total", "alt": n})
    for c in res.combinations:
        totals.append({"label": f"Total Price *{c.name.replace('Alt', 'Alternate')}",
                       "amount": fmt_money(c.total), "style": "total", "alt": -1})
    if res.base.owner_supplied:
        totals.append({"label": "Total *Incl. Owner-supplied items",
                       "amount": fmt_money(res.base.total_incl_owner), "style": "incl"})
    for n in alt_nums:
        alt = rev.alternate(n)
        touches_owner = any(ln.owner_furnished and (ln.alternate == n or ln.id in alt.removes) for ln in rev.lines)
        if touches_owner and res.alternates[n].owner_supplied != res.base.owner_supplied:
            totals.append({"label": f"Total {alt_label(n)} Incl. Owner-supplied items",
                           "amount": fmt_money(res.alternates[n].total_incl_owner), "style": "incl", "alt": n})
    alt_descriptions = [{"n": a.number, "name": a.name, "text": md_to_typst(render(a.description, v))}
                        for a in sorted(rev.alternates, key=lambda a: a.number) if a.description or a.name]

    # ---------------------------------------------------------------- boilerplate
    blocks_by_heading: dict[str, list] = {}
    for b in sorted(rev.blocks, key=lambda b: b.order):
        if not b.on:
            continue
        if b.heading == "Totals" and not alt_nums:
            continue
        body = render(b.body, v)
        item = {"title": b.title, "kind": "text", "body": md_to_typst(body)}
        if "{units_table}" in b.body:
            item = {"title": b.title, "kind": "units",
                    "units": [[u.code, u.description] for u in catalog.units]}
        elif "{rates_table}" in b.body:
            before, _, after = b.body.partition("{rates_table}")
            item = {"title": b.title, "kind": "rates", "rows": rates_table(rev, catalog),
                    "before": md_to_typst(render(before, v)), "after": md_to_typst(render(after, v))}
        blocks_by_heading.setdefault(b.heading, []).append(item)

    ps = payment_schedule(res.base.total, settings)
    payments = [
        {"label": f"Deposit due at signing ({fmt_pct(settings.deposit_pct)})", "amount": fmt_money(ps["deposit"])},
        {"label": "Construction progress payments", "amount": fmt_money(ps["progress"])},
        {"label": f"Retainage due at final completion ({fmt_pct(settings.retainage_pct)})",
         "amount": fmt_money(ps["retainage"])},
        {"label": "Total Price", "amount": fmt_money(res.base.total), "style": "total"},
    ]

    special = {"Intro", "How to read this proposal", "Totals", "Signature"}
    order = list(boilerplate.headings) + [h for h in blocks_by_heading if h not in boilerplate.headings]
    groups = [{"heading": h, "blocks": blocks_by_heading[h],
               "payments": payments if h == "Payment Schedule" else []}
              for h in order if h not in special and blocks_by_heading.get(h)]

    c = settings.company
    return {
        "company": {"name": c.dba, "legal": c.legal_name, "address": c.address, "phone": c.phone,
                    "email": c.email, "logo": "logo.png" if c.logo_path else ""},
        "proposal": {"number": project.number, "date": rev.proposal_date.strftime("%Y.%m.%d"),
                     "revision": rev.rev},
        "client": {"name": project.client_name, "address": project.site_address, "project": project.project_name},
        "intro": blocks_by_heading.get("Intro", []),
        "how_to_read": blocks_by_heading.get("How to read this proposal", []),
        "sections": sections,
        "totals": totals,
        "alternates": alt_descriptions,
        "totals_note": blocks_by_heading.get("Totals", []),
        "signature": blocks_by_heading.get("Signature", []),
        "groups": groups,
        "changes": _changes(diff) if rev.print_changes else None,
        "sov": _sov(rev, res, catalog) if rev.print_sov else None,
    }


# ---------------------------------------------------------------- compile


def _assets():
    return resources.files("proposal_builder") / "render"


def compile_document(doc: dict, logo: Path | None, fmt: str = "pdf", ppi: int = 110,
                     template: str = "proposal.typ"):
    """Return PDF bytes, or a list of PNG bytes (one per page) for fmt='png'."""
    import typst

    assets = _assets()
    with tempfile.TemporaryDirectory(prefix="proposal-") as tmp:
        tmpd = Path(tmp)
        for t in (assets / "templates").iterdir():
            if t.name.endswith(".typ"):
                (tmpd / t.name).write_text(t.read_text(encoding="utf-8"), encoding="utf-8")
        doc = dict(doc)
        if logo and logo.exists():
            shutil.copyfile(logo, tmpd / "logo.png")
        else:
            doc["company"] = {**doc["company"], "logo": ""}
        (tmpd / "data.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
        fonts = tmpd / "fonts"
        fonts.mkdir()
        for f in (assets / "fonts").iterdir():
            if f.name.endswith(".ttf"):
                (fonts / f.name).write_bytes(f.read_bytes())
        kwargs = dict(root=str(tmpd), font_paths=[str(fonts)])
        main = str(tmpd / template)
        if fmt == "png":
            pages = typst.compile(main, format="png", ppi=ppi, **kwargs)
            return pages if isinstance(pages, list) else [pages]
        return typst.compile(main, **kwargs)


def company_block(settings: Settings) -> dict:
    c = settings.company
    return {"name": c.dba, "legal": c.legal_name, "address": c.address, "phone": c.phone,
            "email": c.email, "logo": "logo.png" if c.logo_path else ""}


def pdf_filename(project: Project, rev: Revision) -> str:
    import re
    last = project.client_name.split()[-1] if project.client_name else ""
    parts = [project.number, last, project.project_name.replace(" ", ""), "Proposal", f"V{rev.rev}"]
    return re.sub(r"[^A-Za-z0-9_.]+", "", "_".join(p for p in parts if p)) + ".pdf"
