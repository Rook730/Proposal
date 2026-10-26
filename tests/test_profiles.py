"""Company profiles: Kept Spec Advisors (ks) and Convenient Woodworking (cw)."""

import io
import json
from decimal import Decimal
from pathlib import Path

import pytest

from proposal_builder import store
from proposal_builder.calc import calculate
from proposal_builder.models import CW, KS, Catalog, CatalogItem, Section
from proposal_builder.proposal import Line, Project, Revision, default_blocks
from proposal_builder.store import DataStore, ProjectStore
from proposal_builder.summary import all_project_income
from proposal_builder.ui.state import AppState


@pytest.fixture
def st(tmp_path: Path) -> AppState:
    return AppState(DataStore(tmp_path / "data"))


def test_old_project_files_are_kept_spec():
    p = Project.model_validate_json(json.dumps({"number": "26005", "project_name": "Kitchen"}))
    assert p.profile == KS


def test_cw_files_seeded_beside_kept_spec(st: AppState):
    root = st.store.root
    assert (root / "settings.json").exists() and (root / "boilerplate.json").exists()
    assert (root / "profiles/cw/settings.json").exists()
    assert (root / "profiles/cw/boilerplate.json").exists()
    assert (root / "profiles/cw/logo.svg").exists()
    cw = st.settings_for(CW)
    assert cw.company.dba == "Convenient Woodworking"
    assert cw.company.email == "Nick@ConvenientWoodworking.com"
    assert st.settings.company.dba == "Kept Spec Advisors"
    assert st.boilerplate_for(CW) is not st.boilerplate
    assert {b.heading for b in st.boilerplate_for(CW).blocks} >= {"Intro", "How to read this proposal", "Signature"}


def test_shared_settings_come_from_kept_spec(st: AppState):
    st.settings.next_proposal_seq = 42
    cw = st.settings_for(CW)
    assert cw.next_proposal_number() == st.settings.next_proposal_number()
    assert cw.lists is st.settings.lists and cw.performers is st.settings.performers
    # editing a shared list through the CW settings lands in the Kept Spec file
    cw.spelling_words.append("mortise")
    st.save_settings(CW)
    again = AppState(DataStore(st.store.root))
    assert "mortise" in again.settings.spelling_words
    assert again.settings_for(CW).next_proposal_seq == 42


def test_profile_settings_saved_separately(st: AppState):
    cw = st.settings_for(CW)
    cw.validity_days = 45
    cw.company.phone = "555.0100"
    st.save_settings(CW)
    again = AppState(DataStore(st.store.root))
    assert again.settings_for(CW).validity_days == 45
    assert again.settings_for(CW).company.phone == "555.0100"
    assert again.settings.validity_days == 30
    assert again.settings.company.phone == "423.218.6067"


def test_profile_terms_library_saved_separately(st: AppState):
    lib = st.boilerplate_for(CW)
    lib.blocks[0].body = "Edited for CW"
    st.save_boilerplate(CW)
    again = AppState(DataStore(st.store.root))
    assert again.boilerplate_for(CW).blocks[0].body == "Edited for CW"
    assert all(b.body != "Edited for CW" for b in again.boilerplate.blocks)


def test_profile_backups_do_not_mix(st: AppState):
    st.settings.validity_days = 31
    st.save_settings()
    cw = st.settings_for(CW)
    cw.validity_days = 46
    st.save_settings(CW)
    names = sorted(p.name for p in st.store.backup_dir.iterdir())
    assert any(n.startswith("settings.") for n in names)
    assert any(n.startswith("profiles_cw_settings.") for n in names)


