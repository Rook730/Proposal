"""Calculation engine: variables, stock rounding, line costs, totals, alternates.

Rules (spec section 5):
- line cost = qty x unit price, rounded to cents (half up)
- subtotal = sum of base lines that are not percent items
- each percent item = its fraction x subtotal (flat, no compounding)
- total = subtotal + percent items
- an alternate removes base lines and/or adds its own lines; its percent items
  are recomputed on its own subtotal
"""

from __future__ import annotations

import itertools
import math
import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from .models import Settings, StockClass
from .proposal import Line, Project, Revision

CENT = Decimal("0.01")
VAR_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
SPECIAL_PLACEHOLDERS = {"units_table", "rates_table"}   # rendered by the document layer
DOCUMENT_VARIABLES = {"total_price", "subtotal", "deposit_amount", "progress_amount", "retainage_amount"}


def money(v: Decimal) -> Decimal:
    return v.quantize(CENT, rounding=ROUND_HALF_UP)


def fmt_pct(fraction: Decimal) -> str:
    return f"{(fraction * 100).normalize():f}%"


# ---------------------------------------------------------------- variables


def builtin_variables(project: Project | None, rev: Revision | None, settings: Settings) -> dict[str, str]:
    v = {
        "company_name": settings.company.dba,
        "company_legal_name": settings.company.legal_name,
        "company_address": settings.company.address,
        "company_phone": settings.company.phone,
        "company_email": settings.company.email,
        "deposit_pct": fmt_pct(settings.deposit_pct),
        "retainage_pct": fmt_pct(settings.retainage_pct),
        "validity_days": str(settings.validity_days),
        "waste_pct": fmt_pct(settings.default_waste_pct),
    }
    if project:
        v.update(proposal_number=project.number, client_name=project.client_name,
                 site_address=project.site_address, project_name=project.project_name)
    if rev:
        v.update(revision=rev.rev, proposal_date=rev.proposal_date.strftime("%Y.%m.%d"))
    return v


def variable_map(project: Project | None, rev: Revision | None, settings: Settings) -> dict[str, str]:
    """Built-ins < global variables < proposal variables."""
    v = builtin_variables(project, rev, settings)
    v.update({g.name: g.value for g in settings.global_variables})
    if rev:
        v.update({p.name: p.value for p in rev.variables})
    return v


def render(text: str, variables: dict[str, str]) -> str:
    def sub(m: re.Match) -> str:
        name = m.group(1)
        if name in SPECIAL_PLACEHOLDERS:
            return m.group(0)
        return variables.get(name, m.group(0))
    return VAR_RE.sub(sub, text or "")


def referenced(text: str) -> set[str]:
    return set(VAR_RE.findall(text or ""))


def undefined_references(text: str, variables: dict[str, str]) -> set[str]:
    return {n for n in referenced(text)
            if n not in variables and n not in SPECIAL_PLACEHOLDERS and n not in DOCUMENT_VARIABLES}


def numeric(value: str) -> Decimal:
    """'~90"' -> 90, '$1,200' -> 1200, '25%' -> 25."""
    s = re.sub(r"[^0-9.\-]", "", str(value))
    try:
        return Decimal(s)
    except InvalidOperation:
        raise ValueError(f"variable value {value!r} is not a number")


# ---------------------------------------------------------------- stock rounding


@dataclass
class StockResult:
    takeoff: Decimal
    waste_pct: Decimal
    need: Decimal                      # takeoff x (1 + waste)
    pieces: dict[Decimal, int]         # length ft -> count
    total: Decimal                     # purchased LF

    @property
    def excess(self) -> Decimal:
        return self.total - self.need

    def describe(self) -> str:
        parts = [f"{n} x {length.normalize():f}'" for length, n in sorted(self.pieces.items(), reverse=True)]
        return f"{', '.join(parts)} = {self.total.normalize():f} LF"


