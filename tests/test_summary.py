import json
from datetime import date
from decimal import Decimal
from importlib import resources
from pathlib import Path

from proposal_builder.models import Catalog, Settings
from proposal_builder.proposal import Project, ProjectStatus, Revision, RevisionState
from proposal_builder.store import DataStore, ProjectStore
from proposal_builder.summary import all_project_income, in_window, pipeline, to_csv

FIXTURE = Path(__file__).parent / "fixtures" / "26005_anon.json"


def seed(name):
    return (resources.files("proposal_builder") / "seed" / name).read_text(encoding="utf-8")


def test_summary_window_and_pipeline(tmp_path):
    ds = DataStore(tmp_path)
    ds.initialize_from_seed()
    ps = ProjectStore(ds)
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    settings, catalog = Settings.model_validate_json(seed("settings.json")), Catalog.model_validate_json(seed("catalog.json"))

    won = Project.model_validate(data["project"])
    rev = Revision.model_validate(data["revision"])
    rev.rev, rev.state, rev.selected_alternates = "2.0", RevisionState.ACCEPTED, []
    won.set_status(ProjectStatus.ACCEPTED, on=date(2026, 3, 1))
    ps.create(won, rev)

    lost = won.model_copy(update={"number": "26006", "accepted_on": None, "project_name": "Bath"})
    lost.set_status(ProjectStatus.REJECTED)
    r2 = Revision.model_validate(data["revision"])
    r2.proposal_date = date(2026, 4, 1)
    ps.create(lost, r2)

    rows = all_project_income(ps, settings, catalog)
    assert {r.project.number: r.basis for r in rows} == {"26005": "accepted", "26006": "proposal date"}
    assert [r.project.number for r in in_window(rows, date(2026, 1, 1), date(2026, 3, 31))] == ["26005"]
    pl = pipeline(rows)
    assert (pl.proposals, pl.won, pl.lost) == (2, 1, 1) and pl.win_rate == Decimal("0.5")
    w = next(r for r in rows if r.won)
    assert w.amount("actual") is not None and w.amount("estimate") == w.amount("estimate", "KS") + w.amount("estimate", "CW")
    assert "26005" in to_csv(rows, "actual")
    assert won.closed_on is None
    won.set_status(ProjectStatus.CLOSED, on=date(2026, 6, 1))
    assert won.closed_on == date(2026, 6, 1) and won.accepted_on == date(2026, 3, 1)