def test_sections_and_items_by_profile():
    cat = Catalog(sections=[Section(number=100, name="General", key="G"),
                            Section(number=2100, name="Metalcraft", key="M", profile=CW),
                            Section(number=1500, name="Delivery", key="D", profile="both")],
                  items=[CatalogItem(code=110, section=100, title="Printing"),
                         CatalogItem(code=2110, section=2100, title="Restore"),
                         CatalogItem(code=1510, section=1500, title="Delivery"),
                         CatalogItem(code=9999, section=9900, title="Orphan")])
    assert [s.number for s in cat.sections_for(KS)] == [100, 1500]
    assert [s.number for s in cat.sections_for(CW)] == [2100, 1500]
    assert {i.code for i in cat.items_for(KS)} == {110, 1510, 9999}
    assert {i.code for i in cat.items_for(CW)} == {2110, 1510}


def test_seed_sections_are_kept_spec():
    from importlib import resources
    cat = Catalog.model_validate_json((resources.files("proposal_builder") / "seed" / "catalog.json")
                                      .read_text(encoding="utf-8"))
    assert all(s.profile == KS for s in cat.sections if s.number < 2000)
    assert {s.number: s.profile for s in cat.sections if s.number >= 2000} == {3000: CW, 3100: CW}


def test_config_moves_from_old_app_folder(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.delenv("PROPOSAL_DATA_DIR", raising=False)
    old = tmp_path / "KeptSpecProposal" / "config.json"
    old.parent.mkdir()
    old.write_text(json.dumps({"data_dir": str(tmp_path / "Proton")}), encoding="utf-8")
    assert store.resolve_data_dir() == tmp_path / "Proton"
    assert (tmp_path / "ProposalBuilder" / "config.json").exists()
    assert old.exists()                       # left in place for an older copy of the app


def _cw_project(st: AppState) -> tuple[Project, Revision]:
    p = Project(number="26006", project_name="Boxes", client_name="Borg Warner Turbo", profile=CW)
    rev = Revision(blocks=default_blocks(st.boilerplate_for(CW).blocks))
    piece = rev.add_piece("Square box")
    rev.add_line(Line(id=rev.new_line_id(piece.number), section=piece.number, title="Square box", unit="EA",
                      qty=Decimal(10), unit_price=Decimal(305)))
    ProjectStore(st.store).create(p, rev)
    return p, rev


def test_cw_project_totals_and_income(st: AppState):
    p, rev = _cw_project(st)
    res = calculate(rev, st.settings_for(p.profile), st.catalog.stock_classes, p)
    assert res.base.total == Decimal("3050.00")
    rows = all_project_income(st.projects, st.settings, st.catalog, st.settings_for)
    assert isinstance(rows, list)


def test_cw_document_uses_cw_company_and_svg_logo(st: AppState):
    pytest.importorskip("typst")
    pypdf = pytest.importorskip("pypdf")
    from proposal_builder.render.document import build_document, compile_document
    p, rev = _cw_project(st)
    s = st.settings_for(CW)
    doc = build_document(p, rev, s, st.catalog, st.boilerplate_for(CW))
    assert doc["company"]["name"] == "Convenient Woodworking"
    assert any("Nick" in str(b) for b in doc["intro"])
    pdf = compile_document(doc, st.store.path(s.company.logo_path))
    text = "".join(pg.extract_text() for pg in pypdf.PdfReader(io.BytesIO(pdf)).pages)
    assert "Nick@ConvenientWoodworking.com" in text
    assert "Square box" in text


def test_editor_and_closeout_open_with_project_profile(tmp_path: Path):
    from proposal_builder.ui import state as state_mod
    from proposal_builder.ui.closeout import Closeout
    from proposal_builder.ui.editor import Editor
    st = state_mod.set_data_dir(tmp_path / "data")
    p, rev = _cw_project(st)
    st.save_catalog()
    ed = Editor(p.number)
    assert ed.settings.company.dba == "Convenient Woodworking"
    assert ed.library is st.boilerplate_for(CW)
    assert [s.number for s in ed.sections] == [3000, 3100]
    assert ed.results.base.total == Decimal("3050.00")
    assert Closeout(p.number).settings.company.dba == "Convenient Woodworking"