def stock_round(takeoff: Decimal, waste_pct: Decimal, lengths_ft: list[Decimal]) -> StockResult:
    """Cheapest-excess combination of stock lengths covering takeoff x (1 + waste).

    Ties are broken by fewer pieces. Works in whole inches.
    """
    need = takeoff * (1 + waste_pct)
    lengths = sorted({int((L * 12).to_integral_value()) for L in lengths_ft if L > 0})
    if not lengths:
        raise ValueError("stock class has no lengths")
    need_in = math.ceil(need * 12)
    limit = need_in + max(lengths)
    INF = 10 ** 9
    best = [INF] * (limit + 1)       # min pieces to make exactly t inches
    choice = [0] * (limit + 1)
    best[0] = 0
    for t in range(1, limit + 1):
        for L in lengths:
            if L <= t and best[t - L] + 1 < best[t]:
                best[t] = best[t - L] + 1
                choice[t] = L
    t = next(t for t in range(max(need_in, 0), limit + 1) if best[t] < INF)
    pieces: dict[Decimal, int] = {}
    rest = t
    while rest > 0:
        L = choice[rest]
        key = (Decimal(L) / 12).normalize()
        pieces[key] = pieces.get(key, 0) + 1
        rest -= L
    return StockResult(takeoff=takeoff, waste_pct=waste_pct, need=need, pieces=pieces,
                       total=(Decimal(t) / 12).normalize())


# ---------------------------------------------------------------- line + totals


@dataclass
class LineResult:
    line: Line
    qty: Decimal
    unit_price: Decimal
    cost: Decimal
    stock: StockResult | None = None
    errors: list[str] = field(default_factory=list)


@dataclass
class Scenario:
    name: str                          # "Base", "Alt 1", "Alt 1 + Alt 2"
    alternates: tuple[int, ...]
    line_ids: list[str]                # lines included (non-percent and percent)
    subtotal: Decimal
    percent_items: dict[str, Decimal]  # line id -> amount
    section_base: dict[int, Decimal]   # section -> total excluding percent items
    section_pct: dict[int, Decimal]    # section -> percent items in that section
    owner_supplied: Decimal = Decimal(0)        # owner-furnished lines' cost: outside subtotal and total
    owner_lines: tuple[str, ...] = ()

    @property
    def percent_total(self) -> Decimal:
        return sum(self.percent_items.values(), Decimal(0))

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.percent_total

    @property
    def total_incl_owner(self) -> Decimal:
        """Whole project cost: Total Price plus what the owner buys directly."""
        return self.total + self.owner_supplied

    def section_total(self, section: int, with_pct: bool = True) -> Decimal:
        base = self.section_base.get(section, Decimal(0))
        return base + (self.section_pct.get(section, Decimal(0)) if with_pct else Decimal(0))


@dataclass
class Results:
    lines: dict[str, LineResult]
    base: Scenario
    alternates: dict[int, Scenario]                  # single alternates
    combinations: list[Scenario]                     # 2+ alternates, compatible only
    conflicts: list[tuple[int, int]]                 # alternate pairs touching the same base line
    errors: list[str]

    def delta(self, alt: int) -> Decimal:
        return self.alternates[alt].total - self.base.total


