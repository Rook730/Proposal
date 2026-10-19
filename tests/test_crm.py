from datetime import date

from proposal_builder.crm import (
    Contractor,
    ContractorBook,
    CustomerBook,
    add_from_sub_names,
    insurance_warnings,
    line_contractor,
    link_projects,
)
from proposal_builder.proposal import Line, Project


def test_link_projects_by_name_and_address():
    book = CustomerBook()
    a = Project(number="26001", client_name="Kim  and Pam Hotch", site_address="20 Trafalgar Cir.")
    b = Project(number="26005", client_name="kim and pam hotch", site_address="12 Elm St")
    c = Project(number="26006", client_name="", site_address="x")
    changed = link_projects(book, [a, b, c])
    assert changed == [a, b] and len(book.customers) == 1
    cust = book.customers[0]
    assert a.customer_id == b.customer_id == cust.id and c.customer_id is None
    assert [x.address for x in cust.addresses] == ["20 Trafalgar Cir.", "12 Elm St"]
    assert cust.address(b.site_address_id).address == "12 Elm St"
    assert cust.mailing_address_id == a.site_address_id
    assert link_projects(book, [a, b]) == []                     # already linked


def test_contractors_from_sub_names_and_insurance():
    book = ContractorBook()
    assert add_from_sub_names(book, ["Sparky Electric", "", "sparky electric "])
    assert len(book.contractors) == 1
    ln = Line(id="6.01", section=600, title="Elec", sub_name="Sparky Electric")
    assert line_contractor(book, ln).company == "Sparky Electric"
    c = book.contractors[0]
    today = date(2026, 10, 1)
    assert c.insurance_status(today) == "unknown"
    c.insurance_expiry = date(2026, 10, 20)
    assert c.insurance_status(today) == "expiring"
    c.insurance_expiry = date(2026, 9, 1)
    assert insurance_warnings(book, {c.id}, today) == ["Sparky Electric: insurance expired 2026.09.01"]
    book.contractors.append(Contractor(company="Good Co", insurance_expiry=date(2027, 1, 1)))
    assert insurance_warnings(book, {book.contractors[1].id}, today) == []
