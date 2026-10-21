"""Data model for the proposal builder.

Money and percentages are Decimal so totals match to the cent. Percent values
are stored as fractions (0.05 = 5%).
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = 1


class _Model(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")


# ---------------------------------------------------------------- enums


class PriceSource(str, Enum):
    FIXED = "fixed"          # unit price typed on the item
    RATE = "rate"            # unit price comes from the rate table
    ALLOWANCE = "allowance"  # unit price comes from an allowance range tier
    PERCENT = "percent"      # price is a fraction of the subtotal


# What the app shows for each price basis. The stored value stays "allowance" for compatibility with saved files;
# on screen it is "range" so it is not confused with the Allowance flag (which is what prints).
BASIS_LABEL = {"fixed": "fixed", "rate": "rate", "allowance": "range", "percent": "percent"}


def basis_label(v) -> str:
    v = getattr(v, "value", v)
    return BASIS_LABEL.get(v, v)


class Performer(str, Enum):
    NONE = ""
    KEPT_SPEC = "Kept Spec Advisors"
    CW = "Convenient Woodworking"
    SUB = "Licensed Sub"
    CLIENT = "Client (owner-furnished)"


class Tier(str, Enum):
    LOW = "low"
    MID = "mid"
    HIGH = "high"


# ---------------------------------------------------------------- catalog


class Unit(_Model):
    code: str
    description: str


class Rate(_Model):
    key: str
    name: str
    unit: str = "HR"
    rate: Decimal


class Section(_Model):
    number: int                 # 100, 200 ... 1400
    name: str
    key: str                    # short identifier, e.g. "MEP"

    @property
    def index(self) -> int:     # 11 for section 1100; used in line IDs
        return self.number // 100


class StockClass(_Model):
    key: str
    name: str
    lengths_ft: list[Decimal]


class AllowanceRange(_Model):
    id: str
    category: str
    description: str
    unit: str
    low: Decimal
    high: Decimal
    basis: str = ""

    @property
    def mid(self) -> Decimal:
        return ((self.low + self.high) / 2).quantize(Decimal("0.01"))

    def price(self, tier: Tier) -> Decimal:
        return {Tier.LOW: self.low, Tier.MID: self.mid, Tier.HIGH: self.high}[tier]


class CatalogItem(_Model):
    code: int
    section: int                          # Section.number
    group: str = ""                       # sub-heading inside a section, e.g. "Electrical"
    title: str
    description: str = ""                 # general description, printed on every use
    unit: str = "LS"
    price_source: PriceSource = PriceSource.FIXED
    price: Decimal | None = None          # FIXED: unit price; PERCENT: fraction
    rate_key: str | None = None           # RATE
    allowance_ids: list[str] = Field(default_factory=list)
    default_tier: Tier = Tier.HIGH
    performer: str = ""                  # a Settings performer name (see Performer for the built-ins)
    stock_class: str | None = None        # stick goods rounding
    is_allowance: bool = False            # lines print "Allowance"; defaults on for allowance-priced items
    not_included: bool = False            # $0 scope-clarity line
    owner_furnished: bool = False
    credit_if_unused: bool = False
    internal_notes: str = ""
    active: bool = True

    @model_validator(mode="before")
    @classmethod
    def _default_allowance(cls, data):
        # catalogs saved before the field existed: flag items priced from or linked to allowance ranges
        if isinstance(data, dict) and "is_allowance" not in data:
            data = {**data, "is_allowance": data.get("price_source") in (PriceSource.ALLOWANCE, "allowance")
                    or bool(data.get("allowance_ids"))}
        return data

    @model_validator(mode="after")
    def _check_source(self) -> "CatalogItem":
        if self.price_source is PriceSource.RATE and not self.rate_key:
            raise ValueError(f"item {self.code}: price_source 'rate' needs rate_key")
        if self.price_source is PriceSource.PERCENT and self.price is None:
            raise ValueError(f"item {self.code}: price_source 'percent' needs price")
        return self


class Catalog(_Model):
    schema_version: int = SCHEMA_VERSION
    units: list[Unit] = Field(default_factory=list)
    rates: list[Rate] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    items: list[CatalogItem] = Field(default_factory=list)
    allowances: list[AllowanceRange] = Field(default_factory=list)
    stock_classes: list[StockClass] = Field(default_factory=list)

    # lookups
    def item(self, code: int) -> CatalogItem | None:
        return next((i for i in self.items if i.code == code), None)

    def rate(self, key: str) -> Rate | None:
        return next((r for r in self.rates if r.key == key), None)

    def allowance(self, id_: str) -> AllowanceRange | None:
        return next((a for a in self.allowances if a.id == id_), None)

    def section(self, number: int) -> Section | None:
        return next((s for s in self.sections if s.number == number), None)

    def unit_price(self, item: CatalogItem, tier: Tier | None = None) -> Decimal | None:
        """Resolved default unit price (fraction for percent items)."""
        if item.price_source is PriceSource.RATE:
            r = self.rate(item.rate_key or "")
            return r.rate if r else None
        if item.price_source is PriceSource.ALLOWANCE:
            if item.allowance_ids:
                a = self.allowance(item.allowance_ids[0])
                if a:
                    return a.price(tier or item.default_tier)
            return item.price
        return item.price

    def unit_options(self, current: str | None = None) -> dict[str, str]:
        """Unit codes for a picker; a code no longer in the list stays selectable so the form still opens."""
        opts = {u.code: u.code for u in self.units}
        if current and current not in opts:
            opts = {current: f"{current} (not in Units)", **opts}
        return opts

    def rename_unit(self, old: str, new: str) -> int:
        """Point catalog items, rates and allowance ranges at a renamed unit. Returns how many changed."""
        n = 0
        for coll in (self.items, self.rates, self.allowances):
            for x in coll:
                if x.unit == old:
                    x.unit = new
                    n += 1
        return n

    def unit_users(self, code: str) -> list[str]:
        return ([f"item {i.code}" for i in self.items if i.unit == code]
                + [f"rate {r.key}" for r in self.rates if r.unit == code]
                + [f"allowance {a.category}: {a.description}" for a in self.allowances if a.unit == code])

    def validate_refs(self) -> list[str]:
        """Return human-readable integrity problems (empty list = clean)."""
        problems: list[str] = []
        codes = [i.code for i in self.items]
        for c in sorted({c for c in codes if codes.count(c) > 1}):
            problems.append(f"duplicate item code {c}")
        sec = {s.number for s in self.sections}
        units = {u.code for u in self.units}
        rates = {r.key for r in self.rates}
        allow = {a.id for a in self.allowances}
        stock = {s.key for s in self.stock_classes}
        for i in self.items:
            if i.section not in sec:
                problems.append(f"item {i.code}: unknown section {i.section}")
            if i.unit not in units:
                problems.append(f"item {i.code}: unknown unit {i.unit}")
            if i.rate_key and i.rate_key not in rates:
                problems.append(f"item {i.code}: unknown rate {i.rate_key}")
            for a in i.allowance_ids:
                if a not in allow:
                    problems.append(f"item {i.code}: unknown allowance {a}")
            if i.stock_class and i.stock_class not in stock:
                problems.append(f"item {i.code}: unknown stock class {i.stock_class}")
        for a in self.allowances:
            if a.unit not in units:
                problems.append(f"allowance {a.id}: unknown unit {a.unit}")
            if a.low > a.high:
                problems.append(f"allowance {a.id}: low > high")
        return problems


# ---------------------------------------------------------------- boilerplate


class BoilerplateBlock(_Model):
    id: str
    heading: str            # group heading, e.g. "Payment Schedule"
    title: str              # sub-heading printed above the body ("" = none)
    body: str               # Markdown; may contain {variables}
    default_on: bool = True
    order: int = 0


class Boilerplate(_Model):
    schema_version: int = SCHEMA_VERSION
    headings: list[str] = Field(default_factory=list)   # print order of groups
    blocks: list[BoilerplateBlock] = Field(default_factory=list)

    def by_heading(self, heading: str) -> list[BoilerplateBlock]:
        return sorted((b for b in self.blocks if b.heading == heading), key=lambda b: b.order)


# ---------------------------------------------------------------- settings


class Variable(_Model):
    name: str               # referenced as {name}
    value: str
    unit: str = ""
    description: str = ""


class Company(_Model):
    legal_name: str = ""
    dba: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    logo_path: str = ""     # relative to the data folder


class PerformerDef(_Model):
    """An entry in the Performer dropdown (Settings > Lists)."""
    name: str
    note: str = ""                       # printed at the start of the line's description; blank prints nothing
    income: str = ""                     # "KS", "CW" or "" (pass-through): which Income column it counts in


def default_performers() -> list[PerformerDef]:
    return [PerformerDef(name=Performer.KEPT_SPEC.value, income="KS"),
            PerformerDef(name=Performer.CW.value, note="Performed by Convenient Woodworking.", income="CW"),
            PerformerDef(name=Performer.SUB.value, note="Performed by a licensed subcontractor."),
            PerformerDef(name=Performer.CLIENT.value, note="Owner-furnished.")]


class Lists(_Model):
    """Editable dropdown lists (Settings > Lists)."""
    co_actions: list[str] = Field(default_factory=lambda: ["Add", "Delete", "Modify"])
    contact_roles: list[str] = Field(default_factory=lambda: ["Owner", "Spouse", "Property manager", "Tenant",
                                                              "Designer", "Realtor"])
    lead_sources: list[str] = Field(default_factory=lambda: ["Referral", "Website", "Repeat client", "Google",
                                                             "Social media", "Sign / yard sign"])
    trades: list[str] = Field(default_factory=lambda: ["Electrical", "Plumbing", "HVAC", "Gas", "Drywall",
                                                       "Painting", "Flooring", "Tile", "Framing", "Insulation",
                                                       "Countertops", "Glass", "Finish carpentry", "Roofing"])
    quote_scopes: list[str] = Field(default_factory=lambda: ["Electrical", "Plumbing", "HVAC", "Painting",
                                                             "Flooring", "Tile", "Drywall", "Countertops"])
    address_labels: list[str] = Field(default_factory=lambda: ["Home", "Site", "Mailing", "Rental", "Office"])


class Settings(_Model):
    schema_version: int = SCHEMA_VERSION
    company: Company = Field(default_factory=Company)
    proposal_year: int = 26
    next_proposal_seq: int = 6
    default_waste_pct: Decimal = Decimal("0.10")
    deposit_pct: Decimal = Decimal("0.25")
    retainage_pct: Decimal = Decimal("0.05")
    validity_days: int = 30
    dark_mode: bool = False
    performers: list[PerformerDef] = Field(default_factory=default_performers)
    lists: Lists = Field(default_factory=Lists)
    license_threshold: Decimal = Decimal("40000")   # warn when a total reaches this; 0 turns the check off
    rfq_note: str = ("Please quote the scope below for the project listed. Include materials, labor and any permits "
                     "for your trade, and list exclusions, assumptions and lead time. Quantities are our takeoff; "
                     "verify on site. Send your quote to {company_email}.")
    comparison_note: str = ("Quotes are the subcontractors' prices for the scope listed. Contingency, overhead and "
                            "profit apply to the selected quote as they do to the rest of the proposal.")
    global_variables: list[Variable] = Field(default_factory=list)
    spelling_words: list[str] = Field(default_factory=list)   # accepted by the spelling check
    # change orders and reconciliation: which catalog codes play which role
    co_markup_codes: list[int] = Field(default_factory=lambda: [1410, 1420])   # overhead, profit
    contingency_code: int = 1310
    co_management_code: int = 1320
    co_management_rate_key: str = "pm"     # rate for change order management hours
    recommended_by: str = "Kept Spec - Nick Matney"

    def performer(self, name: str) -> PerformerDef | None:
        return next((p for p in self.performers if p.name == name), None) if name else None

    def performer_note(self, name: str) -> str:
        p = self.performer(name)
        if p is not None:
            return p.note
        return {d.name: d.note for d in default_performers()}.get(name, "")   # saved proposals with an old name

    def income_performers(self, entity: str | None = None) -> list[str]:
        return [p.name for p in self.performers if p.income and (entity is None or p.income == entity)]

    def performer_names(self) -> list[str]:
        return ["", *(p.name for p in self.performers)]

    def next_proposal_number(self) -> str:
        return f"{self.proposal_year:02d}{self.next_proposal_seq:03d}"
