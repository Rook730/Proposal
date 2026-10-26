"""Build sheets: the internal cost build-up behind a Convenient Woodworking line (never printed).

A line priced "Built" gets its unit price from its build sheet:

    cost       = setup + qty x (materials + outsourced + hours x shop rate)   per piece
                 (rows marked "buy whole" round the line's quantity up to whole sheets or sticks first)
    line price = cost x (1 + overhead % + profit %)       markups on cost, flat, like KS percent items
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
    """Nominal stock for a finished thickness: the thinnest whose finished size covers it. Thicker than the map
    (a glue-up): priced at the thickest nominal's rate, board feet counted at the thickness plus 1/4"."""
    ordered = sorted(rough_map, key=lambda r: r.finished)
    for r in ordered:
        if thickness <= r.finished:
            return r.nominal, r.nominal_in
    q = Decimal(math.ceil((thickness + Decimal("0.25")) * 4)) / 4
    return (ordered[-1].nominal if ordered else f"{int(q * 4)}/4"), q


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
    typed_cost: bool = False               # unit cost typed by hand: Pull prices leaves it alone
    buy_whole: bool = False                # round the line's quantity up to whole units (sheets, sticks)
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
        """Per piece (or once, for setup rows), before buying whole units."""
        return (self.quantity * self.unit_cost).quantize(CENT, rounding=ROUND_HALF_UP)

    def line_quantity(self, qty: Decimal) -> Decimal:
        """Quantity bought for a line of qty pieces."""
        n = self.quantity if self.setup else self.quantity * qty
        return Decimal(math.ceil(n)) if self.buy_whole else n

    def line_cost(self, qty: Decimal) -> Decimal:
        return (self.line_quantity(qty) * self.unit_cost).quantize(CENT, rounding=ROUND_HALF_UP)

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
    materials: Decimal                     # whole line, outsourced excluded, whole units bought
    outsourced: Decimal                    # whole line
    setup_materials: Decimal               # included in materials
    whole_units: Decimal                   # included in materials: extra from buying whole sheets / sticks
    setup_hours: Decimal
    unit_hours: Decimal
    shop_rate: Decimal
    cost: Decimal                          # whole line
    overhead: Decimal
    profit: Decimal
    line_price: Decimal                    # before rounding
    unit_price: Decimal                    # rounded up
    line_total: Decimal

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
        """Labor + profit per shop hour: the line total less materials, outsourced work and overhead (a cost),
        per hour. Includes the price rounding."""
        return ((self.line_total - self.materials - self.outsourced - self.overhead) / self.hours).quantize(CENT) \
            if self.hours else None

    @property
    def profit_margin(self) -> Decimal | None:
        """Profit as a share of the price (the profit % is a markup on cost)."""
        return self.profit / self.line_price if self.line_price else None


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

    def apply_policy(self, p: PricingPolicy) -> None:
        """Take the current rates (a template added to a proposal follows Settings, not the rates it was saved
        with); materials and labor stay."""
        self.shop_rate, self.overhead_pct, self.profit_pct, self.rounding = (p.shop_rate, p.overhead_pct,
                                                                             p.profit_pct, p.rounding)
        self.yield_low, self.yield_medium, self.yield_high = p.yield_low, p.yield_medium, p.yield_high
        self.rough_map = [r.model_copy() for r in p.rough_map]
        self.recalc()

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
        q = qty if qty and qty > 0 else Decimal(1)
        mats = sum((m.line_cost(q) for m in self.materials if m.kind != "outsourced"), ZERO)
        outs = sum((m.line_cost(q) for m in self.materials if m.kind == "outsourced"), ZERO)
        s_mat = sum((m.cost for m in self.materials if m.setup and m.kind != "outsourced"), ZERO)
        exact = sum(((m.quantity if m.setup else m.quantity * q) * m.unit_cost for m in self.materials), ZERO)
        whole = (mats + outs - exact).quantize(CENT, rounding=ROUND_HALF_UP) \
            if any(m.buy_whole for m in self.materials) else ZERO
        s_hrs = sum((x.hours for x in self.labor if x.setup), ZERO)
        u_hrs = sum((x.hours for x in self.labor if not x.setup), ZERO)
        cost = (mats + outs + (s_hrs + q * u_hrs) * self.shop_rate).quantize(CENT, rounding=ROUND_HALF_UP)
        overhead = (cost * self.overhead_pct).quantize(CENT, rounding=ROUND_HALF_UP)
        profit = (cost * self.profit_pct).quantize(CENT, rounding=ROUND_HALF_UP)
        line_price = cost + overhead + profit
        step = self.rounding if self.rounding and self.rounding > 0 else CENT
        unit = Decimal(math.ceil(line_price / q / step)) * step
        unit = unit.quantize(CENT)
        return BuildTotals(qty=q, materials=mats, outsourced=outs, setup_materials=s_mat, whole_units=whole,
                           setup_hours=s_hrs, unit_hours=u_hrs,
                           shop_rate=self.shop_rate, cost=cost, overhead=overhead, profit=profit,
                           line_price=line_price, unit_price=unit, line_total=(unit * q).quantize(CENT))

    def unit_price(self, qty: Decimal) -> Decimal:
        return self.totals(qty).unit_price

    @property
    def empty(self) -> bool:
        return not self.materials and not self.labor


# ---------------------------------------------------------------- pricing from Catalog > Price references


def price_material(m: BuildMaterial, prices, sheet: BuildSheet) -> bool:
    """Set the unit cost from the price references. Lumber is priced for the nominal its parts need.
    Returns False when no price was found."""
    if m.kind == "lumber":
        if m.thickness is not None:
            m.nominal, _ = rough_for(m.thickness, sheet.rough_map)
        species = m.ref or m.name
        lp = prices.lumber_price(species, m.nominal) if m.nominal else None
        if lp is None:
            return False
        m.unit_cost, m.priced_as, m.ref = lp.price, lp.thickness, lp.species
        return True
    ref = prices.find(m.kind, m.ref) if m.ref else None
    if ref is None:
        return False
    if m.kind == "finish":
        m.unit_cost = ref.per_sf_coat
        if m.coats is None and ref.coats:
            m.coats = ref.coats                   # the product's coat count unless the row has its own
    else:
        m.unit_cost = ref.price
    return True


def pull_prices(sheet: BuildSheet, prices) -> tuple[list[str], list[str]]:
    """Refresh unit costs from the price references. Rows with a typed cost are kept; lumber entered directly
    as board feet (no part dimensions) is left alone. Returns (not found, kept typed)."""
    sheet.recalc()
    typed = [m.name for m in sheet.materials if m.typed_cost]
    linked = [m for m in sheet.materials if not m.typed_cost and ((m.ref and m.kind != "lumber") or m.has_dims)]
    missing = [m.name for m in linked if not price_material(m, prices, sheet)]
    return missing, typed
