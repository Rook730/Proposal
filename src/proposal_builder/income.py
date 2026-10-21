"""Kept Spec income per project (internal; never printed).

Income is what Convenient Enterprises keeps, before its own business expenses:
- lines performed by Kept Spec Advisors or Convenient Woodworking (whole line)
- overhead and profit percent lines (settings.co_markup_codes)
- change order management time, drawn from the 1320 allowance or billed beyond it
- overhead and profit on change orders; on absorbed change orders the direct cost is a loss
- overhead and profit on the net line variance
Pass-through (not income): subcontractors, materials, allowances, builder's risk,
contingency, allowance fees, owner-supplied items.

The estimate comes from a calculated proposal scenario. The actual column needs an accepted
revision: it uses entered actual costs (or hours) where present, and the contract amount
where nothing has been entered yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .calc import Results, Scenario
from .closeout import COFunding, Ledger
from .models import Performer, Settings
from .proposal import Revision

ZERO = Decimal(0)
KS, CW = "KS", "CW"                     # which side of the business a group belongs to
ENTITY_NAME = {KS: Performer.KEPT_SPEC.value, CW: Performer.CW.value}


@dataclass
class IncomeLine:
    line_id: str
    title: str
    estimate: Decimal
    actual: Decimal | None = None
    entered: bool = False               # actual comes from entered costs/hours


@dataclass
class IncomeGroup:
    name: str
    estimate: Decimal | None
    actual: Decimal | None = None
    note: str = ""
    lines: list[IncomeLine] = field(default_factory=list)
    entity: str = KS                    # rows not tied to a performer belong to Kept Spec (general contractor)


@dataclass
class IncomeReport:
    groups: list[IncomeGroup]
    estimate_total: Decimal
    actual_total: Decimal | None
    contract_price: Decimal             # Total Price of the scenario
    final_price: Decimal | None         # ledger final cost
    lines_without_actuals: int = 0

    def total(self, kind: str = "estimate", entity: str | None = None) -> Decimal | None:
        """kind: "estimate" or "actual"; entity: KS, CW or None for both."""
        if kind == "actual" and self.actual_total is None:
            return None
        vals = [getattr(g, kind) for g in self.groups if entity is None or g.entity == entity]
        return sum((v for v in vals if v is not None), ZERO)

    def share(self, kind: str = "estimate", entity: str | None = None) -> Decimal | None:
        price = self.contract_price if kind == "estimate" else self.final_price
        t = self.total(kind, entity)
        return t / price if (t is not None and price) else None

    @property
    def estimate_margin(self) -> Decimal | None:
        return self.estimate_total / self.contract_price if self.contract_price else None

    @property
    def actual_margin(self) -> Decimal | None:
        if self.actual_total is None or not self.final_price:
            return None
        return self.actual_total / self.final_price


def scenario_income(rev: Revision, results: Results, scenario: Scenario, settings: Settings) -> Decimal:
    return estimate_report(rev, results, scenario, settings).estimate_total


def estimate_report(rev: Revision, results: Results, scenario: Scenario, settings: Settings) -> IncomeReport:
    included = set(scenario.line_ids)
    groups: list[IncomeGroup] = []
    for ent in (KS, CW):
        perfs = set(settings.income_performers(ent))
        lines = [IncomeLine(ln.id, ln.title, results.lines[ln.id].cost)
                 for ln in rev.lines
                 if ln.id in included and ln.performer in perfs and not ln.is_percent and not ln.owner_furnished]
        groups.append(IncomeGroup(f"{ENTITY_NAME[ent]} lines", sum((x.estimate for x in lines), ZERO), lines=lines,
                                  entity=ent))
    for code in settings.co_markup_codes:
        for ln in rev.lines:
            if ln.code == code and ln.id in scenario.percent_items:
                groups.append(IncomeGroup(ln.title, scenario.percent_items[ln.id]))
    mgmt = sum((scenario.percent_items[ln.id] for ln in rev.lines
                if ln.code == settings.co_management_code and ln.id in scenario.percent_items), ZERO)
    groups.append(IncomeGroup("Change order management time", None,
                              note=f"Earned only as change order time is logged; up to ${mgmt:,.2f} "
                                   "from the allowance, more if billed beyond it"))
    for ent in (KS, CW):
        groups.append(IncomeGroup(f"{ENTITY_NAME[ent]} work on change orders", None, entity=ent,
                                  note=f"Change order items performed by {', '.join(settings.income_performers(ent)) or ENTITY_NAME[ent]}"))
    groups.append(IncomeGroup("Overhead and profit on change orders", None, note="From approved change orders"))
    groups.append(IncomeGroup("Overhead and profit on line variance", None,
                              note="From actual costs against the contract"))
    total = sum((g.estimate for g in groups if g.estimate is not None), ZERO)
    return IncomeReport(groups=groups, estimate_total=total, actual_total=None,
                        contract_price=scenario.total, final_price=None)


def _own(co, performers) -> Decimal:
    return sum((it.delta for it in co.items if it.performer in performers), ZERO)


def contract_report(ledger: Ledger, settings: Settings) -> IncomeReport:
    """Estimate and actual for the accepted contract."""
    c = ledger.contract
    rep = estimate_report(c.rev, c.results, c.results.base, settings)
    recon = {lr.line.id: lr for lr in ledger.lines}
    missing = 0
    own_all = set(settings.income_performers())
    for g in rep.groups[:2]:
        for x in g.lines:
            lr = recon.get(x.line_id)
            if lr is None:
                x.actual = x.estimate
            elif lr.actual is not None:
                x.actual, x.entered = lr.actual, True
            elif lr.unused:
                x.actual, x.entered = ZERO, True
            else:
                x.actual = x.estimate
                missing += 1
        g.actual = sum((x.actual for x in g.lines), ZERO)
    for g in rep.groups:
        if g.name == "Change order management time":
            used = ledger.mgmt_used
            billed = sum((ledger.pricing[o.number].mgmt_billed for o in ledger.approved
                          if o.funding is not COFunding.ABSORBED), ZERO)
            g.actual = used + billed
        elif g.name.endswith("work on change orders"):
            perfs = set(settings.income_performers(g.entity))
            g.actual = sum((_own(o, perfs) for o in ledger.approved if o.funding is not COFunding.ABSORBED), ZERO)
        elif g.name == "Overhead and profit on change orders":
            amt = ZERO
            for o in ledger.approved:
                p = ledger.pricing[o.number]
                # absorbed: you pay for others' work; your own work on it simply earns nothing
                amt += -(p.cost_delta - _own(o, own_all)) if o.funding is COFunding.ABSORBED else p.markup
            g.actual = amt
            if any(o.funding is COFunding.ABSORBED for o in ledger.approved):
                g.note = "Absorbed change orders count the cost of others' work as a loss"
        elif g.name == "Overhead and profit on line variance":
            g.actual = ledger.variance_markup
        elif g.actual is None and g.estimate is not None:
            g.actual = g.estimate            # overhead and profit lines are fixed in the contract
    rep.actual_total = sum((g.actual for g in rep.groups if g.actual is not None), ZERO)
    rep.final_price = ledger.total_final
    rep.lines_without_actuals = missing
    return rep
