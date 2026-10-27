"""Print data for the purchase list (internal: what to buy for a Convenient Woodworking project)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ..buildsheet import MATERIAL_KINDS
from ..models import Settings
from ..proposal import Project, Revision
from ..purchase import PurchaseList
from .document import company_block


def qty(v: Decimal) -> str:
    return f"{v.quantize(Decimal('0.01')).normalize():f}"


def money(v: Decimal) -> str:
    return f"{v:,.2f}"


def row_dict(r) -> dict:
    needed = f"{qty(r.needed)} {r.unit}"
    buy = f"{qty(r.buy)} {r.unit}"
    if r.containers is not None:
        buy = f"{r.containers} x {r.container or 'container'}"
    return {"name": r.name, "part": r.part_number, "supplier": r.supplier, "needed": needed, "buy": buy,
            "unit_cost": money(r.unit_cost) if r.containers is None else money(r.container_price or 0),
            "cost": money(r.est_cost), "lines": ", ".join(r.lines),
            "date": r.price_date.strftime("%Y.%m.%d") if r.price_date else ""}


def purchase_document(project: Project, rev: Revision, settings: Settings, pl: PurchaseList,
                      today: date | None = None) -> dict:
    groups = [{"title": MATERIAL_KINDS.get(k, k), "rows": [row_dict(r) for r in rows],
               "total": money(pl.total(k))} for k, rows in pl.groups()]
    return {
        "company": company_block(settings),
        "client": {"name": project.client_name, "address": project.site_address, "project": project.project_name},
        "proposal": {"number": project.number, "date": rev.proposal_date.strftime("%Y.%m.%d"),
                     "revision": rev.rev},
        "printed": (today or date.today()).strftime("%Y.%m.%d"),
        "groups": groups,
        "total": money(pl.total()),
        "skipped": ", ".join(pl.skipped),
    }


def purchase_filename(project: Project, rev: Revision) -> str:
    import re
    return re.sub(r"[^A-Za-z0-9_.]+", "", f"{project.number}_PurchaseList_V{rev.rev}") + ".pdf"