def line_result(ln: Line, variables: dict[str, str], settings: Settings,
                stock_classes: dict[str, StockClass]) -> LineResult:
    errors: list[str] = []
    stock = None
    qty = ln.qty
    if ln.qty_var:
        try:
            qty = numeric(variables[ln.qty_var])
        except KeyError:
            errors.append(f"{ln.id}: quantity variable {{{ln.qty_var}}} is not defined")
        except ValueError as e:
            errors.append(f"{ln.id}: {e}")
    elif ln.takeoff is not None and ln.stock_class:
        sc = stock_classes.get(ln.stock_class)
        if sc is None:
            errors.append(f"{ln.id}: unknown stock class {ln.stock_class}")
        else:
            waste = ln.waste_pct if ln.waste_pct is not None else settings.default_waste_pct
            stock = stock_round(ln.takeoff, waste, sc.lengths_ft)
            qty = stock.total
    price = ln.unit_price if ln.unit_price is not None else Decimal(0)
    if ln.price_var:
        try:
            price = numeric(variables[ln.price_var])
            if ln.is_percent:
                price = price / 100
        except KeyError:
            errors.append(f"{ln.id}: price variable {{{ln.price_var}}} is not defined")
        except ValueError as e:
            errors.append(f"{ln.id}: {e}")
    cost = Decimal(0) if ln.is_percent else money(qty * price)
    return LineResult(line=ln, qty=qty, unit_price=price, cost=cost, stock=stock, errors=errors)


def _scenario(name: str, alts: tuple[int, ...], rev: Revision, lr: dict[str, LineResult]) -> Scenario:
    removed: set[str] = set()
    for a in alts:
        alt = rev.alternate(a)
        if alt:
            removed |= set(alt.removes)
    included = [ln for ln in rev.lines
                if ln.section in rev.sections
                and ((ln.alternate is None and ln.id not in removed) or (ln.alternate in alts))]
    section_base: dict[int, Decimal] = {}
    subtotal = owner = Decimal(0)
    owner_lines: list[str] = []
    for ln in included:
        if ln.owner_furnished and not ln.is_percent:
            owner += lr[ln.id].cost
            owner_lines.append(ln.id)
            continue
        if not ln.is_percent:
            c = lr[ln.id].cost
            subtotal += c
            section_base[ln.section] = section_base.get(ln.section, Decimal(0)) + c
    pct: dict[str, Decimal] = {}
    section_pct: dict[int, Decimal] = {}
    for ln in included:
        if ln.is_percent:
            amt = money(subtotal * lr[ln.id].unit_price)
            pct[ln.id] = amt
            section_pct[ln.section] = section_pct.get(ln.section, Decimal(0)) + amt
    return Scenario(name=name, alternates=alts, line_ids=[ln.id for ln in included], subtotal=subtotal,
                    percent_items=pct, section_base=section_base, section_pct=section_pct,
                    owner_supplied=owner, owner_lines=tuple(owner_lines))


def calculate(rev: Revision, settings: Settings, stock_classes: list[StockClass],
              project: Project | None = None) -> Results:
    variables = variable_map(project, rev, settings)
    sc = {s.key: s for s in stock_classes}
    lr = {ln.id: line_result(ln, variables, settings, sc) for ln in rev.lines}
    errors = [e for r in lr.values() for e in r.errors]

    base = _scenario("Base", (), rev, lr)
    nums = sorted(a.number for a in rev.alternates)
    alts = {n: _scenario(f"Alt {n}", (n,), rev, lr) for n in nums}

    conflicts = []
    for a, b in itertools.combinations(nums, 2):
        if set(rev.alternate(a).removes) & set(rev.alternate(b).removes):
            conflicts.append((a, b))
    combos = []
    for k in range(2, len(nums) + 1):
        for combo in itertools.combinations(nums, k):
            if any((x, y) in conflicts for x, y in itertools.combinations(combo, 2)):
                continue
            combos.append(_scenario(" + ".join(f"Alt {n}" for n in combo), combo, rev, lr))
    for a in rev.alternates:
        for rid in a.removes:
            if rev.line(rid) is None:
                errors.append(f"Alt {a.number}: removes missing line {rid}")
    return Results(lines=lr, base=base, alternates=alts, combinations=combos,
                   conflicts=conflicts, errors=errors)


def payment_schedule(total: Decimal, settings: Settings) -> dict[str, Decimal]:
    deposit = money(total * settings.deposit_pct)
    retainage = money(total * settings.retainage_pct)
    return {"deposit": deposit, "progress": total - deposit - retainage, "retainage": retainage}
