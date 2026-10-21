"""Change orders and the whole-project reconciliation (spec sections 7 and 9).

Change orders
- cost delta = final cost - original cost, summed over the CO's items (direct cost, no management time)
- CO price = cost delta x (1 + overhead % + profit %) from the accepted revision
- funding: contingency (drawn at CO price, overflow billed to the client), client, or absorbed
- management time: hours on each CO x the contract's project management rate, drawn from the
  change order management allowance (item 1320); time beyond the allowance is billed at the rate

Reconciliation ("Final Project Ledger")
  original contract value (accepted revision total)
+ approved change orders billed to the client
+ net line variance (actual - budget, lines with actuals or marked unused)
+ overhead and profit on the net variance
- unused contingency
- unused change order management allowance
= total final project cost
- costs the client paid directly to subs and suppliers
- payments received by Kept Spec
= balance due
"""

from __future__ import annotations

from dataclasses import dataclass, field
import datetime as dt
from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from .calc import Results, calculate, money
from .models import Performer, Settings, StockClass
from .proposal import Line, Project, Revision, RevisionState

ZERO = Decimal(0)


class _Model(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


# ---------------------------------------------------------------- change orders


class COAction(str, Enum):
    ADD = "Add"
    DELETE = "Delete"
    MODIFY = "Modify"


class COFunding(str, Enum):
    CONTINGENCY = "Contingency"
    CLIENT = "Client"
    ABSORBED = "Absorbed by Kept Spec"


class COStatus(str, Enum):
    DRAFT = "Draft"
    ISSUED = "Issued"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class COItem(_Model):
    description: str = ""              # condition / reason
    action: str = COAction.MODIFY.value    # Settings > Lists > change order actions
    change: str = ""                   # what is added, deleted or modified
    line_ids: list[str] = Field(default_factory=list)
    performer: str = ""                    # Settings performer name; income performers count as income
    contractor_id: str | None = None       # crm.Contractor when a sub does the work
    original_cost: Decimal = ZERO
    final_cost: Decimal = ZERO

    @property
    def delta(self) -> Decimal:
        return self.final_cost - self.original_cost


class ChangeOrder(_Model):
    number: str                        # "26005-01"
    title: str = ""
    requested: date = Field(default_factory=date.today)
    items: list[COItem] = Field(default_factory=list)
    sow: str = ""                      # SOW modifications
    payment_impacts: str = "No impacts to payment progress or payment terms."
    schedule_impacts: str = "No impacts to schedule."
    funding: COFunding = COFunding.CLIENT
    mgmt_hours: Decimal = ZERO         # time spent managing this change
    status: COStatus = COStatus.DRAFT
    approved: date | None = None
    recommended_by: str = ""
    approved_by: str = ""

    @property
    def cost_delta(self) -> Decimal:
        return sum((i.delta for i in self.items), ZERO)

    @property
    def locked(self) -> bool:
        return self.status in (COStatus.APPROVED, COStatus.REJECTED)


class ChangeOrderLog(_Model):
    schema_version: int = 1
    orders: list[ChangeOrder] = Field(default_factory=list)

    def next_number(self, project_number: str) -> str:
        n = 1
        used = {o.number for o in self.orders}
        while f"{project_number}-{n:02d}" in used:
            n += 1
        return f"{project_number}-{n:02d}"

    def get(self, number: str) -> ChangeOrder | None:
        return next((o for o in self.orders if o.number == number), None)


# ---------------------------------------------------------------- reconciliation data


class PaidBy(str, Enum):
    KEPT_SPEC = "Kept Spec"
    CLIENT = "Client direct"


class ActualCost(_Model):
    line_id: str
    date: dt.date | None = None
    vendor: str = ""
    description: str = ""
    hours: Decimal | None = None       # hourly lines: amount defaults to hours x line rate
    amount: Decimal | None = None
    tax: Decimal = ZERO
    paid_by: PaidBy = PaidBy.KEPT_SPEC


class Payment(_Model):
    draw: str = ""
    milestone: str = ""
    date: dt.date | None = None
    amount: Decimal = ZERO


class Reconciliation(_Model):
    schema_version: int = 1
    actuals: list[ActualCost] = Field(default_factory=list)
    unused_lines: list[str] = Field(default_factory=list)      # lines credited in full
    payments: list[Payment] = Field(default_factory=list)
    note: str = ("This ledger reflects all approved change orders and reconciliations as of the date above. "
                 "A copy of each signed change order can be found in the provided as-built documentation.")


# ---------------------------------------------------------------- contract context


def accepted_revision(revs: list[Revision]) -> Revision | None:
    """The accepted revision (latest one marked Accepted)."""
    acc = [r for r in revs if r.state is RevisionState.ACCEPTED]
    return acc[-1] if acc else None


@dataclass
class Contract:
    rev: Revision
    results: Results
    markup_pct: Decimal                 # overhead + profit
    contingency: Decimal
    co_management: Decimal
    contingency_line: str | None
    co_management_line: str | None
    mgmt_rate: Decimal = ZERO           # contract's project management rate
    license_threshold: Decimal = ZERO   # 0 = no check

    @property
    def total(self) -> Decimal:
        return self.results.base.total


def contract_context(rev: Revision, settings: Settings, stock: list[StockClass],
                     project: Project | None = None) -> Contract:
    res = calculate(rev, settings, stock, project)
    by_code: dict[int, list[Line]] = {}
    for ln in rev.lines:
        if ln.is_percent and ln.code is not None and ln.id in res.base.percent_items:
            by_code.setdefault(ln.code, []).append(ln)
    markup = sum((res.lines[ln.id].unit_price for c in settings.co_markup_codes for ln in by_code.get(c, [])), ZERO)
    cont = by_code.get(settings.contingency_code, [])
    mgmt = by_code.get(settings.co_management_code, [])
    pm_line = next((ln for ln in rev.lines if ln.rate_key == settings.co_management_rate_key
                    and ln.unit_price is not None), None)
    return Contract(
        rev=rev, results=res, markup_pct=markup,
        contingency=sum((res.base.percent_items[ln.id] for ln in cont), ZERO),
        co_management=sum((res.base.percent_items[ln.id] for ln in mgmt), ZERO),
        contingency_line=cont[0].id if cont else None,
        co_management_line=mgmt[0].id if mgmt else None,
        mgmt_rate=pm_line.unit_price if pm_line else ZERO,
        license_threshold=settings.license_threshold,
    )


# ---------------------------------------------------------------- change order pricing


@dataclass
class COPricing:
    number: str
    cost_delta: Decimal
    markup: Decimal
    price: Decimal                     # cost delta + markup
    from_contingency: Decimal          # drawn from contingency
    billed: Decimal                    # added to the client's contract (work + management overflow)
    contingency_after: Decimal
    mgmt_hours: Decimal = ZERO
    mgmt_cost: Decimal = ZERO          # hours x rate
    mgmt_from_allowance: Decimal = ZERO
    mgmt_billed: Decimal = ZERO        # beyond the allowance
    mgmt_allowance_after: Decimal = ZERO


def price_change_orders(log: ChangeOrderLog, contract: Contract,
                        include: tuple[COStatus, ...] = (COStatus.APPROVED,)) -> dict[str, COPricing]:
    """Price COs in number order; contingency and the management allowance are consumed only by COs in `include`."""
    remaining = contract.contingency
    mgmt_left = contract.co_management
    out: dict[str, COPricing] = {}
    for co in sorted(log.orders, key=lambda o: o.number):
        delta = co.cost_delta
        price = money(delta * (1 + contract.markup_pct))
        markup = price - delta
        draw, billed = ZERO, ZERO
        counts = co.status in include
        if co.funding is COFunding.ABSORBED:
            billed = ZERO
        elif co.funding is COFunding.CONTINGENCY and price > 0:
            draw = min(price, remaining)
            billed = price - draw
        else:
            billed = price
        after = remaining - draw
        mgmt_cost = money(co.mgmt_hours * contract.mgmt_rate)
        mgmt_draw = min(mgmt_cost, mgmt_left) if mgmt_cost > 0 else ZERO
        mgmt_billed = ZERO if co.funding is COFunding.ABSORBED else mgmt_cost - mgmt_draw
        mgmt_after = mgmt_left - mgmt_draw
        if counts:
            remaining = after
            mgmt_left = mgmt_after
        out[co.number] = COPricing(co.number, delta, markup, price, draw, billed + mgmt_billed, after,
                                   co.mgmt_hours, mgmt_cost, mgmt_draw, mgmt_billed, mgmt_after)
    return out


# ---------------------------------------------------------------- ledger


@dataclass
class LineRecon:
    line: Line
    budget: Decimal
    actual: Decimal | None             # None = no actuals entered (carried at budget)
    unused: bool
    client_paid: Decimal

    @property
    def variance(self) -> Decimal:
        if self.unused:
            return -self.budget + (self.actual or ZERO)
        return ZERO if self.actual is None else self.actual - self.budget


@dataclass
class Ledger:
    contract: Contract
    pricing: dict[str, COPricing]
    approved: list[ChangeOrder]
    lines: list[LineRecon]
    co_billed: Decimal
    contingency_used: Decimal
    unused_contingency: Decimal
    mgmt_used: Decimal
    co_management_credit: Decimal      # unused change order management allowance
    net_variance: Decimal
    variance_markup: Decimal
    total_final: Decimal
    client_direct: Decimal
    payments_received: Decimal
    balance_due: Decimal
    warnings: list[str] = field(default_factory=list)

    @property
    def lines_with_activity(self) -> list[LineRecon]:
        return [lr for lr in self.lines if lr.actual is not None or lr.unused]


def actual_amount(a: ActualCost, line: Line | None) -> Decimal:
    base = a.amount
    if base is None:
        rate = line.unit_price if line and line.unit_price is not None else ZERO
        base = money((a.hours or ZERO) * rate)
    return base + (a.tax or ZERO)


def build_ledger(contract: Contract, log: ChangeOrderLog, recon: Reconciliation) -> Ledger:
    rev, res = contract.rev, contract.results
    pricing = price_change_orders(log, contract)
    approved = [o for o in sorted(log.orders, key=lambda o: o.number) if o.status is COStatus.APPROVED]
    co_billed = sum((pricing[o.number].billed for o in approved), ZERO)
    used = sum((pricing[o.number].from_contingency for o in approved), ZERO)
    mgmt_used = sum((pricing[o.number].mgmt_from_allowance for o in approved), ZERO)

    warnings: list[str] = []
    by_line: dict[str, list[ActualCost]] = {}
    known = {ln.id for ln in rev.lines}
    for a in recon.actuals:
        if a.amount is None and a.hours is None:
            continue                       # incomplete entry: no amount or hours yet
        if a.line_id not in known:
            warnings.append(f"Actual cost for unknown line {a.line_id} ({a.vendor} {a.amount}) is ignored")
            continue
        by_line.setdefault(a.line_id, []).append(a)

    lines: list[LineRecon] = []
    for ln in rev.lines:
        if ln.is_percent or ln.section not in rev.sections or ln.alternate is not None:
            continue
        entries = by_line.get(ln.id, [])
        if ln.owner_furnished:
            if entries:
                warnings.append(f"{ln.id} {ln.title}: owner-supplied, so its actual costs are not reconciled")
            continue
        actual = sum((actual_amount(a, ln) for a in entries), ZERO) if entries else None
        client_paid = sum((actual_amount(a, ln) for a in entries if a.paid_by is PaidBy.CLIENT), ZERO)
        lines.append(LineRecon(ln, res.lines[ln.id].cost, actual, ln.id in recon.unused_lines, client_paid))

    net_var = sum((lr.variance for lr in lines), ZERO)
    var_markup = money(net_var * contract.markup_pct)
    unused_cont = contract.contingency - used
    mgmt_credit = contract.co_management - mgmt_used
    total_final = contract.total + co_billed + net_var + var_markup - unused_cont - mgmt_credit
    client_direct = sum((lr.client_paid for lr in lines), ZERO)
    received = sum((p.amount for p in recon.payments), ZERO)
    for lr in lines:
        if lr.actual is None and not lr.unused and lr.line.credit_if_unused:
            warnings.append(f"{lr.line.id} {lr.line.title}: credit-if-unused line has no actuals; "
                            "mark it unused or enter its cost")
    if contract.co_management and not contract.mgmt_rate and any(o.mgmt_hours for o in approved):
        warnings.append("No project management rate found on the contract; change order hours are priced at $0")
    project_cost = contract.total + res.base.owner_supplied + co_billed
    if contract.license_threshold and project_cost >= contract.license_threshold:
        warnings.append(f"Contract, owner-supplied items and approved change orders total ${project_cost:,.2f}, "
                        f"at or above the ${contract.license_threshold:,.0f} general contractor license threshold")
    return Ledger(contract, pricing, approved, lines, co_billed, used, unused_cont, mgmt_used, mgmt_credit, net_var,
                  var_markup, total_final, client_direct, received,
                  total_final - client_direct - received, warnings)
