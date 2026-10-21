import sys
import types
from decimal import Decimal

from proposal_builder import spelling
from proposal_builder.models import Boilerplate, BoilerplateBlock, Catalog, CatalogItem
from proposal_builder.proposal import Alternate, Line, Project, ProposalBlock, Revision


def _rev():
    rev = Revision(sections=[100])
    rev.add_line(Line(id="1.01", section=100, code=500, title="Cabinetery install",
                      general_description="Remove existing cabinetery.",
                      notes="Recieve {cabinetery_count} boxes. See https://example.com/cabinetery. "
                            "GFCI and LVP per plan; QuietCool fan; owner's backsplash.",
                      unit_price=Decimal(1)))
    rev.add_line(Line(id="2.01", section=200, title="Excluded sectoin", unit_price=Decimal(1)))
    rev.sections = [100]                      # section 200 unchecked: does not print
    rev.alternates.append(Alternate(number=1, name="Upgrayde"))
    rev.blocks.append(ProposalBlock(id="pay", heading="Payment", title="", body="Paymnet is due."))
    rev.blocks.append(ProposalBlock(id="off", heading="X", title="", body="Turnded off", on=False))
    return rev


def test_check_finds_printed_misspellings_only():
    rev = _rev()
    found = {f.word: f for f in spelling.check(Project(number="1", project_name="Kitchen"), rev)}
    assert set(found) == {"Cabinetery", "Recieve", "Upgrayde", "Paymnet"}
    # all-caps, inner capitals, {variables}, links, unchecked sections and blocks that are off are skipped
    assert [p.label for p in found["Cabinetery"].places] == ["1.01 title", "1.01 catalog description"]


def test_user_words_and_builtin_words_are_accepted():
    rev = _rev()
    found = spelling.check(Project(number="1"), rev, ["paymnet", "Upgrayde"])
    assert {f.word for f in found} == {"Cabinetery", "Recieve"}
    assert "backsplash" in spelling.BUILTIN_WORDS


def test_suggestions_keep_case():
    assert spelling.suggestions("Recieve")[0] == "Receive"
    assert "cabinetry" in spelling.suggestions("cabinetery")


def test_replace_word_leaves_variables_and_links():
    text, n = spelling.replace_word("Cabinetery: {cabinetery_x} cabinetery's https://a.com/cabinetery", "cabinetery",
                                    "cabinetry")
    assert n == 2
    assert text == "Cabinetry: {cabinetery_x} cabinetry's https://a.com/cabinetery"


def test_apply_fix_updates_revision_catalog_and_library():
    rev = _rev()
    project = Project(number="1")
    cat = Catalog(items=[CatalogItem(code=500, section=100, title="Cabinets",
                                     description="Remove existing cabinetery.")])
    bp = Boilerplate(blocks=[BoilerplateBlock(id="pay", heading="Payment", title="", body="Paymnet is due.")])
    found = {f.word: f for f in spelling.check(project, rev)}
    counts = spelling.apply_fix(project, rev, found["Cabinetery"], "Cabinetry", cat, bp)
    ln = rev.line("1.01")
    assert ln.title == "Cabinetry install"
    assert ln.general_description == "Remove existing cabinetry."
    assert cat.item(500).description == "Remove existing cabinetry."
    assert counts == {"line": 1, "general": 1, "catalog": 1}
    counts = spelling.apply_fix(project, rev, found["Paymnet"], "Payment", cat, bp)
    assert rev.blocks[0].body == "Payment is due." and bp.blocks[0].body == "Payment is due."
    assert counts == {"block": 1, "library": 1}
    assert {f.word for f in spelling.check(project, rev)} == {"Recieve", "Upgrayde"}


def test_native_menu_patch(monkeypatch):
    from proposal_builder import native_menu

    class Settings:
        AreDefaultContextMenusEnabled = False

    class Sender:
        CoreWebView2 = types.SimpleNamespace(Settings=Settings())

    class EdgeChrome:
        def on_webview_ready(self, sender, args):
            sender.CoreWebView2.Settings.AreDefaultContextMenusEnabled = False   # what pywebview does

    edge = types.ModuleType("webview.platforms.edgechromium")
    edge.EdgeChrome = EdgeChrome
    wv = types.ModuleType("webview")

    def initialize(gui=None):
        sys.modules["webview.platforms.edgechromium"] = edge
        return "winforms"

    wv.initialize = initialize
    monkeypatch.setitem(sys.modules, "webview", wv)
    monkeypatch.delitem(sys.modules, "webview.platforms.edgechromium", raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    native_menu.install()
    native_menu.install()   # idempotent
    assert wv.initialize() == "winforms"
    wv.initialize()
    s = Sender()
    EdgeChrome().on_webview_ready(s, None)
    assert s.CoreWebView2.Settings.AreDefaultContextMenusEnabled is True
    sys.modules.pop("webview.platforms.edgechromium", None)
