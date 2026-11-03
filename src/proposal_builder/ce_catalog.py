"""Convenient Enterprises additions to the shared catalog (CE stage 1).

Applied once to an existing catalog (marker in Catalog.migrations) and used to build the seed. Anything the user
deletes later stays deleted. Codes and section numbers stay in 4000 to 4900 (shared-file contract,
docs/ce-requirements.md section 2): 1.10.1 keeps sections tagged "ce" and their items untouched and hidden.

Section billing: "fixed" sections are the fixed fee (deposit and milestones); "estimate" sections are time and
materials, printed as an estimate and billed at actual.
"""

from __future__ import annotations

from decimal import Decimal

from .models import (
    CE,
    Catalog,
    CatalogItem,
    Performer,
    PriceSource,
    Rate,
    Section,
    Unit,
)

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


# ---------------------------------------------------------------- stage 2 (Detailed depth)

STAGE2 = "ce-stage2"
HARDWARE_SECTION = 4300
HARDWARE_CODE = 4310
STAGE2_SECTIONS = [Section(number=HARDWARE_SECTION, name="Hardware (procured by the Consultant)", key="CEHardware",
                           profile=CE, billing="estimate")]
STAGE2_ITEMS = [CatalogItem(code=HARDWARE_CODE, section=HARDWARE_SECTION, title="Hardware procured by the Consultant",
                            unit="LS", price=D(0), performer=PERF,
                            description="Billed at invoiced cost plus the sourcing fee. Items marked Consultant in "
                                        "the bill of materials.")]

# Library blocks for Detailed depth (off in Letter depth; the depth switch turns them on): heading, id, title, body, order
DETAILED_BLOCKS = [
    ("Material", "bom", "Bill of materials", "{bom_table}", 20),
    ("Time Table", "timeline", "Schedule", "{timeline_table}", 20),
    ("Cost", "milestones", "Milestone payments", "{milestone_table}", 25),
    ("Assumptions", "assumptions", "", (
        "- The existing machine is mechanically sound and its current controls documentation is accurate.\n"
        "- Client staff and the machine are available for the onsite days as scheduled.\n"
        "- TBD: project-specific assumptions and risks."), 10),
]
DETAILED_IDS = tuple(b[1] for b in DETAILED_BLOCKS)


# Library blocks for URS-response depth (stage 3): M17 compliance, M18 system description, M19 commercial items.
STAGE3 = "ce-stage3"
URS_HEADINGS = (("Requirements", "Scope"), ("System Description", "Requirements"), ("Commercial", "Cost"))
_SD = "TBD: describe {} (or turn this block off on the Proposal text tab)."
URS_BLOCKS = [
    ("Requirements", "compliance-intro", "", (
        "This proposal responds to the Client's User Requirements Specification {urs_reference}. Each requirement's "
        "compliance is listed below. Deviations and clarifications are detailed on the attached URS Response "
        "Form; any requirement not listed there will be met as written."), 10),
    ("Requirements", "compliance", "Compliance matrix", "{compliance_table}", 20),
    ("System Description", "sd-loading", "Loading and unloading", _SD.format("how parts are loaded and unloaded"),
     10),
    ("System Description", "sd-machine-layout", "Machine layout", _SD.format("the machine layout"), 20),
    ("System Description", "sd-cell-layout", "Cell layout", _SD.format("the cell layout"), 30),
    ("System Description", "sd-data", "Data collection and management",
     _SD.format("the data collection and management scheme"), 40),
    ("System Description", "sd-controls", "Controls functionality and operating modes",
     _SD.format("the controls functionality and the automatic and manual modes"), 50),
    ("System Description", "sd-hmi", "HMI screens", _SD.format("the HMI screens (titles or examples)"), 60),
    ("System Description", "sd-sequence", "Order of operations",
     _SD.format("the order of operations in automatic and manual modes"), 70),
    ("System Description", "sd-quality", "Quality checks", _SD.format("the quality checks"), 80),
    ("System Description", "sd-cycle", "Estimated cycle time",
     _SD.format("the estimated cycle time, broken down into manual and automatic operations"), 90),
    ("System Description", "sd-recipes", "Recipes", _SD.format("the recipe layout and ingredients"), 100),
    ("Commercial", "commercial", "Capital, tooling and major components", "{commercial_table}", 10),
    ("Commercial", "training", "Training and support", (
        "On-site training and support for the duration of installation is included. Additional on-site training "
        "and support: TBD days, to be used consecutively within TBD months of installation."), 20),
    ("Commercial", "warranty", "Warranty", "TBD: warranty and any extended warranty offered.", 30),
    ("Commercial", "shipping", "Crating, insurance and shipment",
     "TBD: skidding, crating and protection, insurance and method of shipment.", 40),
    ("Commercial", "ongoing-support", "Ongoing support", (
        "Technical support and field service are provided by the Consultant from Fletcher, NC. Remote "
        "troubleshooting: response within TBD business hours by phone. On-site break-down repairs and scheduled "
        "maintenance: TBD. Unplanned break-down support is billed at {eng_rate}/hr plus travel. Emergency service "
        "agreement: TBD."), 50),
]
URS_IDS = tuple(b[1] for b in URS_BLOCKS)


