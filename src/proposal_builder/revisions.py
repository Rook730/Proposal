"""Revision lifecycle and revision-to-revision differences (spec section 6).

- 1.0, 1.1, 1.2 ... are issued while the client is deciding. Issuing locks the file.
- Finalize creates 2.0 from the latest 1.x once the client has chosen: base only, chosen
  alternates merged. 2.0 (or 2.1 ... if it needs another pass) is issued for signature.
- Mark accepted records the signature on the latest issued 2.x. After that, scope changes
  go through change orders; no further revisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from .calc import calculate
from .models import Settings, StockClass
from .proposal import (
    Project,
    ProjectStatus,
    Revision,
    RevisionState,
    contract_revision,
    new_revision_from,
    next_revision_number,
    rev_major,
)
from .store import ProjectStore


class RevisionError(ValueError):
    pass


def latest(ps: ProjectStore, number: str) -> Revision:
    return ps.load_revision(number)


def issue(ps: ProjectStore, project: Project, rev: Revision) -> Revision:
    """Lock a draft. Earlier issued revisions become Superseded; the project status follows."""
    if rev.locked:
        raise RevisionError(f"Rev {rev.rev} is already {rev.state.value.lower()}")
    rev.state = RevisionState.ISSUED
    rev.issued_at = datetime.now().replace(microsecond=0)
    ps.save_revision(project.number, rev, allow_locked=True)
    for r in ps.list_revisions(project.number):
        if r == rev.rev:
            continue
        old = ps.load_revision(project.number, r)
        if old.state in (RevisionState.ISSUED, RevisionState.ACCEPTED):
            old.state = RevisionState.SUPERSEDED
            ps.save_revision(project.number, old, allow_locked=True)
    project.status = ProjectStatus.PRESENTED
    ps.save_project(project)
    return rev


def mark_accepted(ps: ProjectStore, project: Project, rev: Revision) -> Revision:
    """The client signed the issued final revision."""
    if not rev.is_contract:
        raise RevisionError("Finalize the client's selections (Rev 2.0) before marking the proposal accepted")
    if rev.state is not RevisionState.ISSUED:
        raise RevisionError(f"Issue Rev {rev.rev} before marking it accepted")
    if rev.rev != ps.list_revisions(project.number)[-1]:
        raise RevisionError("Only the latest revision can be accepted")
    rev.state = RevisionState.ACCEPTED
    ps.save_revision(project.number, rev, allow_locked=True)
    project.status = ProjectStatus.ACCEPTED
    ps.save_project(project)
    return rev


def create_revision(ps: ProjectStore, project: Project) -> Revision:
    """New editable revision copied from the latest one (which must be issued)."""
    src = latest(ps, project.number)
    if src.state is RevisionState.ACCEPTED:
        raise RevisionError("The proposal is accepted; changes now go through change orders")
    if not src.locked:
        raise RevisionError(f"Rev {src.rev} is still a draft; issue it or keep editing it")
    rev = new_revision_from(src, next_revision_number(ps.list_revisions(project.number)))
    ps.save_revision(project.number, rev)
    return rev


def finalize(ps: ProjectStore, project: Project, selected_alternates: list[int]) -> Revision:
    """Create the final revision 2.0 (base only, chosen alternates merged) from the latest issued 1.x."""
    src = latest(ps, project.number)
    if rev_major(src.rev) >= 2:
        raise RevisionError("This project already has a final (2.x) revision")
    if not src.locked:
        raise RevisionError(f"Issue Rev {src.rev} before finalizing it")
    try:
        rev = contract_revision(src, selected_alternates)
    except ValueError as e:
        raise RevisionError(str(e)) from e
    ps.save_revision(project.number, rev)
    return rev


def previous_issued(ps: ProjectStore, number: str, rev: Revision) -> Revision | None:
    """The revision this one should be compared against: its source, else the one before it."""
    revs = ps.list_revisions(number)
    target = rev.based_on if rev.based_on in revs else None
    if target is None:
        earlier = [r for r in revs if tuple(map(int, r.split("."))) < tuple(map(int, rev.rev.split(".")))]
        target = earlier[-1] if earlier else None
    return ps.load_revision(number, target) if target else None


# ---------------------------------------------------------------- differences


@dataclass
class LineChange:
    kind: str                     # added | removed | changed
    line_id: str
    title: str
    details: list[str] = field(default_factory=list)
    old_cost: Decimal | None = None
    new_cost: Decimal | None = None


@dataclass
class RevisionDiff:
    old_rev: str
    new_rev: str
    changes: list[LineChange]
    old_subtotal: Decimal
    new_subtotal: Decimal
    old_total: Decimal
    new_total: Decimal
    notes: list[str] = field(default_factory=list)   # section / alternate / boilerplate level

    @property
    def total_change(self) -> Decimal:
        return self.new_total - self.old_total

    @property
    def empty(self) -> bool:
        return not self.changes and not self.notes and self.total_change == 0


def _m(v: Decimal | None) -> str:
    return "" if v is None else f"${v:,.2f}"


def _q(v: Decimal) -> str:
    return f"{v.normalize():f}"


def revision_diff(old: Revision, new: Revision, settings: Settings, stock: list[StockClass],
                  project: Project | None = None, section_names: dict[int, str] | None = None) -> RevisionDiff:
    ro = calculate(old, settings, stock, project)
    rn = calculate(new, settings, stock, project)
    names = section_names or {}
    changes: list[LineChange] = []

    def cost(res, ln):
        if ln.is_percent:
            return res.base.percent_items.get(ln.id)
        return res.lines[ln.id].cost

    old_ids = {ln.id: ln for ln in old.lines if ln.section in old.sections}
    new_ids = {ln.id: ln for ln in new.lines if ln.section in new.sections}

    for lid, ln in new_ids.items():
        if lid not in old_ids:
            changes.append(LineChange("added", lid, ln.title, [f"{_q(rn.lines[lid].qty)} {ln.unit}"],
                                      None, cost(rn, ln) if ln.alternate is None else None))
    for lid, ln in old_ids.items():
        if lid not in new_ids:
            changes.append(LineChange("removed", lid, ln.title, [], cost(ro, ln) if ln.alternate is None else None,
                                      None))
    for lid in sorted(set(old_ids) & set(new_ids)):
        a, b = old_ids[lid], new_ids[lid]
        la, lb = ro.lines[lid], rn.lines[lid]
        det = []
        if a.title != b.title:
            det.append(f"title: {a.title} to {b.title}")
        if a.section != b.section:
            det.append(f"moved to {names.get(b.section, b.section)}")
        if la.qty != lb.qty or a.unit != b.unit:
            det.append(f"qty {_q(la.qty)} {a.unit} to {_q(lb.qty)} {b.unit}")
        if la.unit_price != lb.unit_price:
            if a.is_percent:
                det.append(f"rate {la.unit_price * 100:.2f}% to {lb.unit_price * 100:.2f}%")
            else:
                det.append(f"unit price {_m(la.unit_price)} to {_m(lb.unit_price)}")
        if a.notes != b.notes or (a.print_general != b.print_general) or a.general_description != b.general_description:
            det.append("description updated")
        if a.performer != b.performer:
            det.append(f"performer {a.performer.value or 'none'} to {b.performer.value or 'none'}")
        if a.alternate != b.alternate:
            det.append("now part of the base" if b.alternate is None else f"moved to Alternate {b.alternate}")
        if det:
            changes.append(LineChange("changed", lid, b.title, det,
                                      cost(ro, a) if a.alternate is None else None,
                                      cost(rn, b) if b.alternate is None else None))

    notes = []
    for s in new.sections:
        if s not in old.sections:
            notes.append(f"Section added: {names.get(s, s)}")
    for s in old.sections:
        if s not in new.sections:
            notes.append(f"Section removed: {names.get(s, s)}")
    if new.selected_alternates and not old.selected_alternates:
        notes.append("Accepted with " + ", ".join(f"Alternate {n}" for n in new.selected_alternates)
                     + "; alternate lines are now part of the base")
    elif new.is_contract and not old.is_contract and old.alternates:
        notes.append("Accepted as the base proposal; alternates were not selected")
    old_alts = {a.number for a in old.alternates}
    new_alts = {a.number for a in new.alternates}
    for n in sorted(new_alts - old_alts):
        notes.append(f"Alternate {n} added")
    for n in sorted(old_alts - new_alts):
        if not new.is_contract:
            notes.append(f"Alternate {n} removed")
    ob = {b.id: b for b in old.blocks if b.on}
    nb = {b.id: b for b in new.blocks if b.on}
    for bid in nb.keys() - ob.keys():
        notes.append(f"Terms added: {nb[bid].title or bid}")
    for bid in ob.keys() - nb.keys():
        notes.append(f"Terms removed: {ob[bid].title or bid}")
    for bid in ob.keys() & nb.keys():
        if ob[bid].body != nb[bid].body or ob[bid].title != nb[bid].title:
            notes.append(f"Terms updated: {nb[bid].title or bid}")

    order = {"changed": 0, "added": 1, "removed": 2}
    changes.sort(key=lambda c: (tuple(int(x) for x in c.line_id.split(".")), order[c.kind]))
    return RevisionDiff(old.rev, new.rev, changes, ro.base.subtotal, rn.base.subtotal,
                        ro.base.total, rn.base.total, notes)
