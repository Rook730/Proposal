"""Convenient Enterprises data saved in revisions and settings (CE stage 2: Detailed depth).

Kept apart from proposal.py so models.py and proposal.py can both use them. All are SavedModels: files written by
a newer version keep their extra fields.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import Field

from .base import SavedModel

D = Decimal
LETTER, DETAILED = "letter", "detailed"
DEPTHS = {LETTER: "Letter", DETAILED: "Detailed"}
CLIENT, CONSULTANT = "client", "consultant"
BUYERS = {CLIENT: "Client", CONSULTANT: "Consultant (cost + sourcing fee)"}


def new_id() -> str:
    return uuid.uuid4().hex[:10]


class TaskHours(SavedModel):
    """One task in a line's hours buildup (internal, never printed). The line's quantity is their sum."""
    name: str
    hours: Decimal = D(0)
    note: str = ""


class TaskTemplate(SavedModel):
    """Settings > Proposals (Convenient Enterprises): a task with its usual hours, offered in hours buildups."""
    name: str
    hours: Decimal = D(0)
    deliverable: str = ""          # wording for the Deliverables list, if the task produces one


class BomItem(SavedModel):
    """Bill of materials row. Client-bought items print for reference; Consultant-bought items are billed at
    invoiced cost plus the sourcing fee through one hardware line (ce.sync_hardware_line)."""
    id: str = Field(default_factory=new_id)
    manufacturer: str = ""
    model: str = ""
    part_number: str = ""
    description: str = ""
    qty: Decimal = D(1)
    unit: str = "EA"
    unit_cost: Decimal | None = None
    supplier: str = ""
    lead_time: str = ""
    buyer: str = CLIENT
    price_ref: str | None = None   # catalog.prices.hardware id it was picked from
    notes: str = ""

    @property
    def extended(self) -> Decimal | None:
        return None if self.unit_cost is None else (self.qty * self.unit_cost).quantize(D("0.01"))


class Milestone(SavedModel):
    """A fixed-fee invoice point. pct is a fraction of the fixed fee; the deposit is the first row and comes
    from Settings (deposit %), so the deposit plus every milestone should make 100%."""
    name: str
    trigger: str = ""              # when it is invoiced, e.g. "Design approval (Deliverables 1 to 5)"
    pct: Decimal = D(0)


class Phase(SavedModel):
    """A schedule phase in weeks after approval (printed as a bar chart)."""
    name: str
    start_week: Decimal = D(0)
    weeks: Decimal = D(1)
    gate: str = ""                 # what it waits on, e.g. "Client risk assessment received"


class TravelDestination(SavedModel):
    """Settings > Proposals (Convenient Enterprises): a site the Consultant travels to."""
    name: str
    one_way_hours: Decimal = D(0)
    round_trip_miles: Decimal = D(0)     # beyond the free zone; 0 = none charged or not entered yet
    overnight: bool = False


def default_milestones() -> list[Milestone]:
    return [Milestone(name="Design approval", trigger="Design review approved by the Client", pct=D("0.40")),
            Milestone(name="Documentation and program delivery", trigger="Schematics, BOM and program delivered",
                      pct=D("0.30")),
            Milestone(name="Run-off", trigger="Onsite validation and machine run-off", pct=D("0.20"))]


def default_phases() -> list[Phase]:
    return [Phase(name="Design", start_week=D(0), weeks=D(3), gate="Deposit and Client inputs received"),
            Phase(name="Documentation and programming", start_week=D(2), weeks=D(3)),
            Phase(name="Onsite validation and run-off", start_week=D(5), weeks=D(1),
                  gate="Client hardware installed")]


def default_task_templates() -> list[TaskTemplate]:
    t = TaskTemplate
    return [t(name="Safety control system design", hours=D(24),
              deliverable="Safety control system design, with safety relay and valve specification."),
            t(name="Pneumatic schematic", hours=D(8),
              deliverable="Pneumatic schematic documenting the final valve configuration and air circuits."),
            t(name="Safety wiring schematic", hours=D(8),
              deliverable="Wiring schematic documenting the final safety control system configuration."),
            t(name="PLC wiring schematic", hours=D(6),
              deliverable="Wiring schematic documenting the final PLC configuration."),
            t(name="Bill of materials", hours=D(4), deliverable="Bill of materials for the upfit."),
            t(name="PLC programming", hours=D(20), deliverable="PLC programming to integrate the changes."),
            t(name="HMI development", hours=D(16), deliverable="HMI screens for the new functions."),
            t(name="Robot programming", hours=D(24), deliverable="Robot programs for the new functions."),
            t(name="Vision setup", hours=D(12), deliverable="Vision tools and inspection setup."),
            t(name="Program delivery", hours=D(2), deliverable="Digital and printed copy of the final program."),
            t(name="Advisory review", hours=D(4),
              deliverable="Advisory review of the Client's calculations and risk assessment."),
            t(name="Risk assessment template", hours=D(2)),
            t(name="Commissioning", hours=D(16)),
            t(name="Training", hours=D(4), deliverable="Operator and maintenance training."),
            t(name="Documentation package", hours=D(8), deliverable="Manuals and as-built documentation."),
            t(name="Project management", hours=D(4))]


def default_destinations() -> list[TravelDestination]:
    # 224 Rutledge Rd to Murphy: about 116 road miles; the one-hour zone ends near mile 61 (US 74 past
    # Sylva), so about 55 miles each way, 110 round trip, are beyond it
    return [TravelDestination(name="Murphy, NC", one_way_hours=D("2.5"), round_trip_miles=D(110), overnight=True)]
