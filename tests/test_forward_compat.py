"""1.10.1 forward compatibility: a data folder written by a newer version (e.g. the CE branch) must stay
readable here, and nothing this version saves may drop or change what the newer version wrote."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

from proposal_builder.closeout import ChangeOrderLog
from proposal_builder.crm import CustomerBook
from proposal_builder.models import CW, KS, Catalog, Section, Settings
from proposal_builder.proposal import Line, Project, Revision
from proposal_builder.store import DataStore, ForeignProjectError, ProjectStore
from proposal_builder.summary import all_project_income
from proposal_builder.ui.state import AppState

CE_SECTION = {"number": 4000, "name": "Controls engineering", "key": "CTL", "profile": "ce", "brand": "x"}
CE_ITEM = {"code": 4010, "section": 4000, "title": "PLC programming", "price_source": "fee",
           "fee_kind": "fixed", "hours": "80"}


def _read(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _write(p: Path, data: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _digest(root: Path) -> dict[str, str]:
    return {f.relative_to(root).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(root.rglob("*")) if f.is_file()}


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    """A data folder as a newer version would leave it: new fields everywhere, a CE section with an item
    using a price basis this version does not know, a CE profile folder and a CE project."""
    root = tmp_path / "data"
    st = AppState(DataStore(root))
    ps = st.projects
    p = Project(number="26010", project_name="Kitchen", client_name="Smith", profile=KS)
    rev = Revision()
    rev.add_line(Line(id="1.01", section=100, title="Demo", qty=Decimal(2), unit_price=Decimal(50)))
    ps.create(p, rev)

    s = _read(root / "settings.json")
    s["brand"] = {"primary": "#000000", "heading_style": "band"}
    s["company"]["website"] = "keptspec.com"
    _write(root / "settings.json", s)

    c = _read(root / "catalog.json")
    c["sections"].append(CE_SECTION)
    c["items"].append(CE_ITEM)
    c["units"][0]["category"] = "time"
    c["task_templates"] = [{"key": "plc", "hours": 8}]
    _write(root / "catalog.json", c)

    _write(root / "customers.json", {"customers": [{"id": "c1", "name": "MGM Brakes", "is_company": True,
                                                    "industry": "automotive"}]})

    d = ps.project_dir("26010")
    pj = _read(d / "project.json")
    pj["job_code"] = "KS-26010"
    _write(d / "project.json", pj)
    rv = _read(d / "rev_1.0.json")
    rv["modules"] = {"m1": True}
    rv["lines"][0]["category"] = "engineering"
    _write(d / "rev_1.0.json", rv)

    _write(root / "profiles/ce/settings.json", {"company": {"dba": "Convenient Enterprises"}, "rate": "125"})
    ce = root / "projects/26011_MGM_Brakes_Tandem_Jig"
    _write(ce / "project.json", {"number": "26011", "profile": "ce", "client_name": "MGM Brakes",
                                 "project_name": "Tandem Jig", "status": "Awaiting PO", "customer_id": "c1"})
    _write(ce / "rev_1.0.json", {"rev": "1.0", "fees": [{"kind": "fixed", "amount": "10000"}]})
    return root


def test_code_stays_strict():
    with pytest.raises(TypeError):
        Section(number=100, name="General", key="GEN", bogus=1)
    s = Section(number=100, name="General", key="GEN")
    with pytest.raises(ValueError):
        s.bogus = 1


def test_unknown_fields_survive_load_edit_save(folder: Path):
    st = AppState(DataStore(folder))
    assert st.settings.unknown_fields["brand"]["primary"] == "#000000"
    st.settings.validity_days = 45
    st.save_settings()
    st.catalog.units[0].description = "Day"
    st.save_catalog()
    st.customers.customers[0].notes = "PO pending"
    st.save_customers()

    ps = st.projects
    p = ps.load_project("26010")
    p.status = p.status.__class__("Presented")
    ps.save_project(p)
    rev = ps.load_revision("26010")
    rev.lines[0].qty = Decimal(3)
    ps.save_revision("26010", rev)

    s = _read(folder / "settings.json")
    assert s["validity_days"] == 45 and s["brand"]["heading_style"] == "band"
    assert s["company"]["website"] == "keptspec.com"
    c = _read(folder / "catalog.json")
    assert c["units"][0] == {**c["units"][0], "category": "time", "description": "Day"}
    assert c["task_templates"] == [{"key": "plc", "hours": 8}]
    assert _read(folder / "customers.json")["customers"][0]["industry"] == "automotive"
    d = ps.project_dir("26010")
    assert _read(d / "project.json")["job_code"] == "KS-26010"
    rv = _read(d / "rev_1.0.json")
    assert rv["modules"] == {"m1": True} and rv["lines"][0]["category"] == "engineering"


def test_new_revision_copy_keeps_unknown_fields(folder: Path):
    from proposal_builder.proposal import new_revision_from
    rev = ProjectStore(DataStore(folder)).load_revision("26010")
    nxt = new_revision_from(rev, "1.1")
    assert nxt.unknown_fields["modules"] == {"m1": True}
    assert nxt.lines[0].unknown_fields["category"] == "engineering"


def test_foreign_catalog_sections_hidden_and_kept(folder: Path):
    st = AppState(DataStore(folder))
    cat = st.catalog
    assert all(s.number != 4000 for s in cat.sections)
    assert cat.item(4010) is None
    assert all(i.code != 4010 for prof in (KS, CW) for i in cat.items_for(prof))
    assert 4010 in cat.reserved_codes() and 4000 in cat.reserved_section_numbers()
    cat.sections.append(Section(number=1500, name="Extra", key="X"))
    st.save_catalog()
    c = _read(folder / "catalog.json")
    assert CE_SECTION in c["sections"] and CE_ITEM in c["items"]
    assert "foreign_sections" not in c and "foreign_items" not in c
    again = Catalog.model_validate_json((folder / "catalog.json").read_text(encoding="utf-8"))
    assert len(again.foreign_items) == 1 and any(s.number == 1500 for s in again.sections)


def test_foreign_code_counts_as_duplicate():
    cat = Catalog.model_validate({"sections": [CE_SECTION, {"number": 100, "name": "G", "key": "G"}],
                                  "items": [CE_ITEM, {"code": 4010, "section": 100, "title": "Clash",
                                                      "price_source": "fixed", "price": "1"}]})
    assert "duplicate item code 4010" in cat.validate_refs()


def test_foreign_projects_listed_but_never_opened(folder: Path):
    ps = ProjectStore(DataStore(folder))
    assert [p.number for p in ps.list_projects()] == ["26010"]
    foreign = ps.list_foreign_projects()
    assert [d["number"] for d in foreign] == ["26011"] and foreign[0]["profile"] == "ce"
    with pytest.raises(ForeignProjectError):
        ps.load_project("26011")
    with pytest.raises(ForeignProjectError):
        ps.load_revision("26011")
    with pytest.raises(ForeignProjectError):
        ps.save_revision("26011", Revision())
    with pytest.raises(ForeignProjectError):
        ps.save_project(Project(number="26011", project_name="x"))
    with pytest.raises(ValueError):          # its number stays taken
        ps.create(Project(number="26011", project_name="x"), Revision())


def test_foreign_files_untouched_by_normal_use(folder: Path):
    before = _digest(folder)
    st = AppState(DataStore(folder))          # startup migrations and customer linking run here
    st.save_settings()
    st.save_settings(CW)
    st.save_catalog()
    st.save_customers()
    all_project_income(st.projects, st.settings, st.catalog, st.settings_for)
    after = _digest(folder)
    ce = [k for k in before if k.startswith(("projects/26011", "profiles/ce/"))]
    assert ce and all(after[k] == before[k] for k in ce)
    c = _read(folder / "catalog.json")
    assert CE_SECTION in c["sections"] and CE_ITEM in c["items"]


def test_income_ignores_foreign_projects(folder: Path):
    st = AppState(DataStore(folder))
    rows = all_project_income(st.projects, st.settings, st.catalog, st.settings_for)
    assert all(r.project.number != "26011" for r in rows)


def test_change_order_log_keeps_unknown_fields():
    log = ChangeOrderLog.model_validate({"orders": [], "ecn_mode": True})
    assert json.loads(log.model_dump_json())["ecn_mode"] is True


def test_customer_book_and_settings_extras_roundtrip():
    book = CustomerBook.model_validate({"customers": [{"id": "a", "name": "A", "tier": 2}]})
    assert json.loads(book.model_dump_json())["customers"][0]["tier"] == 2
    s = Settings.model_validate({"brand": {"primary": "#123456"}})
    assert json.loads(s.model_dump_json())["brand"] == {"primary": "#123456"}