def upgrade_library_stage3(bp) -> bool:
    """URS-response blocks and their headings (Requirements, System Description, Commercial), once."""
    from .models import BoilerplateBlock
    if STAGE3 in bp.migrations:
        return False
    for heading, after in URS_HEADINGS:
        if heading not in bp.headings:
            at = bp.headings.index(after) + 1 if after in bp.headings else len(bp.headings)
            bp.headings.insert(at, heading)
    have = {b.id for b in bp.blocks}
    bp.blocks += [BoilerplateBlock(id=i, heading=h, title=t, body=body, default_on=False, order=o)
                  for h, i, t, body, o in URS_BLOCKS if i not in have]
    bp.migrations.append(STAGE3)
    return True


# Default category per section (a line's category overrides it): ce-requirements 6, needed for M19
SECTION_CATEGORY = {4000: "engineering", 4100: "support", 4200: "travel", 4300: "hardware"}


def apply_stage2(catalog: Catalog) -> bool:
    """Hardware section and its pass-through line item, once."""
    if STAGE2 in catalog.migrations:
        return False
    have_sec = catalog.reserved_section_numbers()
    catalog.sections += [s.model_copy() for s in STAGE2_SECTIONS if s.number not in have_sec]
    catalog.sections.sort(key=lambda s: s.number)
    have = catalog.reserved_codes()
    catalog.items += [i.model_copy(deep=True) for i in STAGE2_ITEMS if i.code not in have]
    catalog.items.sort(key=lambda i: i.code)
    catalog.migrations.append(STAGE2)
    return True


def upgrade_library(bp) -> bool:
    """Convenient Enterprises terms library: Detailed-depth blocks and the Assumptions heading, once."""
    from .models import BoilerplateBlock
    if STAGE2 in bp.migrations:
        return False
    if "Assumptions" not in bp.headings:
        at = bp.headings.index("Time Table") if "Time Table" in bp.headings else len(bp.headings)
        bp.headings.insert(at, "Assumptions")
    have = {b.id for b in bp.blocks}
    bp.blocks += [BoilerplateBlock(id=i, heading=h, title=t, body=body, default_on=False, order=o)
                  for h, i, t, body, o in DETAILED_BLOCKS if i not in have]
    bp.migrations.append(STAGE2)
    return True


def upgrade_settings(s) -> bool:
    """Convenient Enterprises settings: task templates, travel destinations, milestone and schedule starting
    points, once (left alone if the user has already filled them)."""
    from .ce_models import (
        default_destinations,
        default_milestones,
        default_phases,
        default_task_templates,
    )
    if STAGE2 in s.migrations:
        return False
    s.task_templates = s.task_templates or default_task_templates()
    s.destinations = s.destinations or default_destinations()
    s.milestone_template = s.milestone_template or default_milestones()
    s.phase_template = s.phase_template or default_phases()
    s.migrations.append(STAGE2)
    return True
