"""MGM Brakes Tandem Jig Phase 1 (Proposal_20260828 Rev 1.0) rebuilt as a Convenient Enterprises proposal.
Shared by tests/test_ce.py (acceptance test 1) and the self-test."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from proposal_builder.models import CE, Boilerplate, Catalog
from proposal_builder.proposal import Alternate, Project, Revision, default_blocks, line_from_item

MGM_TEXT = {
    "cover": "Thank you for the opportunity to quote engineering services for the Tandem Jig Assembly Machine safety "
             "upfit. This proposal covers Phase 1 only: the safety control system, associated pneumatic "
             "reconfiguration, and PLC integration required to bring the machine into compliance while restoring "
             "legacy cycle time and reducing air consumption. Additional machine upgrades discussed are outside this "
             "phase and can be quoted separately.",
    "machine": "The Tandem Jig is a custom assembly machine used to tandemize the assembly of air brake actuators. "
               "It uses pneumatic press motions and torque drivers and requires manual part placement mid-process. "
               "Existing controls are a finger-detection light curtain, two-hand safety controls, and a Unitronics "
               "V430 PLC. Legacy cycle time was approximately 37 seconds; the current configuration runs "
               "approximately 49 seconds.",
    "objective": "The primary goal is safety compliance. The design will convert the safe reaction from full air "
                 "dump to stop-and-hold, with the intent to restore the legacy cycle time, and reduce compressed air "
                 "consumption where possible, while meeting the required safety performance level.",
    "timetable": "The engagement begins upon proposal approval and receipt of deposit. Design work begins upon "
                 "receipt of Client's existing-parts BOM and the sketch of the existing pneumatics and PLC wiring.",
}


def mgm(catalog: Catalog, boilerplate: Boilerplate) -> tuple[Project, Revision]:
    project = Project(number="26007", profile=CE, client_name="MGM Brakes",
                      attention="Mark Chandler, Beverly Allen", site_address="229 Park Ave\nMurphy NC 28906",
                      project_name="Tandem Jig Assembly Machine Phase 1 Safety Controls Upfit")
    rev = Revision(blocks=default_blocks(boilerplate.blocks), proposal_date=date(2026, 8, 28))
    for b in rev.blocks:
        if b.id in MGM_TEXT:
            b.body = MGM_TEXT[b.id] if b.id != "timetable" else b.body.replace(
                "The engagement begins upon proposal approval and receipt of deposit. TBD: what design work waits on "
                "(Client inputs).", MGM_TEXT["timetable"])
        if b.id == "engineering":
            b.body = b.body.replace("- TBD: scope item", "- Reconfigure the safety relay circuit to separate "
                                    "light-curtain, two-hand, access-door and e-stop functions.")

    def add(code, qty, alt=None, notes=""):
        it = catalog.item(code)
        ln = line_from_item(it, catalog, rev.new_line_id(it.section))
        ln.qty, ln.alternate, ln.notes = Decimal(qty), alt, notes
        rev.add_line(ln)
        return ln

    add(4010, 80, notes="Deliverables 1 through 8.")
    add(4110, 16, notes="Up to two (2) onsite days in Murphy, NC.")
    add(4120, 4)
    add(4210, "2.5", notes="Fletcher to Murphy, NC.")
    add(4220, 1)
    rev.alternates.append(Alternate(number=1, name="ISO 13849-1 verification (SISTEMA)",
                                    description="Baseline is for Client to perform the risk assessment and determine "
                                                "the required Performance Level."))
    add(4050, 8, alt=1)
    return project, rev
