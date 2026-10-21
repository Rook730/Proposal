from decimal import Decimal

from proposal_builder import preflight
from proposal_builder.calc import calculate
from proposal_builder.crm import Contact, Customer, CustomerBook
from proposal_builder.models import Settings
from proposal_builder.proposal import Line, Project, Revision, Variable


def _rev(*lines):
    rev = Revision(sections=[100])
    for ln in lines:
        rev.add_line(ln)
    rev.sections = [100]
    return rev


def L(id, title="Item", price="10", **kw):
    return Line(id=id, section=kw.pop("section", 100), title=title,
                unit_price=None if price is None else Decimal(price), **kw)


def test_zero_lines():
    rev = _rev(L("1.01", "Free", "0"), L("1.02", "Excluded", "0", not_included=True),
               L("1.03", "Owner", "0", owner_furnished=True), L("1.04", "Paid"), L("1.05", "No qty", "0", qty=0),
               L("2.01", "Unchecked", "0", section=200))
    res = calculate(rev, Settings(), [], Project(number="1"))
    assert [m for _, m in preflight.zero_lines(rev, res)] == [
        "1.01 Free: prices at $0 but is not marked Not included (the terms say a $0 line is not included); "
        "enter a price or mark it Not included"]


def test_placeholders():
    rev = _rev(L("1.01", "Cabinets TBD", notes="Size ?? and $XXX; [ ] confirm. Sixty boxes, tbd."),
               L("1.02", "Exxon tie-in", notes="Max 2XL, Texas"))
    rev.variables.append(Variable(name="start", value="TBA"))
    msgs = [m for _, m in preflight.placeholders(Project(number="1"), rev)]
    assert msgs == ["1.01 title: placeholder TBD left in the text",
                    "1.01 notes: placeholder ??, XXX, [ ], tbd left in the text",
                    "Variable 'start': placeholder TBA in its value"]


def test_allowance_wording():
    rev = _rev(L("1.01", "Tile", is_allowance=True, notes="Allowance for tile at $5/SF."),
               L("1.02", "Allowance for fixtures"),
               L("1.03", "Lights", notes="Allowance: 6 cans"),
               L("1.04", "Hood", is_allowance=True, notes="Hood insert"),
               L("1.05", "PM", general_description="5% allowance for change order management"))
    msgs = preflight.allowance_wording(rev)
    assert [m.split(":")[0] for _, m in msgs] == ["1.01 Tile", "1.02 Allowance for fixtures", "1.03 Lights"]
    assert "flag also prints" in msgs[0][1] and "flag is off" in msgs[1][1]


def test_duplicate_lines():
    rev = _rev(L("1.01", "Appliances", notes="Range"), L("1.02", "Appliances", notes="Dishwasher"),
               L("1.03", "Trim", notes="Base"), L("1.04", "trim ", notes="Base "),
               L("1.05", "Trim", notes="Base", alternate=1))
    assert [m for _, m in preflight.duplicate_lines(rev)] == [
        "1.03, 1.04 Trim: same title and notes in one section; added twice?"]


def test_project_info():
    book = CustomerBook(customers=[Customer(id="c1", name="Pat", contacts=[Contact(name="Pat")]),
                                   Customer(id="c2", name="Lee", contacts=[Contact(name="Lee", phone="555")])])
    assert [m for _, m in preflight.project_info(Project(number="1"), book)] == [
        "Project info: client name is blank", "Project info: site address is blank",
        "Project info: not linked to a customer"]
    p = Project(number="1", client_name="Pat", site_address="1 Main", customer_id="c1")
    assert [m for _, m in preflight.project_info(p, book)] == ["Customer Pat: no contact with a phone or email"]
    p.customer_id = "c2"
    assert preflight.project_info(p, book) == []
