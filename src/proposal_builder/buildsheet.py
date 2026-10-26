"""Build sheets: the internal cost build-up behind a Convenient Woodworking line (never printed).

A line priced "Built" gets its unit price from its build sheet:

    cost       = setup + qty x (materials + outsourced + hours x shop rate)   per piece
    line price = cost x (1 + overhead % + profit %)       flat, not compounded, like KS percent items
    unit price = line price / qty, rounded up to the rounding step ($5)
    line total = unit price x qty

Setup rows (design, drawings, jigs, CNC programming, one-time materials) are counted once per
line; every other row is per piece. The sheet keeps its own copy of the pricing policy (shop
rate, overhead, profit, rounding, yield factors, rough thickness map) and of every material's
unit cost, so changing Settings or the price references never changes a saved proposal. "Pull
prices" refreshes the material costs on request.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, ConfigDict, Field

ZERO = Decimal(0)
CENT = Decimal("0.01")

MATERIAL_KINDS: dict[str, str] = {
    "lumber": "Lumber", "sheet": "Sheet goods", "veneer": "Veneer", "dimensional": "Dimensional",
    "hardware": "Hardware", "finish": "Finish", "outsourced": "Outsourced", "other": "Other",
}
YIELD_TIERS = ("low", "medium", "high")
DEFAULT_PHASES = ["Design", "Milling", "Joinery and machining", "Assembly", "Sanding", "Finishing",
                  "Hardware and fitting", "Crating", "Delivery and install"]


class _Model(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class RoughThickness(_Model):
    finished: Decimal          # finished thickness (in) this nominal yields, e.g. 0.75
    nominal: str               # "4/4"
    nominal_in: Decimal        # 1.0 (board feet are counted at nominal thickness)


def default_rough_map() -> list[RoughThickness]:
    return [RoughThickness(finished=Decimal(f), nominal=n, nominal_in=Decimal(i)) for f, n, i in
            (("0.75", "4/4", "1"), ("1", "5/4", "1.25"), ("1.25", "6/4", "1.5"), ("1.75", "8/4", "2"),
             ("2.75", "12/4", "3"), ("3.75", "16/4", "4"))]


def rough_for(thickness: Decimal, rough_map: list[RoughThickness]) -> tuple[str, Decimal]:
    """Nominal stock for a finished thickness: the thinnest whose finished size covers it."""
    for r in sorted(rough_map, key=lambda r: r.finished):
        if thickness <= r.finished:
            return r.nominal, r.nominal_in
    q = Decimal(math.ceil((thickness + Decimal("0.25")) * 4)) / 4        # thicker than the map: add 1/4"
    return f"{int(q * 4)}/4", q


class PricingPolicy(_Model):
    """Convenient Woodworking pricing defaults (Settings). Each new build sheet copies them."""
    shop_rate: Decimal = Decimal(75)
    overhead_pct: Decimal = Decimal("0.15")
    profit_pct: Decimal = Decimal("0.10")
    rounding: Decimal = Decimal(5)                 # unit prices round up to this step
    yield_low: Decimal = Decimal("1.25")
    yield_medium: Decimal = Decimal("1.5")
    yield_high: Decimal = Decimal("1.8")
    rough_map: list[RoughThickness] = Field(default_factory=default_rough_map)
    phases: list[str] = Field(default_factory=lambda: list(DEFAULT_PHASES))

    def yield_factor(self, tier: str) -> Decimal:
        return {"low": self.yield_low, "high": self.yield_high}.get(tier, self.yield_medium)


class BuildMaterial(_Model):
    kind: str = "other"                    # MATERIAL_KINDS
    ref: str = ""                          # price reference id it was priced from ("" = typed)
    name: str = ""
    setup: bool = False                    # once per line instead of per piece
    # lumber: parts at finished size; board feet are computed at nominal (rough) thickness
    pieces: Decimal | None = None
    thickness: Decimal | None = None       # finished, inches
    width: Decimal | None = None           # inches
    length: Decimal | None = None          # inches
    yield_tier: str = "medium"
    nominal: str = ""                      # set by recalc, e.g. "8/4"
    priced_as: str = ""                    # nominal the unit cost was taken for
    qty: Decimal = Decimal(1)              # per piece (BF for lumber parts, computed)
    unit: str = "EA"
    coats: Decimal | None = None           # finish: SF x coats
    unit_cost: Decimal = ZERO              # snapshot
    notes: str = ""

    @property
    def has_dims(self) -> bool:
        return self.kind == "lumber" and None not in (self.pieces, self.thickness, self.width, self.length)

    @property
    def has_area(self) -> bool:
        """Veneer: pieces x W x L give square feet."""
        return self.kind == "veneer" and None not in (self.pieces, self.width, self.length)

    @property
    def quantity(self) -> Decimal:
        if self.kind == "finish" and self.coats:
            return self.qty * self.coats
        return self.qty

    @property
    def cost(self) -> Decimal:
        return (self.quantity * self.unit_cost).quantize(CENT, rounding=ROUND_HALF_UP)

    @property
    def stale(self) -> bool:
        """Lumber priced for a different thickness than its parts now need."""
        return self.kind == "lumber" and bool(self.priced_as) and bool(self.nominal) and self.priced_as != self.nominal


class BuildLabor(_Model):
    phase: str = ""
    hours: Decimal = ZERO
    setup: bool = False                    # once per line instead of per piece
    notes: str = ""


@dataclass
class BuildTotals:
    qty: Decimal
    setup_materials: Decimal
    setup_outsourced: Decimal
    setup_hours: Decimal
    unit_materials: Decimal                # per piece
    unit_outsourced: Decimal
    unit_hours: Decimal
    shop_rate: Decimal
    cost: Decimal                          # whole line
    overhead: Decimal
    profit: Decimal
    line_price: Decimal                    # before rounding
    unit_price: Decimal                    # rounded up
    line_total: Decimal

    @property
    def materials(self) -> Decimal:        # whole line, outsourced excluded
        return self.setup_materials + self.qty * self.unit_materials

    @property
    def outsourced(self) -> Decimal:
        return self.setup_outsourced + self.qty * self.unit_outsourced

    @property
    def hours(self) -> Decimal:
        return self.setup_hours + self.qty * self.unit_hours

    @property
    def labor(self) -> Decimal:
        return (self.hours * self.shop_rate).quantize(CENT, rounding=ROUND_HALF_UP)

    @property
    def rounding(self) -> Decimal:
        return self.line_total - self.line_price

    @property
    def effective_rate(self) -> Decimal | None:
        """What each shop hour earns: line total less materials and outsourced, per hour."""
        return ((self.line_total - self.materials - self.outsourced) / self.hours).quantize(CENT) \
            if self.hours else None


class BuildSheet(_Model):
    materials: list[BuildMaterial] = Field(default_factory=list)
    labor: list[BuildLabor] = Field(default_factory=list)
    shop_rate: Decimal = Decimal(75)
    overhead_pct: Decimal = Decimal("0.15")
    profit_pct: Decimal = Decimal("0.10")
    rounding: Decimal = Decimal(5)
    yield_low: Decimal = Decimal("1.25")
    yield_medium: Decimal = Decimal("1.5")
    yield_high: Decimal = Decimal("1.8")
    rough_map: list[RoughThickness] = Field(default_factory=default_rough_map)
    notes: str = ""

    @classmethod
    def from_policy(cls, p: PricingPolicy) -> "BuildSheet":
        return cls(shop_rate=p.shop_rate, overhead_pct=p.overhead_pct, profit_pct=p.profit_pct,
                   rounding=p.rounding, yield_low=p.yield_low, yield_medium=p.yield_medium,
                   yield_high=p.yield_high, rough_map=[r.model_copy() for r in p.rough_map])

    def yield_factor(self, tier: str) -> Decimal:
        return {"low": self.yield_low, "high": self.yield_high}.get(tier, self.yield_medium)

    def recalc(self) -> None:
        """Board feet of lumber parts from their dimensions."""
        for m in self.materials:
            if m.has_dims:
                m.nominal, nom_in = rough_for(m.thickness, self.rough_map)
                bf = m.pieces * nom_in * m.width * m.length / 144 * self.yield_factor(m.yield_tier)
                m.qty = bf.quantize(CENT, rounding=ROUND_HALF_UP)
                m.unit = "BF"
            elif m.has_area:
                sf = m.pieces * m.width * m.length / 144 * self.yield_factor(m.yield_tier)
                m.qty = sf.quantize(CENT, rounding=ROUND_HALF_UP)
                m.unit = "SF"

    def totals(self, qty: Decimal) -> BuildTotals:
        def sums(setup: bool) -> tuple[Decimal, Decimal, Decimal]:
            mats = sum((m.cost for m in self.materials if m.setup == setup and m.kind != "outsourced"), ZERO)
            outs = sum((m.cost for m in self.materials if m.setup == setup and m.kind == "outsourced"), ZERO)
            hrs = sum((x.hours for x in self.labor if x.setup == setup), ZERO)
            return mats, outs, hrs
        s_mat, s_out, s_hrs = sums(True)
        u_mat, u_out, u_hrs = sums(False)
        q = qty if qty and qty > 0 else Decimal(1)
        cost = (s_mat + s_out + s_hrs * self.shop_rate
                + q * (u_mat + u_out + u_hrs * self.shop_rate)).quantize(CENT, rounding=ROUND_HALF_UP)
        overhead = (cost * self.overhead_pct).quantize(CENT, rounding=ROUND_HALF_UP)
        profit = (cost * self.profit_pct).quantize(CENT, rounding=ROUND_HALF_UP)
        line_price = cost + overhead + profit
        step = self.rounding if self.rounding and self.rounding > 0 else CENT
        unit = Decimal(math.ceil(line_price / q / step)) * step
        unit = unit.quantize(CENT)
        return BuildTotals(qty=q, setup_materials=s_mat, setup_outsourced=s_out, setup_hours=s_hrs,
                           unit_materials=u_mat, unit_outsourced=u_out, unit_hours=u_hrs,
                           shop_rate=self.shop_rate, cost=cost, overhead=overhead, profit=profit,
                           line_price=line_price, unit_price=unit, line_total=(unit * q).quantize(CENT))

    def unit_price(self, qty: Decimal) -> Decimal:
        return self.totals(qty).unit_price

    @property
    def empty(self) -> bool:
        return not self.materials and not self.labor
