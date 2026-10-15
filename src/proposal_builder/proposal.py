"""Project, revision and line models.

Snapshot rule (spec 4.9): a line copies everything it needs from the catalog
when it is created. Later catalog, rate or allowance edits never change a
saved line; "pull update" re-copies on request.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from .models import (
    BoilerplateBlock,
    Catalog,
    CatalogItem,
    Performer,
    PriceSource,
    Tier,
    Variable,
)

SCHEMA_VERSION = 1


class _Model(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class ProjectStatus(str, Enum):
    DRAFT = "Draft"
    PRESENTED = "Presented"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"
    IN_PROCESS = "In-Process"
    COMPLETED = "Completed"


class RevisionState(str, Enum):
    DRAFT = "Draft"
    ISSUED = "Issued"
    ACCEPTED = "Accepted"
    SUPERSEDED = "Superseded"


class LineTier(str, Enum):
    LOW = "low"
    MID = "mid"
    HIGH = "high"
    CUSTOM = "custom"


class Line(_Model):
    id: str                                   # "11.04": section index . sequence
    section: int                              # Section.number
    order: int = 0                            # print order inside the section
    code: int | None = None                   # catalog code (None = custom line)
    title: str
    general_description: str = ""             # catalog snapshot, read-only on the line
    print_general: bool = True
    notes: str = ""                           # detail notes, Markdown with {variables}
    unit: str = "LS"

    # quantity: qty_var > takeoff (stock rounding) > qty
    qty: Decimal = Decimal(1)
    qty_var: str | None = None
    takeoff: Decimal | None = None            # LF before waste
    waste_pct: Decimal | None = None          # None = settings default
    stock_class: str | None = None

    # price: price_var > unit_price. unit_price is the snapshot actually used.
    price_basis: PriceSource = PriceSource.FIXED
    unit_price: Decimal | None = None         # PERCENT: fraction of subtotal
    price_var: str | None = None
    rate_key: str | None = None
    allowance_id: str | None = None
    allowance_low: Decimal | None = None
    allowance_high: Decimal | None = None
    tier: LineTier = LineTier.HIGH

    performer: Performer = Performer.NONE
    sub_name: str = ""                        # internal only
    is_allowance: bool = False
    not_included: bool = False
    owner_furnished: bool = False
    credit_if_unused: bool = False
    alternate: int | None = None              # 1..3: line exists only in that alternate

    internal_notes: str = ""
    vendor: str = ""
    quote_ref: str = ""
    quote_amount: Decimal | None = None

    @property
    def is_percent(self) -> bool:
        return self.price_basis is PriceSource.PERCENT

    def tier_price(self) -> Decimal | None:
        lo, hi = self.allowance_low, self.allowance_high
        if lo is None or hi is None:
            return None
        return {LineTier.LOW: lo, LineTier.HIGH: hi,
                LineTier.MID: ((lo + hi) / 2).quantize(Decimal("0.01"))}.get(self.tier)


class Alternate(_Model):
    number: int                               # 1..3
    name: str = ""
    description: str = ""
    removes: list[str] = Field(default_factory=list)   # base line IDs removed

    def kind(self, has_adds: bool) -> str:
        if self.removes and has_adds:
            return "swap"
        return "deduct" if self.removes else "add"


class ProposalBlock(_Model):
    """Boilerplate block copied into a revision. Edits here never touch the library."""
    id: str
    heading: str
    title: str
    body: str
    on: bool = True
    order: int = 0


class Revision(_Model):
    schema_version: int = SCHEMA_VERSION
    rev: str = "1.0"
    proposal_date: date = Field(default_factory=date.today)
    state: RevisionState = RevisionState.DRAFT
    sections: list[int] = Field(default_factory=list)          # included, in print order
    lines: list[Line] = Field(default_factory=list)
    alternates: list[Alternate] = Field(default_factory=list)
    variables: list[Variable] = Field(default_factory=list)
    blocks: list[ProposalBlock] = Field(default_factory=list)
    next_seq: dict[int, int] = Field(default_factory=dict)     # section -> next line sequence

    # -- lines
    def line(self, line_id: str) -> Line | None:
        return next((ln for ln in self.lines if ln.id == line_id), None)

    def section_lines(self, section: int) -> list[Line]:
        return sorted((ln for ln in self.lines if ln.section == section), key=lambda ln: (ln.order, ln.id))

    def new_line_id(self, section: int) -> str:
        seq = self.next_seq.get(section, 1)
        used = {ln.id for ln in self.lines}
        while f"{section // 100}.{seq:02d}" in used:
            seq += 1
        self.next_seq[section] = seq + 1
        return f"{section // 100}.{seq:02d}"

    def add_line(self, line: Line) -> Line:
        if line.section not in self.sections:
            self.sections.append(line.section)
            self.sections.sort()
        existing = self.section_lines(line.section)
        line.order = (existing[-1].order + 10) if existing else 10
        self.lines.append(line)
        return line

    def remove_line(self, line_id: str) -> None:
        """IDs are retired, never reused (next_seq only moves forward)."""
        self.lines = [ln for ln in self.lines if ln.id != line_id]
        for alt in self.alternates:
            if line_id in alt.removes:
                alt.removes.remove(line_id)

    def move_line(self, line_id: str, direction: int) -> None:
        ln = self.line(line_id)
        if ln is None:
            return
        sib = self.section_lines(ln.section)
        i = sib.index(ln)
        j = i + direction
        if 0 <= j < len(sib):
            sib[i].order, sib[j].order = sib[j].order, sib[i].order
            if sib[i].order == sib[j].order:
                for n, s in enumerate(sib):
                    s.order = (n + 1) * 10
                sib[i].order, sib[j].order = sib[j].order, sib[i].order

    def alternate(self, number: int) -> Alternate | None:
        return next((a for a in self.alternates if a.number == number), None)


class Project(_Model):
    schema_version: int = SCHEMA_VERSION
    number: str                       # "26005"
    client_name: str = ""
    site_address: str = ""
    project_name: str = ""
    status: ProjectStatus = ProjectStatus.DRAFT
    created: date = Field(default_factory=date.today)
    notes: str = ""

    @property
    def folder_name(self) -> str:
        import re
        tail = re.sub(r"[^A-Za-z0-9]+", "_", f"{self.client_name.split()[-1] if self.client_name else ''}_{self.project_name}").strip("_")
        return f"{self.number}_{tail}" if tail else self.number


# ---------------------------------------------------------------- catalog -> line


def line_from_item(item: CatalogItem, catalog: Catalog, line_id: str,
                   tier: Tier | None = None) -> Line:
    """Snapshot a catalog item into a new proposal line."""
    ln = Line(
        id=line_id, section=item.section, code=item.code, title=item.title,
        general_description=item.description, unit=item.unit,
        price_basis=item.price_source, rate_key=item.rate_key,
        performer=item.performer, stock_class=item.stock_class,
        not_included=item.not_included, owner_furnished=item.owner_furnished,
        credit_if_unused=item.credit_if_unused,
        is_allowance=item.price_source is PriceSource.ALLOWANCE or bool(item.allowance_ids),
        tier=LineTier((tier or item.default_tier).value),
    )
    apply_catalog_price(ln, item, catalog)
    if item.not_included:
        ln.qty = Decimal(1)
    return ln


def apply_catalog_price(ln: Line, item: CatalogItem, catalog: Catalog) -> None:
    """Copy the current price inputs for the line's basis from the catalog."""
    if ln.price_basis is PriceSource.RATE:
        r = catalog.rate(ln.rate_key or item.rate_key or "")
        ln.unit_price = r.rate if r else None
    elif ln.price_basis is PriceSource.ALLOWANCE:
        aid = ln.allowance_id or (item.allowance_ids[0] if item.allowance_ids else None)
        a = catalog.allowance(aid) if aid else None
        if a:
            ln.allowance_id, ln.allowance_low, ln.allowance_high = a.id, a.low, a.high
            ln.unit = a.unit
            ln.unit_price = ln.tier_price() if ln.tier is not LineTier.CUSTOM else ln.unit_price
        else:
            ln.unit_price = item.price
    else:
        ln.unit_price = item.price


