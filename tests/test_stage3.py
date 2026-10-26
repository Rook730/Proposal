"""1.9.0: restoration items, veneer, client property and storage, appendix images, 6 alternates,
placeholders and unpriced lines blocking Issue."""

import io
from decimal import Decimal as D
from importlib import resources
from pathlib import Path

import pytest

from proposal_builder import cw_catalog
from proposal_builder.buildsheet import BuildMaterial, BuildSheet, PricingPolicy
from proposal_builder.calc import calculate, variable_map
from proposal_builder.models import Boilerplate, Catalog, Settings
from proposal_builder.preflight import blocking, content_checks
from proposal_builder.proposal import (Alternate, Line, Project, ProposalImage, Revision, default_blocks,
                                       line_from_item)


def seed(path):
    return (resources.files("proposal_builder") / "seed" / path).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def cw():
    return (Settings.model_validate_json(seed("cw/settings.json")), Catalog.model_validate_json(seed("catalog.json")),
            Boilerplate.model_validate_json(seed("cw/boilerplate.json")))


def test_restoration_items(cw):
    _, cat, _ = cw
    assert cat.item(2110).title == "Restore" and cat.item(2110).price == D(200)
    assert "mechanical" in cat.item(2120).description and "refinish" in cat.item(2110).description
    assert cat.item(2130).price is None                              # priced per job
    assert cat.item(2630).section == 3000                            # joins Delivery & Installation
    assert {i.code for i in cat.items_for("cw")} >= {2010, 2420, 2530, 2620, 3101}
    assert not any(2000 <= i.code < 3000 for i in cat.items_for("ks"))


def test_restoration_applies_once_to_a_1_8_catalog():
    cat = Catalog()
    cw_catalog.apply(cat)                                            # a 1.8.0 catalog
    assert cat.item(2110) is None
    assert cw_catalog.apply_all(cat) and cat.item(2110) is not None
    cat.items = [i for i in cat.items if i.code != 2110]
    assert not cw_catalog.apply_all(cat) and cat.item(2110) is None  # deleted stays deleted


def test_terms_block_added_once(cw):
    _, _, bp = cw
    assert any(b.id == "client-property" for b in bp.blocks)
    old = Boilerplate(headings=["Terms & Conditions"], blocks=[])
    assert cw_catalog.apply_terms(old) and len(old.blocks) == 1
    old.blocks = []
    assert not cw_catalog.apply_terms(old) and old.blocks == []


def test_storage_and_property_variables(cw):
    s, _, bp = cw
    p = Project(number="26007", profile="cw", property_received=__import__("datetime").date(2026, 4, 11))
    v = variable_map(p, Revision(), s)
    assert (v["storage_rate"], v["storage_min"], v["storage_grace_days"]) == ("$2.00", "$25.00", "15")
    assert v["property_received"] == "2026.04.11"
    body = next(b.body for b in bp.blocks if b.id == "client-property")
    from proposal_builder.calc import render
    assert "$2.00 per square foot" in render(body, v)


def test_veneer_square_feet():
    b = BuildSheet.from_policy(PricingPolicy())
    b.materials = [BuildMaterial(kind="veneer", name="Walnut", pieces=D(2), width=D(24), length=D(48),
                                 yield_tier="low", unit_cost=D("3.50"))]
    b.recalc()
    m = b.materials[0]
    assert (m.qty, m.unit, m.cost) == (D("20.00"), "SF", D("70.00"))      # 2 x 24 x 48 / 144 x 1.25


def test_six_alternates_and_same_line_options(cw):
    s, cat, _ = cw
    rev = Revision()
    piece = rev.add_piece("Table")
    base = Line(id=rev.new_line_id(piece.number), section=piece.number, title="Table, cherry", unit_price=D(1000))
    rev.add_line(base)
    for n in range(1, 7):
        alt = Line(id=rev.new_line_id(piece.number), section=piece.number, title=f"Option {n}",
                   unit_price=D(1000 + 100 * n), alternate=n)
        rev.add_line(alt)
        rev.alternates.append(Alternate(number=n, name=f"Option {n}", removes=[base.id]))
    res = calculate(rev, s, cat.stock_classes)
    assert sorted(res.alternates) == [1, 2, 3, 4, 5, 6]
    assert res.combinations == []                          # all swap the same line: one or the other
    assert res.alternates[6].subtotal == D(1600)


def test_placeholders_and_unpriced_lines_block_issue(cw):
    s, cat, _ = cw
    rev = Revision()
    piece = rev.add_piece("Lamp")
    ln = line_from_item(cat.item(2130), cat, rev.new_line_id(piece.number))
    ln.section = piece.number
    rev.add_line(ln)
    ok = Line(id=rev.new_line_id(piece.number), section=piece.number, title="Refurbish", unit_price=D(75),
              notes="Price TBD after teardown")
    rev.add_line(ok)
    p = Project(number="1", profile="cw", client_name="X", site_address="Y")
    res = calculate(rev, s, cat.stock_classes, p)
    msgs = blocking(p, rev, res)
    assert any("no unit price" in m for m in msgs) and any("TBD" in m for m in msgs)
    kinds = {k for k, m, _ in content_checks(p, rev, res) if "TBD" in m or "no unit price" in m}
    assert kinds == {"error"}
    ln.unit_price, ok.notes = D(0), "Price after teardown"
    assert blocking(p, rev, calculate(rev, s, cat.stock_classes, p)) == []


def test_images_scaled_and_printed(tmp_path: Path, cw):
    PIL = pytest.importorskip("PIL")
    from PIL import Image
    from proposal_builder.images import add_image, normalize
    buf = io.BytesIO()
    Image.new("RGB", (4000, 3000), (200, 120, 40)).save(buf, "JPEG")
    name = add_image(tmp_path / "images", buf.getvalue(), "IMG 0042.JPG")
    assert name.endswith(".jpg") and name.startswith("IMG_0042_")
    with Image.open(tmp_path / "images" / name) as im:
        assert max(im.size) == 2000
    with pytest.raises(ValueError):
        normalize(b"not an image", ".pdf")
    s, cat, bp = cw
    from proposal_builder.render.document import build_document, compile_document
    rev = Revision(blocks=default_blocks(bp.blocks))
    piece = rev.add_piece("Side table")
    rev.add_line(Line(id=rev.new_line_id(piece.number), section=piece.number, title="Side table",
                      unit_price=D(3000)))
    rev.images = [ProposalImage(file=name, caption="Rendering", section=piece.number),
                  ProposalImage(file="missing.png", caption="gone")]
    p = Project(number="26008", profile="cw", client_name="Abraham", project_name="Side table")
    doc = build_document(p, rev, s, cat, bp, image_dir=tmp_path / "images")
    assert [(a["caption"], a["piece"]) for a in doc["appendix"]] == [("Rendering", "Side table")]
    pytest.importorskip("typst")
    pypdf = pytest.importorskip("pypdf")
    pdf = compile_document(doc, None)
    text = "".join(pg.extract_text() for pg in pypdf.PdfReader(io.BytesIO(pdf)).pages)
    assert "Appendix: Images and Drawings" in text and "Rendering" in text
