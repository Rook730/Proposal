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
BILLING_LABEL = {ce.FIXED: "Fixed fee", ce.ESTIMATE: "Estimate, billed at actual"}


def _money(v: Decimal | None) -> str:
    return "" if v is None else f"${v:,.2f}"


def ce_variables(project: Project, rev: Revision, settings: Settings, catalog: Catalog, res: Results) -> dict:
    v = variable_map(project, rev, settings)
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


def _client(project: Project) -> dict:
    return {"name": project.client_name, "attention": project.attention, "address": project.site_address,
            "project": project.project_name, "po": project.po_number}


def _company(settings: Settings) -> dict:
    c = settings.company
    return {"name": c.dba, "legal": c.legal_name, "address": c.address, "phone": c.phone, "email": c.email,
            "logo": "logo.png" if c.logo_path else "", "accent": "", "brand": brand_data(settings)}


def build_ce_document(project: Project, rev: Revision, settings: Settings, catalog: Catalog,
                      boilerplate: Boilerplate, results: Results | None = None) -> dict:
    res = results or calculate(rev, settings, catalog.stock_classes, project)
    v = ce_variables(project, rev, settings, catalog, res)
    by_heading: dict[str, list] = {}
    for b in sorted(rev.blocks, key=lambda b: b.order):
        if not b.on:
            continue
        if b.body.strip() == COST_TABLE:
            item = {"title": b.title, "kind": "cost"}
        elif b.body.strip() == SIGNATURES:
            item = {"title": b.title, "kind": "signatures"}
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
