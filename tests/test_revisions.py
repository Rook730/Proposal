import json
from decimal import Decimal
from importlib import resources
from pathlib import Path

import pytest

from proposal_builder.calc import calculate
from proposal_builder.models import Catalog, Settings
from proposal_builder.proposal import (
    Line,
    Project,
    ProjectStatus,
    Revision,
    RevisionState,
    contract_revision,
    next_revision_number,
)
from proposal_builder.revisions import RevisionError, create_revision, finalize, issue, mark_accepted, revision_diff
from proposal_builder.store import DataStore, ProjectStore

FIXTURE = Path(__file__).parent / "fixtures" / "26005_anon.json"
D = Decimal


def seed(name):
    return (resources.files("proposal_builder") / "seed" / name).read_text(encoding="utf-8")


@pytest.fixture
def env(tmp_path):
    ds = DataStore(tmp_path)
    ds.initialize_from_seed()
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    project, rev = Project.model_validate(data["project"]), Revision.model_validate(data["revision"])
    ps = ProjectStore(ds)
    ps.create(project, rev)
    return ps, project, ds.load_settings(), ds.load_catalog()


def test_numbering():
    assert next_revision_number([]) == "1.0"
    assert next_revision_number(["1.0"]) == "1.1"
    assert next_revision_number(["1.0", "1.1", "1.10", "1.9"]) == "1.11"
    assert next_revision_number(["1.0", "2.0"]) == "2.1"


def test_issue_locks_and_new_revision(env):
    ps, project, settings, catalog = env
    rev = ps.load_revision(project.number)
    issue(ps, project, rev)
    assert ps.load_revision(project.number, "1.0").state is RevisionState.ISSUED
    assert ps.load_project(project.number).status is ProjectStatus.PRESENTED
    rev.lines[0].qty = D(9)
    with pytest.raises(PermissionError):
        ps.save_revision(project.number, rev)                       # write-once
    with pytest.raises(RevisionError):
        issue(ps, project, rev)

    r11 = create_revision(ps, project)
    assert (r11.rev, r11.state, r11.based_on) == ("1.1", RevisionState.DRAFT, "1.0")
    with pytest.raises(RevisionError):
        create_revision(ps, project)                                # 1.1 still a draft
    r11.lines[0].qty = D(2)
    ps.save_revision(project.number, r11)
    issue(ps, project, r11)
    assert ps.load_revision(project.number, "1.0").state is RevisionState.SUPERSEDED
    assert ps.list_revisions(project.number) == ["1.0", "1.1"]


def test_finalize_with_alternate_and_accept(env):
    ps, project, settings, catalog = env
    with pytest.raises(RevisionError):
        finalize(ps, project, [1])                                  # 1.0 not issued yet
    issue(ps, project, ps.load_revision(project.number))
    with pytest.raises(RevisionError):
        mark_accepted(ps, project, ps.load_revision(project.number))  # 1.x cannot be accepted
    r20 = finalize(ps, project, [1])
    assert r20.rev == "2.0" and r20.alternates == [] and r20.selected_alternates == [1]
    assert r20.line("11.01") is None and r20.line("11.02").alternate is None
    res = calculate(r20, settings, catalog.stock_classes)
    assert res.base.total == D("38199.69")                          # the alternate total becomes the contract
    with pytest.raises(RevisionError):
        mark_accepted(ps, project, r20)                             # not issued yet
    issue(ps, project, r20)
    assert ps.load_revision(project.number, "2.0").state is RevisionState.ISSUED
    with pytest.raises(RevisionError):
        finalize(ps, project, [])
    r21 = create_revision(ps, project)                              # one more pass before signature
    assert r21.rev == "2.1"
    issue(ps, project, r21)
    mark_accepted(ps, project, r21)
    assert ps.load_revision(project.number, "2.1").state is RevisionState.ACCEPTED
    assert ps.load_project(project.number).status is ProjectStatus.ACCEPTED
    with pytest.raises(RevisionError):
        create_revision(ps, project)                                # change orders from here


def test_accept_base_only(env):
    ps, project, settings, catalog = env
    issue(ps, project, ps.load_revision(project.number))
    r20 = finalize(ps, project, [])
    assert r20.line("11.01") is not None and r20.line("11.02") is None
    assert calculate(r20, settings, catalog.stock_classes).base.total == D("41186.59")


def test_contract_rejects_conflicting_alternates():
    from proposal_builder.proposal import Alternate
    rev = Revision(sections=[100], alternates=[Alternate(number=1, removes=["1.01"]),
                                               Alternate(number=2, removes=["1.01"])])
    rev.add_line(Line(id="1.01", section=100, title="a", unit_price=D(1)))
    with pytest.raises(ValueError):
        contract_revision(rev, [1, 2])


def test_diff(env):
    ps, project, settings, catalog = env
    old = ps.load_revision(project.number)
    new = old.model_copy(deep=True)
    new.rev = "1.1"
    new.line("2.01").qty = D(14)                                      # 12 -> 14 HR @ 75
    new.remove_line("3.02")                                           # 150
    new.add_line(Line(id=new.new_line_id(300), section=300, title="Extra", unit_price=D(100)))
    new.blocks[0].body += " Edited."
    d = revision_diff(old, new, settings, catalog.stock_classes)
    kinds = {(c.kind, c.line_id) for c in d.changes}
    assert ("changed", "2.01") in kinds and ("removed", "3.02") in kinds and ("added", "3.04") in kinds
    ch = next(c for c in d.changes if c.line_id == "2.01")
    assert ch.details == ["qty 12 HR to 14 HR"] and (ch.old_cost, ch.new_cost) == (D("900.00"), D("1050.00"))
    assert d.new_subtotal - d.old_subtotal == D(100)                  # +150 -150 +100
    assert d.total_change == (d.new_subtotal - d.old_subtotal) * D("1.255")
    assert any(n.startswith("Terms updated") for n in d.notes)
    assert revision_diff(old, old, settings, catalog.stock_classes).empty
