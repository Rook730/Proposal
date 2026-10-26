"""Line and section order (1.9.3): Move up / Move down, and adding a section keeps the user's order."""

from decimal import Decimal as D

from proposal_builder.proposal import Line, Revision


def line(rev: Revision, section: int, title: str) -> Line:
    ln = Line(id=rev.new_line_id(section), section=section, title=title, qty=D(1))
    return rev.add_line(ln)


def ids(rev: Revision) -> list[str]:
    return [ln.id for sec in rev.sections for ln in rev.section_lines(sec)]


def test_move_within_section_and_equal_orders():
    rev = Revision()
    a, b, c = (line(rev, 2100, t) for t in "abc")
    for ln in (a, b, c):
        ln.order = 10                       # imported data can carry equal orders
    assert rev.move_line(c.id, -1)
    assert [ln.title for ln in rev.section_lines(2100)] == ["a", "c", "b"]
    assert rev.move_line(a.id, 1)
    assert [ln.title for ln in rev.section_lines(2100)] == ["c", "a", "b"]
    assert not rev.move_line(c.id, -1)      # already first: reported, not silently ignored


def test_single_line_sections_move_as_a_whole_past_empty_ones():
    rev = Revision()
    box = rev.add_piece("Box")
    rev.add_piece("Empty piece")
    table = rev.add_piece("Table")
    line(rev, box.number, "box")
    line(rev, table.number, "table")
    line(rev, 3000, "delivery")
    assert ids(rev) == ["90.01", "92.01", "30.01"]
    assert rev.move_section(table.number, -1)                   # skips the empty piece
    assert ids(rev) == ["92.01", "90.01", "30.01"]
    assert rev.move_section(3000, -1)
    assert ids(rev) == ["92.01", "30.01", "90.01"]
    assert not rev.move_section(table.number, -1)


def test_adding_a_section_keeps_manual_order():
    rev = Revision()
    line(rev, 3000, "delivery")
    line(rev, 2100, "shop")
    assert rev.sections == [2100, 3000]
    rev.move_section(3000, -1)
    assert rev.sections == [3000, 2100]
    line(rev, 2500, "finish")                                   # used to re-sort everything
    assert rev.sections == [2500, 3000, 2100]                   # 3000 stays ahead of 2100
    p = rev.add_piece("Box")                                    # pieces go before catalog sections
    assert rev.sections == [p.number, 2500, 3000, 2100]
