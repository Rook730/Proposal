"""Print data for change orders and the final project ledger."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from ..closeout import ChangeOrder, COFunding, Contract, COPricing, Ledger, Reconciliation
from ..models import Settings
from ..proposal import Project
from .document import company_block, fmt_pct
from .markup import md_to_typst


def m(v: Decimal | None) -> str:
    """Money for the accounting cell: '1,234.56', '(1,234.56)' for negatives, '-' for zero."""
    if v is None:
        return ""
    if v == 0:
        return "-"
    s = f"{abs(v):,.2f}"
    return f"({s})" if v < 0 else s


def _header(project: Project, contract: Contract) -> dict:
    return {
        "client": {"name": project.client_name, "address": project.site_address, "project": project.project_name},
        "proposal": {"number": project.number, "date": contract.rev.proposal_date.strftime("%Y.%m.%d"),
                     "revision": contract.rev.rev},
    }


def change_order_document(project: Project, contract: Contract, co: ChangeOrder, pricing: COPricing,
                          settings: Settings) -> dict:
    rows = [("Cost change", m(pricing.cost_delta), ""),
            (f"Overhead and profit ({fmt_pct(contract.markup_pct)})", m(pricing.markup), ""),
            ("Change order price", m(pricing.price), "bold")]
    if co.funding is COFunding.CONTINGENCY:
        rows.append(("Covered by contingency", m(-pricing.from_contingency), ""))
        rows.append(("Contingency remaining after this change order", m(pricing.contingency_after), ""))
    if co.funding is COFunding.ABSORBED:
        rows.append(("Absorbed by Kept Spec", m(-pricing.price), ""))
    if pricing.mgmt_hours:
        hrs = f"{pricing.mgmt_hours.normalize():f}"
        rows.append((f"Change management: {hrs} HR at ${contract.mgmt_rate:,.2f}", m(pricing.mgmt_cost), ""))
        rows.append(("Drawn from change order management allowance", m(-pricing.mgmt_from_allowance), ""))
        if co.funding is COFunding.ABSORBED and pricing.mgmt_cost > pricing.mgmt_from_allowance:
            rows.append(("Management beyond the allowance, absorbed by Kept Spec",
                         m(-(pricing.mgmt_cost - pricing.mgmt_from_allowance)), ""))
        rows.append(("Management allowance remaining after this change order", m(pricing.mgmt_allowance_after), ""))
    rows.append(("Change to contract price", m(pricing.billed), "total"))
    sections = [{"title": t, "body": md_to_typst(b)} for t, b in
                (("SOW Modifications", co.sow), ("Payment Impacts", co.payment_impacts),
                 ("Schedule Impacts", co.schedule_impacts)) if b.strip()]
    return {
        "company": company_block(settings),
        **_header(project, contract),
        "co": {
            "number": co.number, "title": co.title, "requested": co.requested.strftime("%Y.%m.%d"),
            "approved": co.approved.strftime("%Y.%m.%d") if co.approved else "",
            "items": [{"description": md_to_typst(i.description), "action": i.action.value,
                       "change": md_to_typst(i.change), "lines": ", ".join(i.line_ids),
                       "original": m(i.original_cost), "final": m(i.final_cost)} for i in co.items],
            "pricing": [{"label": a, "amount": b, "style": c} for a, b, c in rows],
            "sections": sections,
            "recommended_by": co.recommended_by or settings.recommended_by,
            "approved_by": co.approved_by,
        },
    }


def ledger_document(project: Project, ledger: Ledger, recon: Reconciliation, settings: Settings,
                    on: date | None = None) -> dict:
    c = ledger.contract
    rev = c.rev
    contract_rows = [
        (f"Original contract value (Rev {rev.rev})", m(c.total), "bold"),
        ("Contingency carried in contract", m(c.contingency), ""),
        ("Change order management allowance carried in contract", m(c.co_management), ""),
    ]
    if rev.selected_alternates:
        contract_rows.insert(1, ("Includes " + ", ".join(f"Alternate {n}" for n in rev.selected_alternates),
                                 "", ""))
    cos = [{"number": o.number, "title": o.title or (o.items[0].change if o.items else ""),
            "approved": o.approved.strftime("%Y.%m.%d") if o.approved else "",
            "funding": o.funding.value, "price": m(ledger.pricing[o.number].price),
            "contingency": m(ledger.pricing[o.number].from_contingency),
            "billed": m(ledger.pricing[o.number].billed)} for o in ledger.approved]
    hours = sum((o.mgmt_hours for o in ledger.approved), Decimal(0))
    co_summary = [("Change orders billed to the client", m(ledger.co_billed), "bold"),
                  ("Contingency used by change orders", m(ledger.contingency_used), ""),
                  ("Unused contingency (credited)", m(ledger.unused_contingency), ""),
                  (f"Change order management used ({hours.normalize():f} HR)", m(ledger.mgmt_used), ""),
                  ("Unused change order management (credited)", m(ledger.co_management_credit), "")]
    lines = []
    for lr in ledger.lines_with_activity:
        note = []
        if lr.unused:
            note.append("not used, credited")
        if lr.client_paid:
            note.append(f"client paid ${lr.client_paid:,.2f} directly")
        lines.append({"id": lr.line.id, "title": lr.line.title, "budget": m(lr.budget),
                      "actual": m(lr.actual if lr.actual is not None else Decimal(0)),
                      "variance": m(lr.variance), "note": "; ".join(note)})
    variance_rows = [("Net line variance", m(ledger.net_variance), "bold"),
                     (f"Overhead and profit on net variance ({fmt_pct(c.markup_pct)})", m(ledger.variance_markup), "")]
    final = [
        ("Original contract value", m(c.total), ""),
        ("Plus: change orders billed", m(ledger.co_billed), ""),
        ("Plus: net line variance", m(ledger.net_variance), ""),
        ("Plus: overhead and profit on variance", m(ledger.variance_markup), ""),
        ("Less: unused contingency", m(-ledger.unused_contingency), ""),
    ]
    final.append(("Less: unused change order management", m(-ledger.co_management_credit), ""))
    final += [
        ("Total final project cost", m(ledger.total_final), "bold"),
        ("Less: paid by the client directly to subcontractors and suppliers", m(-ledger.client_direct), ""),
        ("Less: payments received by Kept Spec Advisors", m(-ledger.payments_received), ""),
        ("Balance due upon final completion" if ledger.balance_due >= 0 else "Credit due to client",
         m(abs(ledger.balance_due)), "total"),
    ]
    rows = lambda rs: [{"label": a, "amount": b, "style": s} for a, b, s in rs]  # noqa: E731
    return {
        "company": company_block(settings),
        **_header(project, c),
        "date": (on or date.today()).strftime("%Y.%m.%d"),
        "contract": rows(contract_rows),
        "cos": cos,
        "co_summary": rows(co_summary),
        "lines": lines,
        "variance_summary": rows(variance_rows),
        "payments": [{"draw": p.draw, "milestone": p.milestone, "date": p.date.strftime("%Y.%m.%d") if p.date else "",
                      "amount": m(p.amount)} for p in recon.payments],
        "final": rows(final),
        "note": recon.note,
    }


def safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "", s)
