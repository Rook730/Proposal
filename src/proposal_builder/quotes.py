"""Subcontractor quotes: request-for-quote packages and side-by-side comparisons.

A request for quote lists the proposal lines assigned to one contractor (no prices, no client
name). Quotes received are logged per project (quotes.json); when several contractors quote the
same scope, a comparison document can be shared with the client. The winning price is entered on
the lines by hand.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from .calc import calculate, render, variable_map
from .crm import Contractor, ContractorBook, line_contractor, new_id
from .models import Settings
from .proposal import Line, Project, Revision


class _Model(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class Quote(_Model):
    id: str = Field(default_factory=new_id)
    scope: str = ""                      # e.g. "Electrical"; quotes with the same scope are compared
    contractor_id: str | None = None
    line_ids: list[str] = Field(default_factory=list)
    amount: Decimal | None = None
    received: date | None = None
    valid_until: date | None = None
    notes: str = ""                      # inclusions, exclusions, lead time


class QuoteLog(_Model):
    schema_version: int = 1
    quotes: list[Quote] = Field(default_factory=list)

    def scopes(self) -> list[str]:
        seen: dict[str, str] = {}
        for q in self.quotes:
            if q.scope.strip():
                seen.setdefault(q.scope.strip().casefold(), q.scope.strip())
        return sorted(seen.values(), key=str.casefold)

    def for_scope(self, scope: str) -> list[Quote]:
        return [q for q in self.quotes if q.scope.strip().casefold() == scope.strip().casefold()]


def contractor_lines(rev: Revision, book: ContractorBook, contractor_id: str) -> list[Line]:
    return [ln for ln in rev.lines if (c := line_contractor(book, ln)) and c.id == contractor_id
            and not ln.is_percent]


def _line_text(ln: Line, v: dict) -> str:
    from .render.markup import md_to_typst
    parts = []
    if ln.print_general and ln.general_description:
        parts.append(render(ln.general_description, v))
    if ln.notes:
        parts.append(render(ln.notes, v))
    return md_to_typst("\n\n".join(parts))


def rfq_document(project: Project, rev: Revision, contractor: Contractor, lines: list[Line],
                 settings: Settings, stock_classes) -> dict:
    from .render.document import company_block, fmt_qty
    from .render.markup import md_to_typst
    v = variable_map(project, rev, settings)
    res = calculate(rev, settings, stock_classes, project)
    c = settings.company
    note = render(settings.rfq_note, {**v, "company_email": c.email, "company_phone": c.phone})
    return {
        "company": company_block(settings),
        "to": {"company": contractor.company, "contact": contractor.contact, "phone": contractor.phone,
               "email": contractor.email},
        "project": {"number": project.number, "name": project.project_name, "address": project.site_address,
                    "date": date.today().strftime("%Y.%m.%d"), "from": settings.recommended_by},
        "note": md_to_typst(note),
        "lines": [{"id": ln.id, "title": ln.title, "body": _line_text(ln, v), "unit": ln.unit,
                   "qty": fmt_qty(res.lines[ln.id].qty),
                   "alt": f"Alternate {ln.alternate}" if ln.alternate else ""} for ln in lines],
    }


def comparison_document(project: Project, rev: Revision, scope: str, quotes: list[Quote],
                        book: ContractorBook, settings: Settings) -> dict:
    from .render.document import company_block
    from .render.markup import md_to_typst
    line_ids = sorted({lid for q in quotes for lid in q.line_ids},
                      key=lambda x: tuple(int(p) for p in x.split(".") if p.isdigit()))
    lines = [rev.line(lid) for lid in line_ids if rev.line(lid)]
    rows = []
    for q in sorted(quotes, key=lambda q: (q.amount is None, q.amount or 0)):
        con = book.get(q.contractor_id)
        rows.append({"company": con.company if con else "(no contractor)",
                     "amount": f"{q.amount:,.2f}" if q.amount is not None else "",
                     "received": q.received.strftime("%Y.%m.%d") if q.received else "",
                     "valid": q.valid_until.strftime("%Y.%m.%d") if q.valid_until else "",
                     "notes": md_to_typst(q.notes)})
    return {
        "company": company_block(settings),
        "client": {"name": project.client_name, "address": project.site_address, "project": project.project_name},
        "proposal": {"number": project.number, "date": rev.proposal_date.strftime("%Y.%m.%d"), "revision": rev.rev},
        "today": date.today().strftime("%Y.%m.%d"),
        "scope": scope,
        "lines": [{"id": ln.id, "title": ln.title} for ln in lines],
        "rows": rows,
        "note": md_to_typst(settings.comparison_note),
    }
