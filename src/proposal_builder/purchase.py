"""Purchase list: what to buy for a Convenient Woodworking project, from the build sheets of the base lines.

Quantities are added up across the whole project first and then rounded up once, so two lines that each need
half a sheet buy one sheet:

- lumber: board feet (yield already in the build sheet), by species and nominal thickness, rounded up to whole BF
- sheet goods, dimensional, hardware: whole units
- veneer: whole square feet
- finish: square feet x coats, and containers when the price reference has a coverage
- outsourced and other: as entered

Base lines only: alternate lines are left out (after acceptance, Rev 2.0 already holds the chosen alternates),
and so are lines that are not included or furnished by the owner. The estimated cost uses the current price
reference when the row is linked to one, otherwise the cost on the build sheet.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from .buildsheet import MATERIAL_KINDS, BuildMaterial
from .calc import Results
from .models import PriceReferences
from .proposal import Revision

ZERO = Decimal(0)
CENT = Decimal("0.01")
ROUND_UP = {"lumber", "sheet", "dimensional", "hardware", "veneer"}
KIND_ORDER = list(MATERIAL_KINDS)


@dataclass
class PurchaseRow:
    kind: str
    name: str                      # "Cherry 8/4", "Baltic birch 3/4\" 60 x 60"
    unit: str
    needed: Decimal = ZERO         # exact total across the project
    unit_cost: Decimal = ZERO
    supplier: str = ""
    part_number: str = ""
    price_date: date | None = None
    lines: list[str] = field(default_factory=list)
    containers: int | None = None  # finish: containers to buy
    container: str = ""            # finish: container size
    container_price: Decimal | None = None
    coverage: Decimal | None = None  # finish: SF per container, one coat

    @property
    def buy(self) -> Decimal:
        if self.kind in ROUND_UP:
            return Decimal(math.ceil(self.needed))
        return self.needed.quantize(CENT, rounding=ROUND_HALF_UP)

    @property
    def est_cost(self) -> Decimal:
        if self.containers is not None and self.container_price is not None:
            return (self.container_price * self.containers).quantize(CENT, rounding=ROUND_HALF_UP)
        return (self.buy * self.unit_cost).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass
class PurchaseList:
    rows: list[PurchaseRow]
    skipped: list[str]             # base lines with no build sheet

    def groups(self) -> list[tuple[str, list[PurchaseRow]]]:
        out = []
        for kind in KIND_ORDER:
            rows = sorted((r for r in self.rows if r.kind == kind), key=lambda r: r.name.casefold())
            if rows:
                out.append((kind, rows))
        return out

    def total(self, kind: str | None = None) -> Decimal:
        return sum((r.est_cost for r in self.rows if kind is None or r.kind == kind), ZERO)


def _key_and_row(m: BuildMaterial, prices: PriceReferences) -> tuple[tuple, PurchaseRow]:
    if m.kind == "lumber":
        species = m.ref or m.name
        nominal = m.nominal or m.priced_as
        ref = prices.lumber_price(species, nominal) if nominal else None
        row = PurchaseRow("lumber", f"{species} {nominal}".strip(), "BF",
                          unit_cost=ref.price if ref else m.unit_cost,
                          supplier=ref.supplier if ref else "", price_date=ref.date if ref else None)
        if ref and (ref.grade or ref.surfacing):
            row.name += f" ({', '.join(x for x in (ref.grade, ref.surfacing) if x)})"
        return ("lumber", species.casefold(), nominal), row
    ref = prices.find(m.kind, m.ref) if m.ref else None
    if ref is None:
        return (m.kind, m.name.casefold(), m.unit, m.unit_cost), PurchaseRow(m.kind, m.name, m.unit,
                                                                             unit_cost=m.unit_cost)
    key = (m.kind, "ref", ref.id)
    if m.kind == "sheet":
        name = f"{ref.product} {ref.thickness} {ref.width_in.normalize():f} x {ref.length_in.normalize():f}"
        return key, PurchaseRow("sheet", name, "SHT", unit_cost=ref.price, supplier=ref.supplier,
                                price_date=ref.date)
    if m.kind == "dimensional":
        name = f"{ref.material} {ref.size} x {ref.length_ft.normalize():f}'"
        return key, PurchaseRow("dimensional", name, "EA", unit_cost=ref.price, supplier=ref.supplier,
                                price_date=ref.date)
    if m.kind == "hardware":
        return key, PurchaseRow("hardware", ref.name, ref.unit, unit_cost=ref.price, supplier=ref.supplier,
                                part_number=ref.part_number, price_date=ref.date)
    if m.kind == "finish":
        return key, PurchaseRow("finish", ref.product, "SF", unit_cost=ref.per_sf_coat, supplier=ref.supplier,
                                price_date=ref.date, container=ref.container,
                                container_price=ref.container_price if ref.coverage_sf else None,
                                coverage=ref.coverage_sf or None)
    if m.kind == "veneer":
        name = f"{ref.species} {ref.thickness}".strip()
        return key, PurchaseRow("veneer", name, "SF", unit_cost=ref.price, supplier=ref.supplier,
                                price_date=ref.date)
    if m.kind == "outsourced":
        return key, PurchaseRow("outsourced", ref.service, ref.basis, unit_cost=ref.price, supplier=ref.supplier,
                                price_date=ref.date)
    return key, PurchaseRow(m.kind, m.name, m.unit, unit_cost=m.unit_cost)


def purchase_list(rev: Revision, res: Results, prices: PriceReferences) -> PurchaseList:
    rows: dict[tuple, PurchaseRow] = {}
    skipped: list[str] = []
    base = set(res.base.line_ids)
    for sec in rev.sections:
        for ln in rev.section_lines(sec):
            if ln.id not in base or ln.alternate is not None or ln.not_included or ln.owner_furnished \
                    or ln.is_percent:
                continue
            if ln.build is None or not ln.build.materials:
                if ln.build is None or ln.build.empty:
                    skipped.append(ln.id)
                continue
            qty = res.lines[ln.id].qty if ln.id in res.lines else ln.qty
            q = qty if qty and qty > 0 else Decimal(1)
            for m in ln.build.materials:
                n = m.quantity if m.setup else m.quantity * q
                if not n:
                    continue
                key, new = _key_and_row(m, prices)
                row = rows.setdefault(key, new)
                row.needed += n
                if ln.id not in row.lines:
                    row.lines.append(ln.id)
    for r in rows.values():
        if r.kind == "finish" and r.coverage:
            r.containers = math.ceil(r.needed / r.coverage)
    return PurchaseList(list(rows.values()), skipped)
