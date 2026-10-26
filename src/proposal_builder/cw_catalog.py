"""Convenient Woodworking additions to the shared catalog (1.8.0).

Applied once to an existing catalog (marker in Catalog.migrations) and used to build the seed.
Material prices come from Nick's Costing.xlsx (Costing Wood sheet), plus the Ringsend price for
1/2" prefinished maple; hardware prices for the square box template are placeholders to confirm.
Anything the user deletes later stays deleted (the marker prevents re-adding).
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from .buildsheet import BuildLabor, BuildMaterial, BuildSheet, PricingPolicy
from .models import (CW, Catalog, CatalogItem, DimensionalPrice, HardwarePrice, LumberPrice, PriceSource, Rate,
                     Section, SheetPrice, Unit)

MARKER = "cw-1.8.0"
D = Decimal
COSTING = "From Costing.xlsx"


def _slug(*parts: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", "-".join(parts).lower()).strip("-")


UNITS = [("BF", "Board foot"), ("SHT", "Sheet"), ("PC", "Piece"), ("SET", "Set"), ("MI", "Mile")]
RATES = [Rate(key="cw_shop", name="Convenient Woodworking shop rate", unit="HR", rate=D(75)),
         Rate(key="cw_drive", name="Drive time beyond the local delivery area", unit="HR", rate=D(35)),
         Rate(key="cw_mileage", name="Mileage beyond the local delivery area (IRS 2026 rate)", unit="MI",
              rate=D("0.725"))]
SECTIONS = [Section(number=3000, name="Delivery & Installation", key="CWDelivery", profile=CW),
            Section(number=3100, name="Shop-built pieces", key="CWPieces", profile=CW)]

LUMBER = {   # species: {nominal: $/BF rough}
    "Ash": {"4/4": "5", "8/4": "6", "16/4": "8.5"},
    "Aromatic red cedar": {"4/4": "3.9"},
    "Cherry": {"4/4": "6", "8/4": "7.5", "16/4": "9"},
    "Cypress": {"4/4": "5", "8/4": "6", "16/4": "8"},
    "Maple, figured": {"4/4": "7", "8/4": "8", "16/4": "12"},
    "Maple, hard/soft": {"4/4": "5.25", "8/4": "6", "16/4": "7"},
    "Poplar": {"4/4": "4", "8/4": "5", "16/4": "6"},
    "Oak, red": {"4/4": "4", "8/4": "5", "16/4": "6"},
    "Oak, white": {"4/4": "7", "8/4": "8", "16/4": "10"},
    "Walnut": {"4/4": "9", "8/4": "10", "16/4": "12"},
}
SHEETS = [   # product, thickness, width, length, $/sheet
    ("Baltic birch", '1/8"', 60, 60, "50"), ("Baltic birch", '1/4"', 60, 60, "60"),
    ("Baltic birch", '1/2"', 60, 60, "70"), ("Baltic birch", '3/4"', 60, 60, "80"),
    ("Cabinet grade plywood", '1/4"', 48, 96, "30"), ("Cabinet grade plywood", '1/2"', 48, 96, "60"),
    ("Cabinet grade plywood", '3/4"', 48, 96, "70"),
    ("MDF", '1/8"', 48, 96, "15"), ("MDF", '1/4"', 48, 96, "30"), ("MDF", '1/2"', 48, 96, "50"),
    ("MDF", '3/4"', 48, 96, "60"),
]
DIMENSIONAL = [   # material, size, length ft, $/stick, note
    ("Furring strip", "1x2", "8", "1.98", ""), ("Furring strip", "1x3", "8", "2.98", ""),
    ("Furring strip", "1x4", "8", "3.98", ""), ("Furring strip", "2x2", "8", "3.98", ""),
    ("Whitewood", "2x4", "7.71875", "6.48", "92-5/8\" stud"), ("Whitewood", "2x4", "8", "5.98", ""),
    ("Whitewood", "2x4", "10", "11.53", ""),
    ("SPF", "2x6", "8", "11.53", ""), ("SPF", "2x6", "10", "15.98", ""), ("SPF", "2x6", "12", "19.44", ""),
    ("SPF", "2x6", "16", "30.28", ""),
    ("Southern yellow pine", "2x8", "8", "11.98", ""), ("Southern yellow pine", "2x8", "10", "15.98", ""),
    ("Southern yellow pine", "2x8", "12", "19.62", ""), ("Southern yellow pine", "2x8", "16", "33.95", ""),
    ("Southern yellow pine", "2x10", "8", "14.53", ""), ("Southern yellow pine", "2x10", "10", "17.83", ""),
    ("Southern yellow pine", "2x10", "12", "21.44", ""), ("Southern yellow pine", "2x10", "16", "42.63", ""),
    ("Southern yellow pine", "2x12", "8", "16.98", ""), ("Southern yellow pine", "2x12", "10", "22.52", ""),
    ("Southern yellow pine", "2x12", "12", "25.98", ""), ("Southern yellow pine", "2x12", "16", "53.56", ""),
    ("Southern yellow pine", "4x4", "8", "9.25", ""),
    ("Pressure treated #2", "4x4", "8", "11.48", ""), ("Pressure treated #2", "4x4", "10", "17.58", ""),
    ("Pressure treated #2", "4x4", "12", "19.88", ""), ("Pressure treated #2", "4x4", "16", "27.48", ""),
    ("Pressure treated #2", "2x4", "8", "7.78", ""), ("Pressure treated #2", "2x4", "10", "12.88", ""),
    ("Pressure treated #2", "2x4", "12", "14.88", ""), ("Pressure treated #2", "2x4", "16", "19.88", ""),
    ("Pressure treated #2", "2x6", "8", "11.94", ""),
    ("Pressure treated #2", "2x6", "10", "9.29", "Check: lower than the 8 ft price"),
    ("Pressure treated #2", "2x6", "12", "11.57", "Check: lower than the 8 ft price"),
    ("Pressure treated #2", "2x6", "16", "14.42", ""),
    ("Pressure treated #2", "2x8", "8", "14.98", ""), ("Pressure treated #2", "2x8", "10", "19.88", ""),
    ("Pressure treated #2", "2x8", "12", "23.38", ""),
    ("Pressure treated #2", "2x8", "16", "22.02", "Check: lower than the 12 ft price"),
    ("Pressure treated #2", "2x10", "8", "14.82", ""), ("Pressure treated #2", "2x10", "10", "18.70", ""),
    ("Pressure treated #2", "2x10", "12", "22.02", ""), ("Pressure treated #2", "2x10", "16", "28.96", ""),
    ("Pressure treated #2", "2x12", "8", "22.28", ""), ("Pressure treated #2", "2x12", "10", "28.28", ""),
    ("Pressure treated #2", "2x12", "12", "33.28", ""), ("Pressure treated #2", "2x12", "16", "44.38", ""),
]
PLACEHOLDER = "Placeholder price (McMaster price not checked); confirm"
HARDWARE = [HardwarePrice(id="mcm-1647a34", name="Handle", part_number="1647A34", supplier="McMaster-Carr",
                          price=D(8), notes=PLACEHOLDER),
            HardwarePrice(id="mcm-1766a2", name="Latch", part_number="1766A2", supplier="McMaster-Carr",
                          price=D(10), notes=PLACEHOLDER),
            HardwarePrice(id="mcm-1608a42", name='Piano hinge, 12" length', part_number="1608A42",
                          supplier="McMaster-Carr", price=D(15), notes=PLACEHOLDER)]
MAPLE_PREFIN = SheetPrice(id="prefinished-maple-c2-1-2", product="Prefinished maple plywood, C2", thickness='1/2"',
                          price=D(118), supplier="Ringsend", date=date(2026, 10, 25), notes="List price")


def square_box_template(policy: PricingPolicy) -> CatalogItem:
    """The Borg Warner box (25017 / 26006): 10 boxes price at $305 each with the placeholder hardware."""
    b = BuildSheet.from_policy(policy)
    b.materials = [
        BuildMaterial(kind="sheet", ref=MAPLE_PREFIN.id, name='Prefinished maple plywood, C2 1/2"', qty=D("0.3"),
                      unit="SHT", unit_cost=MAPLE_PREFIN.price,
                      notes="3 sheets per 10 boxes (12\" strips for lids, bottoms and sides; ~11.6\" strips for ends)"),
        *[BuildMaterial(kind="hardware", ref=h.id, name=f"{h.name} ({h.supplier} {h.part_number})", qty=D(q),
                        unit="EA", unit_cost=h.price) for h, q in zip(HARDWARE, ("2", "2", "1"))],
    ]
    b.labor = [BuildLabor(phase="Design", hours=D(1), setup=True, notes="Repeat of 25017; mostly reuse"),
               BuildLabor(phase="Joinery and machining", hours=D("1.5"), setup=True,
                          notes="Engraving file, jigs"),
               BuildLabor(phase="Milling", hours=D("0.5"), setup=True, notes="Sheet layout"),
               BuildLabor(phase="Milling", hours=D("0.3"), notes="Sheet breakdown and cutting"),
               BuildLabor(phase="Assembly", hours=D("0.5"), notes="Fastener joinery"),
               BuildLabor(phase="Sanding", hours=D("0.25"), notes="Edges"),
               BuildLabor(phase="Hardware and fitting", hours=D("0.4"), notes="Hinge, latches, handles"),
               BuildLabor(phase="Joinery and machining", hours=D("0.15"), notes="Part number engraving"),
               BuildLabor(phase="Crating", hours=D("0.15"), notes="QC and packing")]
    b.notes = "Hours and hardware prices are first estimates (26006); adjust after the job."
    return CatalogItem(code=3101, section=3100, title="Square box 12 x 12 x 10", unit="EA",
                       price_source=PriceSource.BUILT, build=b,
                       description=('Square box, 12" x 12" x 10" outside. 1/2" prefinished maple plywood, fastener '
                                    "joinery. Hinged lid on a piano hinge, 2 latches, 2 handles. Part number engraved "
                                    "on the bottom."))


def items() -> list[CatalogItem]:
    return [
        CatalogItem(code=3010, section=3000, title="Delivery", unit="LS", price=D(0),
                    description="Delivery within one hour of our shop in Fletcher. No charge."),
        CatalogItem(code=3020, section=3000, title="Mileage beyond the local area", unit="MI",
                    price_source=PriceSource.RATE, rate_key="cw_mileage",
                    description="Round-trip miles beyond one hour of our shop."),
        CatalogItem(code=3030, section=3000, title="Drive time beyond the local area", unit="HR",
                    price_source=PriceSource.RATE, rate_key="cw_drive",
                    description="Round-trip drive time beyond one hour of our shop."),
        CatalogItem(code=3040, section=3000, title="Installation", unit="HR", price_source=PriceSource.RATE,
                    rate_key="cw_shop",
                    description="Installation on site, billed hourly."),
        CatalogItem(code=3050, section=3000, title="Crating", unit="EA", price=None,
                    description="Crating for freight shipment."),
    ]


# ---------------------------------------------------------------- 1.9.0: restoration (Items sheet 2000 to 2690)

RESTORATION_MARKER = "cw-1.9.0-restoration"
RESTORATION_SECTIONS = [
    Section(number=2000, name="Assessment & Documentation", key="CWAssessment", profile=CW),
    Section(number=2100, name="Metalcraft", key="CWMetal", profile=CW),
    Section(number=2200, name="Woodcraft", key="CWWood", profile=CW),
    Section(number=2300, name="Glasscraft", key="CWGlass", profile=CW),
    Section(number=2400, name="Electrical", key="CWElectrical", profile=CW),
    Section(number=2500, name="Allowances", key="CWAllowances", profile=CW),
]
_RESTORE_METAL = ("Restore the metal components to original, like new, condition.\nMedia blast or chem strip existing "
                  "paint/finish, fill pits/holes/cracks, retap mountings, and fab any missing parts, refinish to "
                  "original specs.")
_RESTORE_WOOD = ("Restore the wooden components to original, like new, condition.\nMedia blast or chem strip existing "
                 "paint/finish, fill pits/holes, retap mountings, and fab any missing parts, refinish to original "
                 "specs.")
_REFURB = "Only remove chipping/flaking paint/finish, stabilize any mechanical issues, touchup finish as required."
# code, section, title, description, price (26003 / 26004 where they had one; None = price per job)
RESTORATION_ITEMS = [
    (2010, 2000, "Condition assessment", "Document corrosion, mechanical integrity, missing hardware, electrical "
                                         "condition.", "25"),
    (2020, 2000, "Photography", "Before/during/after documentation at each phase of restoration.", "0"),
    (2030, 2000, "Records", "Plaque with SN (if applicable), origination, restoration date.", "15"),
    (2110, 2100, "Restore", _RESTORE_METAL, "200"),
    (2120, 2100, "Refurbish", "Clean and repair metal components to improve appearance and function.\n" + _REFURB,
     "75"),
    (2130, 2100, "Fabricate - interior", "Fabricate mountings for use as interior fixture.", None),
    (2140, 2100, "Fabricate - exterior", "Fabricate mountings for use as exterior fixture.", None),
    (2210, 2200, "Restore", _RESTORE_WOOD, None),
    (2220, 2200, "Refurbish", "Clean and repair wooden components to improve appearance and function.\n" + _REFURB,
     "75"),
    (2230, 2200, "Fabricate - interior", "Fabricate base for use as interior fixture.", None),
    (2240, 2200, "Fabricate - exterior", "Fabricate base for use as exterior fixture.", None),
    (2310, 2300, "Restore", "Restore the lamp globe to original, like new, condition.\nClean and polish existing "
                            "(undamaged) globes. Source replacements for broken globes (if possible).", None),
    (2320, 2300, "Refurbish", "Clean and polish lamp globe to improve appearance and function.", "45"),
    (2410, 2400, "Restore", "", None),
    (2420, 2400, "Refurbish", "Remove existing bulb base and all original wiring.\nInstall E26 lampholder to accept "
                              "off-the-shelf LED bulbs.\nRewire to exterior code standard (worst-case location).\n"
                              "Install switched 3-wire grounded cord and plug (interior/lamp use) OR junction box "
                              "pigtail leads (pole/post-mount use).", "60"),
    (2510, 2500, "Bulbs", "Final bulb selection depends on mounting/display location and use. Worst case cost "
                          "scenario provided.", "15"),
    (2520, 2500, "Weatherproofing", "Necessary for exterior located fixtures. Globes sealed with RTV silicone, "
                                    "corrosion inhibitor applied to all unpainted surfaces, all exterior ferrous "
                                    "fasteners substituted with stainless.", "25"),
    (2530, 2500, "Finishes", "Allowance to purchase necessary paint, penetrating finishes, film finishes, etc.", "50"),
    # Items sheet 2600 Delivery & Installation joins the 3000 section (3010 Delivery replaces 2610)
    (2620, 3000, "White glove installation", "White glove installation at a location of your choice.", "0"),
    (2630, 3000, "Installation - exterior", "Installation of fixture base. Electrical hookup not included.", "75"),
]


def apply_restoration(catalog: Catalog) -> bool:
    if RESTORATION_MARKER in catalog.migrations:
        return False
    have_sec = {s.number for s in catalog.sections}
    catalog.sections += [s.model_copy() for s in RESTORATION_SECTIONS if s.number not in have_sec]
    catalog.sections.sort(key=lambda s: s.number)
    have = {i.code for i in catalog.items}
    catalog.items += [CatalogItem(code=c, section=sec, title=t, description=d, unit="EA",
                                  price=D(p) if p is not None else None)
                      for c, sec, t, d, p in RESTORATION_ITEMS if c not in have]
    catalog.items.sort(key=lambda i: i.code)
    catalog.migrations.append(RESTORATION_MARKER)
    return True


def apply(catalog: Catalog, policy: PricingPolicy | None = None) -> bool:
    """Add the Convenient Woodworking content once. Returns True when the catalog changed."""
    if MARKER in catalog.migrations:
        return False
    have_units = {u.code for u in catalog.units}
    catalog.units += [Unit(code=c, description=d) for c, d in UNITS if c not in have_units]
    have_rates = {r.key for r in catalog.rates}
    catalog.rates += [r.model_copy() for r in RATES if r.key not in have_rates]
    have_sec = {s.number for s in catalog.sections}
    catalog.sections += [s.model_copy() for s in SECTIONS if s.number not in have_sec]
    catalog.sections.sort(key=lambda s: s.number)
    have_items = {i.code for i in catalog.items}
    new_items = items() + [square_box_template(policy or PricingPolicy())]
    catalog.items += [i for i in new_items if i.code not in have_items]
    catalog.items.sort(key=lambda i: i.code)
    pr = catalog.prices
    if not pr.lumber:
        pr.lumber = [LumberPrice(id=_slug(sp, t), species=sp, thickness=t, price=D(p), notes=COSTING)
                     for sp, ts in LUMBER.items() for t, p in ts.items()]
    if not pr.sheets:
        pr.sheets = [SheetPrice(id=_slug(n, t), product=n, thickness=t, width_in=D(w), length_in=D(l), price=D(p),
                                notes=COSTING) for n, t, w, l, p in SHEETS] + [MAPLE_PREFIN.model_copy()]
    if not pr.dimensional:
        pr.dimensional = [DimensionalPrice(id=_slug(m, s, L), material=m, size=s, length_ft=D(L), price=D(p),
                                           notes=(note + "; " if note else "") + COSTING)
                          for m, s, L, p, note in DIMENSIONAL]
    if not pr.hardware:
        pr.hardware = [h.model_copy() for h in HARDWARE]
    catalog.migrations.append(MARKER)
    return True


def apply_all(catalog: Catalog, policy: PricingPolicy | None = None) -> bool:
    a = apply(catalog, policy)
    b = apply_restoration(catalog)
    return a or b


# ---------------------------------------------------------------- terms library additions

TERMS_MARKER = "cw-1.9.0"
CLIENT_PROPERTY = ("client-property", "Terms & Conditions", "Client property in our care", (
    "Items you leave with us for restoration or repair are kept in our shop and handled with care. We note their "
    "condition when we receive them; we are not responsible for damage or defects that were already present or that "
    "the work uncovers. Items not picked up within {storage_grace_days} days of our notice that the work is complete "
    "are charged storage at {storage_rate} per square foot of floor space per month, with a minimum of {storage_min} "
    "per month. Please keep items of significant value insured under your own policy."), 45)


def apply_terms(boilerplate) -> bool:
    """Add blocks introduced after a Convenient Woodworking library was created (once)."""
    from .models import BoilerplateBlock
    if TERMS_MARKER in boilerplate.migrations:
        return False
    bid, heading, title, body, order = CLIENT_PROPERTY
    if not any(b.id == bid for b in boilerplate.blocks):
        boilerplate.blocks.append(BoilerplateBlock(id=bid, heading=heading, title=title, body=body, order=order))
        if heading not in boilerplate.headings:
            boilerplate.headings.append(heading)
    boilerplate.migrations.append(TERMS_MARKER)
    return True