def catalog_differences(ln: Line, catalog: Catalog) -> dict[str, tuple]:
    """Fields where the line's snapshot differs from the current catalog: {field: (line, catalog)}."""
    if ln.code is None:
        return {}
    item = catalog.item(ln.code)
    if item is None:
        return {"code": (ln.code, None)}
    diffs: dict[str, tuple] = {}
    if ln.general_description != item.description:
        diffs["general_description"] = (ln.general_description, item.description)
    if ln.price_basis is PriceSource.RATE:
        r = catalog.rate(ln.rate_key or "")
        if r and r.rate != ln.unit_price:
            diffs["rate"] = (ln.unit_price, r.rate)
    elif ln.allowance_id:
        a = catalog.allowance(ln.allowance_id)
        if a and (a.low, a.high) != (ln.allowance_low, ln.allowance_high):
            diffs["allowance range"] = ((ln.allowance_low, ln.allowance_high), (a.low, a.high))
    return diffs


def pull_update(ln: Line, catalog: Catalog) -> list[str]:
    """Re-copy description and price inputs from the catalog. Returns changed field names."""
    diffs = catalog_differences(ln, catalog)
    item = catalog.item(ln.code) if ln.code is not None else None
    if item is None:
        return []
    if "general_description" in diffs:
        ln.general_description = item.description
    if ln.price_basis is PriceSource.RATE and "rate" in diffs:
        apply_catalog_price(ln, item, catalog)
    if "allowance range" in diffs:
        a = catalog.allowance(ln.allowance_id or "")
        if a:
            ln.allowance_low, ln.allowance_high = a.low, a.high
            if ln.price_basis is PriceSource.ALLOWANCE and ln.tier is not LineTier.CUSTOM:
                ln.unit_price = ln.tier_price()
    return list(diffs)


def default_blocks(blocks: list[BoilerplateBlock]) -> list[ProposalBlock]:
    return [ProposalBlock(id=b.id, heading=b.heading, title=b.title, body=b.body,
                          on=b.default_on, order=b.order) for b in blocks]
