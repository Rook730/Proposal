from datetime import date

import pytest

from proposal_builder.migrations import OLD_ZERO_2
from proposal_builder.proposal import ProposalBlock, default_blocks
from proposal_builder.models import BoilerplateBlock


def test_library_status():
    lib = BoilerplateBlock(id="b", heading="H", title="T", body="Library text")
    b = default_blocks([lib])[0]
    assert b.library_status("T", "Library text") == ""
    b.body = "Mine"
    assert b.library_status("T", "Library text") == "edited"
    assert b.library_status("T", "New library text") == "both"
    b.copy_library("T", "Library text")
    assert b.library_status("T", "New library text") == "library"
    assert b.library_status(None, None) == "custom"


def test_library_status_for_proposals_copied_before_tracking():
    old = ProposalBlock(id="zero-lines", heading="H", title="$0 and owner-supplied lines", body=OLD_ZERO_2)
    assert old.library_status("New title", "New body") == "library"
    mine = ProposalBlock(id="zero-lines", heading="H", title="t", body="Edited by hand")
    assert mine.library_status("New title", "New body") == "edited"


def test_dates():
    from proposal_builder.ui.widgets import fmt_date, parse_date
    assert fmt_date(date(2026, 10, 20)) == "2026.10.20"
    for s in ("2026.10.20", "2026-10-20", "10/20/2026", "10/20/26"):
        assert parse_date(s) == date(2026, 10, 20)
    assert parse_date("10/20") == date(date.today().year, 10, 20)
    assert parse_date("") is None
    with pytest.raises(ValueError):
        parse_date("soon")


def test_save_hook(tmp_path):
    from proposal_builder import store
    seen = []
    store.SAVE_HOOKS.append(seen.append)
    try:
        store._atomic_write(tmp_path / "x.json", "{}")
    finally:
        store.SAVE_HOOKS.remove(seen.append)
    assert seen == [tmp_path / "x.json"]


def test_alternates_kept_separate():
    from decimal import Decimal
    from proposal_builder.calc import calculate
    from proposal_builder.models import Settings
    from proposal_builder.proposal import Alternate, Line, Revision, contract_revision
    rev = Revision(sections=[100])
    rev.add_line(Line(id="1.01", section=100, title="Base", unit_price=Decimal(100)))
    rev.add_line(Line(id="1.02", section=100, title="Paint lowers", unit_price=Decimal(10), alternate=1))
    rev.add_line(Line(id="1.03", section=100, title="Paint all", unit_price=Decimal(20), alternate=2))
    rev.alternates += [Alternate(number=1, name="Lowers"), Alternate(number=2, name="All")]
    assert [c.name for c in calculate(rev, Settings(), []).combinations] == ["Alt 1 + Alt 2"]
    rev.set_separate(2, 1, True)
    assert rev.kept_separate(1, 2) and not rev.can_combine(1, 2)
    assert calculate(rev, Settings(), []).combinations == []
    with pytest.raises(ValueError, match="offered separately"):
        contract_revision(rev, [1, 2])
    assert contract_revision(rev, [2]).separate_alternates == []
    rev.set_separate(1, 2, False)
    assert rev.separate_alternates == [] and len(calculate(rev, Settings(), []).combinations) == 1
