"""Convenient Enterprises billing: fixed fee vs time and materials, deposit and options (ce-requirements 6).

A CE proposal's fee items are ordinary proposal lines. Their catalog section says how they are billed
(Section.billing): "fixed" lines make up the fixed fee (deposit on it, the rest by milestone); "estimate" lines
are time and materials, printed as an estimate and billed at actual. Options are add-only alternates: they print
with their own price and never count in the base total.
"""

from __future__ import annotations

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
