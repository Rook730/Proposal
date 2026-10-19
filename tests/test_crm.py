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


def test_rfq_and_comparison_documents_compile():
    import json
    from decimal import Decimal
    from importlib import resources
    from pathlib import Path

    from proposal_builder.models import Catalog, Settings
    from proposal_builder.proposal import Revision
    from proposal_builder.quotes import Quote, QuoteLog, comparison_document, contractor_lines, rfq_document
    from proposal_builder.render.document import compile_document

    seed = lambda n: (resources.files("proposal_builder") / "seed" / n).read_text(encoding="utf-8")  # noqa: E731
    st, cat = Settings.model_validate_json(seed("settings.json")), Catalog.model_validate_json(seed("catalog.json"))
    data = json.loads((Path(__file__).parent / "fixtures" / "26005_anon.json").read_text(encoding="utf-8"))
    project, rev = Project.model_validate(data["project"]), Revision.model_validate(data["revision"])
    book = ContractorBook(contractors=[Contractor(company="Brush Pros"), Contractor(company="Color Co")])
    a, b = book.contractors
    for ln in rev.lines:
        if ln.code == 1110:
            ln.contractor_id = a.id
    lines = contractor_lines(rev, book, a.id)
    assert lines and all(ln.code == 1110 for ln in lines)
    doc = rfq_document(project, rev, a, lines, st, cat.stock_classes)
    assert "price" not in json.dumps(doc["lines"]).lower() and project.client_name not in json.dumps(doc)
    assert compile_document(doc, None, template="rfq.typ")[:4] == b"%PDF"
    log = QuoteLog(quotes=[Quote(scope="Painting", contractor_id=a.id, amount=Decimal(9800)),
                           Quote(scope="painting ", contractor_id=b.id, amount=Decimal(8900))])
    assert log.scopes() == ["Painting"] and len(log.for_scope("Painting")) == 2
    cmp = comparison_document(project, rev, "Painting", log.for_scope("Painting"), book, st)
    assert [r["company"] for r in cmp["rows"]] == ["Color Co", "Brush Pros"]       # lowest first
    assert compile_document(cmp, None, template="comparison.typ")[:4] == b"%PDF"
