"""Convenient Enterprises additions to the shared catalog (CE stage 1).

Applied once to an existing catalog (marker in Catalog.migrations) and used to build the seed. Anything the user
deletes later stays deleted. Codes and section numbers stay in 4000 to 4900 (shared-file contract,
docs/ce-requirements.md section 2): 1.10.1 keeps sections tagged "ce" and their items untouched and hidden.

Section billing: "fixed" sections are the fixed fee (deposit and milestones); "estimate" sections are time and
materials, printed as an estimate and billed at actual.
"""

from __future__ import annotations

from decimal import Decimal

from .models import CE, Catalog, CatalogItem, Performer, PriceSource, Rate, Section, Unit

MARKER = "ce-stage1"
D = Decimal
PERF = Performer.CE.value

UNITS = [("MI", "Mile")]   # no new units: the units table prints every unit on KS and CW proposals
RATES = [Rate(key="ce_eng", name="Convenient Enterprises engineering", unit="HR", rate=D(125)),
         Rate(key="ce_travel", name="Convenient Enterprises travel time (half rate)", unit="HR", rate=D("62.50")),
         Rate(key="ce_lodging", name="Lodging (per night)", unit="EA", rate=D(300)),
         Rate(key="ce_mileage", name="Mileage beyond the one-hour zone (IRS 2026 rate)", unit="MI", rate=D("0.725"))]
SECTIONS = [Section(number=4000, name="Engineering (fixed fee)", key="CEFixed", profile=CE, billing="fixed"),
            Section(number=4100, name="Technical support (time and materials)", key="CESupport", profile=CE,
                    billing="estimate"),
            Section(number=4200, name="Travel (time and materials)", key="CETravel", profile=CE, billing="estimate")]


def _rate(code, section, title, rate_key, unit="HR", description=""):
    return CatalogItem(code=code, section=section, title=title, description=description, unit=unit,
                       price_source=PriceSource.RATE, rate_key=rate_key, performer=PERF)


ITEMS = [
    _rate(4010, 4000, "Fixed-fee design package", "ce_eng",
          description="Design, documentation, programming, program delivery, advisory reviews, revisions and "
                      "associated phone and email communication, per Scope and Deliverables."),
    _rate(4020, 4000, "PLC programming", "ce_eng"),
    _rate(4030, 4000, "HMI development", "ce_eng"),
    _rate(4040, 4000, "Robot programming", "ce_eng"),
    _rate(4050, 4000, "ISO 13849-1 verification (SISTEMA)", "ce_eng",
          description="Model the designed safety functions in the IFA SISTEMA tool to calculate and document the "
                      "achieved Performance Level of the safety circuits."),
    CatalogItem(code=4060, section=4000, title="Fixed fee (lump sum)", unit="LS", price=None, performer=PERF),
    CatalogItem(code=4090, section=4000, title="Requirements intake and URS preparation", unit="LS", price=D(0),
                performer=PERF, description="Included at no charge."),
    _rate(4110, 4100, "Onsite support", "ce_eng", description="Billed at actual time."),
    _rate(4120, 4100, "Remote support", "ce_eng", description="To be used after machine run-off and acceptance. "
                                                              "Billed at actual time."),
    _rate(4130, 4100, "Out-of-scope engineering (approved in writing)", "ce_eng"),
    _rate(4210, 4200, "Travel time (one way)", "ce_travel"),
    _rate(4220, 4200, "Lodging (per night)", "ce_lodging", unit="EA"),
    _rate(4230, 4200, "Mileage beyond the one-hour zone (round trip)", "ce_mileage", unit="MI"),
]


def apply(catalog: Catalog) -> bool:
    """Add the Convenient Enterprises content once. Returns True when the catalog changed."""
    if MARKER in catalog.migrations:
        return False
    have_units = {u.code for u in catalog.units}
    catalog.units += [Unit(code=c, description=d) for c, d in UNITS if c not in have_units]
    have_rates = {r.key for r in catalog.rates}
    catalog.rates += [r.model_copy() for r in RATES if r.key not in have_rates]
    have_sec = catalog.reserved_section_numbers()
    catalog.sections += [s.model_copy() for s in SECTIONS if s.number not in have_sec]
    catalog.sections.sort(key=lambda s: s.number)
    have = catalog.reserved_codes()
    catalog.items += [i.model_copy(deep=True) for i in ITEMS if i.code not in have]
    catalog.items.sort(key=lambda i: i.code)
    catalog.migrations.append(MARKER)
    return True
