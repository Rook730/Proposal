"""Convenient Enterprises billing: fixed fee vs time and materials, deposit and options (ce-requirements 6).

A CE proposal's fee items are ordinary proposal lines. Their catalog section says how they are billed
(Section.billing): "fixed" lines make up the fixed fee (deposit on it, the rest by milestone); "estimate" lines
are time and materials, printed as an estimate and billed at actual. Options are add-only alternates: they print
with their own price and never count in the base total.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from .calc import Results, Scenario
from .models import Catalog, Settings
from .proposal import Line, Revision

ZERO = Decimal(0)
FIXED, ESTIMATE = "fixed", "estimate"


def money(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def billing(section: int, catalog: Catalog) -> str:
    """"fixed" or "estimate". Sections without a billing type (custom sections) count as fixed fee."""
    sec = catalog.section(section)
    return sec.billing if sec is not None and sec.billing in (FIXED, ESTIMATE) else FIXED


@dataclass
class FeeSplit:
    fixed: Decimal
    estimate: Decimal

    @property
    def total(self) -> Decimal:
        return self.fixed + self.estimate


def split(scenario: Scenario, catalog: Catalog) -> FeeSplit:
    fixed = est = ZERO
    for sec, amt in scenario.section_base.items():
        if billing(sec, catalog) == ESTIMATE:
            est += amt
        else:
            fixed += amt
    return FeeSplit(fixed, est)


@dataclass
class Payments:
    deposit_pct: Decimal
    deposit: Decimal               # due at approval: deposit_pct of the fixed fee
    fixed: Decimal
    fixed_balance: Decimal         # rest of the fixed fee, invoiced by milestone
    estimate: Decimal              # time and materials estimate, invoiced weekly at actual
    total: Decimal


def payments(scenario: Scenario, settings: Settings, catalog: Catalog) -> Payments:
    sp = split(scenario, catalog)
    dep = money(sp.fixed * settings.deposit_pct)
    return Payments(settings.deposit_pct, dep, sp.fixed, sp.fixed - dep, sp.estimate, sp.total)


@dataclass
class Option:
    number: int
    name: str
    description: str
    lines: list[Line] = field(default_factory=list)
    amount: Decimal = ZERO              # what the option adds (or removes) on the base total
    total_with: Decimal = ZERO


def options(rev: Revision, res: Results) -> list[Option]:
    out = []
    for a in sorted(rev.alternates, key=lambda a: a.number):
        if a.number not in res.alternates:
            continue
        lines = [ln for ln in rev.lines if ln.alternate == a.number]
        out.append(Option(a.number, a.name or (lines[0].title if len(lines) == 1 else f"Option {a.number}"),
                          a.description, lines, res.delta(a.number), res.alternates[a.number].total))
    return out


# ---------------------------------------------------------------- Detailed depth (stage 2)

def bom_consultant_cost(rev: Revision) -> Decimal:
    """Invoiced cost of the bill of materials items the Consultant buys (unpriced items count as 0)."""
    from .ce_models import CONSULTANT
    return sum((b.extended or ZERO for b in rev.bom if b.buyer == CONSULTANT), ZERO)


def sync_hardware_line(rev: Revision, catalog: Catalog, settings: Settings, new_id) -> Line | None:
    """Keep the one hardware pass-through line in step with the bill of materials: invoiced cost of the
    Consultant-bought items plus the sourcing fee. Added when the first such item appears, removed when none
    are left. new_id(section, code) gives a line ID. Returns the line (or None)."""
    from .ce_catalog import HARDWARE_CODE, HARDWARE_SECTION
    from .ce_models import CONSULTANT
    from .proposal import line_from_item
    items = [b for b in rev.bom if b.buyer == CONSULTANT]
    line = next((ln for ln in rev.lines if ln.code == HARDWARE_CODE and ln.alternate is None), None)
    if not items:
        if line is not None:
            rev.lines.remove(line)
            if not rev.section_lines(line.section) and line.section in rev.sections:
                rev.sections.remove(line.section)
        return None
    cost = bom_consultant_cost(rev)
    price = money(cost * (1 + settings.sourcing_fee_pct))
    if line is None:
        it = catalog.item(HARDWARE_CODE)
        if it is None:
            return None
        line = line_from_item(it, catalog, new_id(HARDWARE_SECTION, HARDWARE_CODE))
        rev.add_line(line)
        if HARDWARE_SECTION not in rev.sections:
            rev.sections.append(HARDWARE_SECTION)
    line.qty, line.unit_price = Decimal(1), price
    n = len(items)
    line.notes = (f"{n} item{'s' if n != 1 else ''} in the bill of materials: invoiced cost ${cost:,.2f} plus "
                  f"{settings.sourcing_fee_pct * 100:.0f}% sourcing fee. Billed at actual invoiced cost.")
    return line


@dataclass
class MilestoneRow:
    name: str
    trigger: str
    pct: Decimal
    amount: Decimal


def milestone_schedule(rev: Revision, scenario: Scenario, settings: Settings,
                       catalog: Catalog) -> tuple[list[MilestoneRow], Decimal]:
    """Deposit (Settings) then the revision's milestones, as amounts of the fixed fee. Returns the rows and the
    percent left unassigned (0 when the schedule adds up to 100%). The last row takes any rounding cent."""
    pay = payments(scenario, settings, catalog)
    rows = [MilestoneRow("Deposit", "Proposal approval", pay.deposit_pct, pay.deposit)]
    for m in rev.milestones:
        rows.append(MilestoneRow(m.name, m.trigger, m.pct, money(pay.fixed * m.pct)))
    left = Decimal(1) - sum((r.pct for r in rows), ZERO)
    if left == 0 and len(rows) > 1:
        rows[-1].amount += pay.fixed - sum((r.amount for r in rows), ZERO)
    return rows, left


def trip_lines(rev: Revision, catalog: Catalog, dest, trips: int, nights: int, new_id) -> list[Line]:
    """Travel lines for trips to a destination: one-way travel time per trip (half rate), lodging nights and
    mileage beyond the free zone (round trip, per trip). Added to the revision; returns them."""
    from .proposal import line_from_item
    out = []
    where = f"{dest.name}, {trips} trip{'s' if trips != 1 else ''}"
    for code, qty, note in ((4210, dest.one_way_hours * trips, f"To {where} (one way per trip)."),
                            (4220, Decimal(nights), f"{where}." if nights else ""),
                            (4230, dest.round_trip_miles * trips, f"Round trip beyond the free zone, {where}.")):
        if not qty:
            continue
        it = catalog.item(code)
        if it is None:
            continue
        ln = line_from_item(it, catalog, new_id(it.section, code))
        ln.qty, ln.notes = Decimal(qty), note
        rev.add_line(ln)
        if it.section not in rev.sections:
            rev.sections.append(it.section)
        out.append(ln)
    return out


def set_depth(rev: Revision, depth: str, library, settings: Settings) -> None:
    """Letter: the Detailed and URS-response blocks are off. Detailed: the Detailed blocks are on (added from the
    library if this revision predates them), and empty milestones and schedule start from the Settings templates.
    URS response: Detailed plus the requirements, system description and commercial blocks."""
    from .ce_catalog import DETAILED_IDS, URS_IDS
    from .ce_models import DETAILED, URS
    from .proposal import default_blocks
    detailed, urs = depth in (DETAILED, URS), depth == URS
    have = {b.id for b in rev.blocks}
    wanted = (DETAILED_IDS if detailed else ()) + (URS_IDS if urs else ())
    missing = [b for b in library.blocks if b.id in wanted and b.id not in have]
    if missing:
        added = default_blocks(missing)
        for b in added:
            b.on = True
        rev.blocks += added
    if detailed:
        if not rev.milestones:
            rev.milestones = [m.model_copy() for m in settings.milestone_template]
        if not rev.phases:
            rev.phases = [p.model_copy() for p in settings.phase_template]
    for b in rev.blocks:
        if b.id in DETAILED_IDS:
            b.on = detailed
        elif b.id in URS_IDS:
            b.on = urs
    rev.depth = depth


# ---------------------------------------------------------------- Issues tab checks (stage 2)

BIG_ITEM = Decimal(1000)
CERT_WORDS = re.compile(r"\b(certif\w*|stamp(?:ed|s)?|guarantee\w*|warrant(?:y|ies|s|ed)?|PE)\b", re.IGNORECASE)
NO_PROCUREMENT = re.compile(r"no hardware is (?:procured|purchased)|all hardware is purchased .{0,40}by the client",
                            re.IGNORECASE)


def _word_counts(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for w in CERT_WORDS.findall(text or ""):
        out[w.lower()] = out.get(w.lower(), 0) + 1
    return out


def new_cert_words(text: str, library_text: str = "") -> list[str]:
    """Certification wording in text beyond what the library's own wording already has (the library's
    disclaimers, such as 'does not constitute PE-stamped calculations', are not flagged)."""
    have, base = _word_counts(text), _word_counts(library_text)
    return sorted(w for w, n in have.items() if n > base.get(w, 0))


def checks(rev: Revision, scenario: Scenario, settings: Settings, catalog: Catalog, library) -> list[tuple]:
    """Convenient Enterprises checks for the Issues tab: (kind, message, target) like the editor's own."""
    from .ce_models import CONSULTANT, DETAILED
    out: list[tuple] = []
    plan = ("tab", "plan")
    if rev.depth == DETAILED and rev.milestones:
        _, left = milestone_schedule(rev, scenario, settings, catalog)
        if left:
            out.append(("warn", f"Payment schedule adds up to {(1 - left) * 100:.0f}% of the fixed fee, not 100% "
                                "(deposit plus milestones, Project plan)", plan))
    for b in rev.bom:
        label = b.description or b.part_number or "BOM item"
        if b.buyer == CONSULTANT and not b.unit_cost:
            out.append(("warn", f"BOM '{label}': bought by the Consultant but has no cost, so it bills as $0",
                        plan))
        if (b.extended or ZERO) >= BIG_ITEM and not (b.manufacturer and b.model):
            out.append(("info", f"BOM '{label}': ${b.extended:,.2f} with no make and model; the client "
                                "cannot check the price", plan))
    lib = {x.id: x.body for x in library.blocks} if library is not None else {}
    for blk in rev.blocks:
        if not blk.on:
            continue
        words = new_cert_words(blk.body, blk.source_body if blk.source_body is not None else lib.get(blk.id, ""))
        if words:
            out.append(("warn", f"'{blk.title or blk.heading or blk.id}' says {', '.join(words)}; certification "
                                "and guarantee wording belongs only in the Standard of care and Exclusions text",
                        ("block", blk.id)))
    for ln in rev.lines:
        words = new_cert_words(ln.notes)
        if words and ln.section in rev.sections:
            out.append(("warn", f"{ln.id} {ln.title}: notes say {', '.join(words)}; certification and guarantee "
                                "wording belongs only in the Standard of care and Exclusions text", ("line", ln.id)))
    if any(b.buyer == CONSULTANT for b in rev.bom):
        for blk in rev.blocks:
            if blk.on and NO_PROCUREMENT.search(blk.body or ""):
                out.append(("warn", f"'{blk.title or blk.heading or blk.id}' says the Client buys all hardware, "
                                    "but the bill of materials has items the Consultant buys", ("block", blk.id)))
    return out
