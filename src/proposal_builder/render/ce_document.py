"""Convenient Enterprises proposal and estimate: print data for ce_proposal.typ and ce_estimate.typ.

The proposal is the company's narrative modules (its terms library: Intro, Scope, Deliverables ... Acceptance),
edited per proposal, with the fee lines printed as a cost table where a block says {cost_table} and signature
blocks where it says {signatures}. The estimate repeats the cost section as an itemized document for the
client's PO.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from .. import ce
from ..calc import Results, calculate, render, variable_map
from ..models import Boilerplate, Catalog, Settings
from ..proposal import Line, Project, Revision
from .document import _line_body, brand_data, fmt_pct, fmt_qty
from .markup import md_to_typst

COST_TABLE, SIGNATURES = "{cost_table}", "{signatures}"
# Detailed depth tables (stage 2): block body -> kind
TABLES = {"{bom_table}": "bom", "{milestone_table}": "milestones", "{timeline_table}": "timeline",
          "{compliance_table}": "compliance", "{commercial_table}": "commercial"}
BILLING_LABEL = {ce.FIXED: "Fixed fee", ce.ESTIMATE: "Estimate, billed at actual"}


def _money(v: Decimal | None) -> str:
    return "" if v is None else f"${v:,.2f}"


def urs_reference(urs) -> str:
    """How the proposal names the requirements it answers: "(Tandem Jig URS, Ref 123, Rev B)"."""
    if urs is None:
        return ""
    if urs.mode == "client":
        c = urs.client
        parts = [c.title, c.reference and f"Ref {c.reference}", c.revision and f"Rev {c.revision}", c.date]
    else:
        parts = [urs.title and f"{urs.title} URS/RFQ", urs.reference and f"Ref {urs.reference}",
                 f"Rev {urs.revision}"]
    parts = [p for p in parts if p]
    return f"({', '.join(parts)})" if parts else ""


def ce_variables(project: Project, rev: Revision, settings: Settings, catalog: Catalog, res: Results,
                 urs=None) -> dict:
    v = variable_map(project, rev, settings)
    v["urs_reference"] = urs_reference(urs if urs is not None else rev.urs)
    pay = ce.payments(res.base, settings, catalog)
    v.update({"total_price": _money(res.base.total), "subtotal": _money(res.base.subtotal),
              "fixed_fee": _money(pay.fixed), "estimate_total": _money(pay.estimate),
              "deposit_amount": _money(pay.deposit), "deposit_pct": fmt_pct(pay.deposit_pct),
              "fixed_balance": _money(pay.fixed_balance)})
    return v


def _row(ln: Line, res: Results, v: dict, settings: Settings) -> dict:
    lr = res.lines[ln.id]
    no_charge = not lr.cost and not ln.not_included
    return {"id": ln.id, "title": ln.title, "body": _line_body(ln, v, settings),
            "qty": fmt_qty(lr.qty), "unit": ln.unit,
            "rate": _money(lr.unit_price) if lr.unit_price else "",
            "amount": "Not included" if ln.not_included else ("No charge" if no_charge else _money(lr.cost))}


def cost_data(project: Project, rev: Revision, settings: Settings, catalog: Catalog, res: Results,
              v: dict) -> dict:
    groups = []
    for sec in rev.sections:
        lines = [ln for ln in rev.section_lines(sec) if ln.alternate is None]
        if not lines:
            continue
        kind = ce.billing(sec, catalog)
        groups.append({"name": rev.section_title(sec, catalog), "billing": kind,
                       "label": BILLING_LABEL[kind], "rows": [_row(ln, res, v, settings) for ln in lines],
                       "subtotal": _money(res.base.section_total(sec, with_pct=False))})
    pay = ce.payments(res.base, settings, catalog)
    totals = []
    if pay.fixed and pay.estimate:
        totals += [{"label": "Fixed fee", "amount": _money(pay.fixed), "style": ""},
                   {"label": "Time and materials (estimate)", "amount": _money(pay.estimate), "style": ""}]
    totals.append({"label": "Total", "amount": _money(res.base.total), "style": "total"})
    if pay.deposit:
        totals.append({"label": f"Deposit due at approval ({fmt_pct(pay.deposit_pct)} of the fixed fee)",
                       "amount": _money(pay.deposit), "style": "note"})
    opts = [{"n": o.number, "name": o.name,
             "text": md_to_typst(render(o.description, v)) if o.description else "",
             "rows": [_row(ln, res, v, settings) for ln in o.lines],
             "amount": ("+" if o.amount >= 0 else "-") + _money(abs(o.amount)), "total_with": _money(o.total_with)}
            for o in ce.options(rev, res)]
    return {"groups": groups, "totals": totals, "options": opts}


def bom_data(rev: Revision) -> list[dict]:
    from ..ce_models import BUYERS, CONSULTANT
    return [{"item": " ".join(x for x in (b.manufacturer, b.model) if x) or b.description,
             "description": b.description if (b.manufacturer or b.model) else "",
             "pn": b.part_number, "qty": fmt_qty(b.qty), "unit": b.unit, "supplier": b.supplier,
             "lead": b.lead_time, "buyer": "Consultant" if b.buyer == CONSULTANT else BUYERS.get(b.buyer, b.buyer)}
            for b in rev.bom]


def milestone_data(rev: Revision, res: Results, settings: Settings, catalog: Catalog) -> dict:
    rows, left = ce.milestone_schedule(rev, res.base, settings, catalog)
    pay = ce.payments(res.base, settings, catalog)
    return {"rows": [{"name": r.name, "trigger": r.trigger, "pct": fmt_pct(r.pct), "amount": _money(r.amount)}
                     for r in rows],
            "fixed": _money(pay.fixed), "complete": left == 0}


def compliance_data(urs) -> list[dict]:
    """M17: every live requirement (not information sections) with its compliance status and response."""
    from .. import ce_urs as U
    if urs is None:
        return []
    out = []
    for it, num, live in U.compliance_rows(urs):
        if not live or it.kind == "information" or (not it.heading and not it.body):
            continue
        out.append({"number": num, "heading": it.heading, "level": it.level,
                    "status": U.STATUSES.get(it.status, "") if it.status else "TBD",
                    "deviate": it.status in U.FORM_STATUSES,
                    "response": it.response if it.status in U.FORM_STATUSES or it.status == "client" else ""})
    return out


def line_category(ln: Line) -> str:
    from ..ce_catalog import SECTION_CATEGORY
    return ln.category or SECTION_CATEGORY.get(ln.section, "engineering")


def commercial_data(rev: Revision, res: Results) -> dict:
    """M19: base-proposal totals by category (tooling separated from capital equipment) and the major purchased
    components (bill of materials items of $10,000 or more)."""
    from ..ce_models import CATEGORIES
    totals: dict[str, Decimal] = {}
    for ln in rev.lines:
        if ln.alternate is not None or ln.section not in rev.sections or ln.id not in res.lines:
            continue
        cat = line_category(ln)
        totals[cat] = totals.get(cat, Decimal(0)) + res.lines[ln.id].cost
    order = ["capital", "tooling", "engineering", "hardware", "support", "travel"]
    rows = [{"label": CATEGORIES.get(k, k.title()), "amount": _money(totals[k])}
            for k in order + sorted(set(totals) - set(order)) if totals.get(k)]
    major = [{"item": " ".join(x for x in (b.manufacturer, b.model) if x) or b.description,
              "description": b.description if (b.manufacturer or b.model) else "", "qty": fmt_qty(b.qty),
              "unit": b.unit}
             for b in rev.bom if (b.extended or Decimal(0)) >= Decimal(10000)]
    return {"rows": rows, "total": _money(res.base.total), "major": major}


def timeline_data(rev: Revision) -> dict:
    end = max((p.start_week + p.weeks for p in rev.phases), default=Decimal(0))
    return {"weeks": float(end), "label": fmt_qty(end),
            "rows": [{"name": p.name, "start": float(p.start_week), "weeks": float(p.weeks),
                      "span": f"Weeks {fmt_qty(p.start_week)} to {fmt_qty(p.start_week + p.weeks)}", "gate": p.gate}
                     for p in rev.phases]}


def _client(project: Project) -> dict:
    return {"name": project.client_name, "attention": project.attention, "address": project.site_address,
            "project": project.project_name, "po": project.po_number}


def _company(settings: Settings) -> dict:
    c = settings.company
    return {"name": c.dba, "legal": c.legal_name, "address": c.address, "phone": c.phone, "email": c.email,
            "logo": "logo.png" if c.logo_path else "", "accent": "", "brand": brand_data(settings)}


def build_ce_document(project: Project, rev: Revision, settings: Settings, catalog: Catalog,
                      boilerplate: Boilerplate, results: Results | None = None, urs=None) -> dict:
    """urs: the project's live requirements for a draft; an issued revision prints its own snapshot."""
    res = results or calculate(rev, settings, catalog.stock_classes, project)
    if rev.urs is not None and (urs is None or rev.state.value != "Draft"):
        urs = rev.urs
    v = ce_variables(project, rev, settings, catalog, res, urs)
    by_heading: dict[str, list] = {}
    for b in sorted(rev.blocks, key=lambda b: b.order):
        if not b.on:
            continue
        if b.body.strip() == COST_TABLE:
            item = {"title": b.title, "kind": "cost"}
        elif b.body.strip() == SIGNATURES:
            item = {"title": b.title, "kind": "signatures"}
        elif b.body.strip() in TABLES:
            item = {"title": b.title, "kind": TABLES[b.body.strip()]}
        else:
            item = {"title": b.title, "kind": "text", "body": md_to_typst(render(b.body, v))}
        by_heading.setdefault(b.heading, []).append(item)
    order = list(boilerplate.headings) + [h for h in by_heading if h not in boilerplate.headings]
    modules = [{"heading": h, "blocks": by_heading[h]} for h in order if h != "Intro" and by_heading.get(h)]
    return {
        "template": "ce_proposal.typ",
        "company": _company(settings),
        "proposal": {"number": project.number, "date": rev.proposal_date.strftime("%m/%d/%Y"), "revision": rev.rev},
        "client": _client(project),
        "intro": by_heading.get("Intro", []),
        "modules": modules,
        "cost": cost_data(project, rev, settings, catalog, res, v),
        "bom": bom_data(rev),
        "milestones": milestone_data(rev, res, settings, catalog),
        "timeline": timeline_data(rev),
        "compliance": compliance_data(urs),
        "commercial": commercial_data(rev, res),
        "signatures": {"client": project.client_name or "Client",
                       "company": settings.company.dba or settings.company.legal_name},
    }


def build_estimate_document(project: Project, rev: Revision, settings: Settings, catalog: Catalog,
                            results: Results | None = None) -> dict:
    res = results or calculate(rev, settings, catalog.stock_classes, project)
    v = ce_variables(project, rev, settings, catalog, res)
    valid = rev.proposal_date + timedelta(days=settings.validity_days)
    return {
        "template": "ce_estimate.typ",
        "company": _company(settings),
        "estimate": {"number": project.number, "revision": rev.rev, "date": rev.proposal_date.strftime("%B %d, %Y"),
                     "valid": valid.strftime("%B %d, %Y"), "title": project.project_name,
                     "total": _money(res.base.total),
                     "deposit": _money(ce.payments(res.base, settings, catalog).deposit)},
        "client": _client(project),
        "cost": cost_data(project, rev, settings, catalog, res, v),
        "note": render(settings.estimate_note, v) if settings.estimate_note else "",
    }


def estimate_filename(project: Project, rev: Revision) -> str:
    from .document import pdf_filename
    return pdf_filename(project, rev).replace("_Proposal_", "_Estimate_")
