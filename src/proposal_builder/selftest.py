"""End-to-end check used by the Windows build: data folder, catalog, calculation, PDF.

    python -m proposal_builder --self-test
    "Proposal Builder.exe" --self-test   (writes selftest.log next to the exe)
"""

from __future__ import annotations

import json
import tempfile
import traceback
from decimal import Decimal
from pathlib import Path


def run_self_test() -> tuple[bool, str]:
    lines: list[str] = []
    try:
        from . import __version__
        from .calc import calculate
        from .closeout import ChangeOrderLog, Reconciliation, build_ledger, contract_context
        from .proposal import Line, Project, Revision, contract_revision, default_blocks, line_from_item
        from .render.closeout_docs import ledger_document
        from .render.document import build_document, compile_document
        from .store import DataStore, ProjectStore

        lines.append(f"proposal builder {__version__}")
        with tempfile.TemporaryDirectory() as tmp:
            ds = DataStore(Path(tmp) / "data")
            written = ds.initialize_from_seed()
            lines.append(f"seeded: {', '.join(written)}")
            settings, catalog, bp = ds.load_settings(), ds.load_catalog(), ds.load_boilerplate()
            assert not catalog.validate_refs(), catalog.validate_refs()
            rev = Revision(blocks=default_blocks(bp.blocks))
            for code in (210, 1410, 1420):
                it = catalog.item(code)
                rev.add_line(line_from_item(it, catalog, rev.new_line_id(it.section)))
            rev.add_line(Line(id=rev.new_line_id(1100), section=1100, title="Test line", unit_price=Decimal(100),
                              notes="Notes with $ # [brackets] and {project_name}"))
            project = Project(number="99999", client_name="Self Test", project_name="Check")
            ProjectStore(ds).create(project, rev)
            res = calculate(rev, settings, catalog.stock_classes, project)
            lines.append(f"calc total {res.base.total}")
            pdf = compile_document(build_document(project, rev, settings, catalog, bp), ds.path("logo.png"))
            assert pdf[:4] == b"%PDF", "proposal PDF"
            lines.append(f"proposal pdf {len(pdf)} bytes")
            ctr = contract_context(contract_revision(rev, []), settings, catalog.stock_classes, project)
            recon = Reconciliation()
            led = compile_document(ledger_document(project, build_ledger(ctr, ChangeOrderLog(), recon), recon, settings),
                                   ds.path("logo.png"), template="ledger.typ")
            assert led[:4] == b"%PDF", "ledger PDF"
            lines.append(f"ledger pdf {len(led)} bytes")
            # Convenient Woodworking: its own settings, terms and SVG logo
            cw_settings, cw_bp = ds.load_settings("cw"), ds.load_boilerplate("cw")
            cw_project = Project(number="99998", client_name="Self Test", project_name="Box", profile="cw")
            cw_rev = Revision(blocks=default_blocks(cw_bp.blocks), taxable=True, tax_county="Buncombe",
                              tax_rate=cw_settings.tax_rate("Buncombe"))
            piece = cw_rev.add_piece("Square box")
            box = line_from_item(catalog.item(3101), catalog, cw_rev.new_line_id(piece.number))
            box.section, box.qty = piece.number, Decimal(10)
            cw_rev.add_line(box)
            cw_res = calculate(cw_rev, cw_settings, catalog.stock_classes, cw_project)
            assert cw_res.base.total == Decimal("3263.50"), cw_res.base.total
            lines.append(f"cw build sheet total {cw_res.base.total}")
            cw_pdf = compile_document(build_document(cw_project, cw_rev, cw_settings, catalog, cw_bp),
                                      ds.path(cw_settings.company.logo_path))
            assert cw_pdf[:4] == b"%PDF", "CW proposal PDF"
            lines.append(f"cw proposal pdf {len(cw_pdf)} bytes")
            from .purchase import purchase_list
            from .render.purchase_doc import purchase_document
            pl = purchase_list(cw_rev, cw_res, catalog.prices)
            assert pl.total() == Decimal("864.00"), pl.total()
            buy_pdf = compile_document(purchase_document(cw_project, cw_rev, cw_settings, pl),
                                       ds.path(cw_settings.company.logo_path), template="purchase.typ")
            assert buy_pdf[:4] == b"%PDF", "purchase list PDF"
            lines.append(f"cw purchase list {pl.total()}, pdf {len(buy_pdf)} bytes")
            # Convenient Enterprises: fee lines, an option, its proposal and estimate (header band, Plex font)
            from . import ce_catalog
            from .proposal import Alternate
            from .render.ce_document import build_estimate_document
            ce_catalog.apply(catalog)
            ce_catalog.apply_stage2(catalog)
            ce_settings, ce_bp = ds.load_settings("ce"), ds.load_boilerplate("ce")
            ce_project = Project(number="99997", client_name="Self Test", project_name="Cell", profile="ce")
            ce_rev = Revision(blocks=default_blocks(ce_bp.blocks))
            for code, qty, alt in ((4010, 80, None), (4110, 16, None), (4210, "2.5", None), (4050, 8, 1)):
                it = catalog.item(code)
                ln = line_from_item(it, catalog, ce_rev.new_line_id(it.section))
                ln.qty, ln.alternate = Decimal(qty), alt
                ce_rev.add_line(ln)
            ce_rev.alternates.append(Alternate(number=1, name="SISTEMA"))
            ce_rev.sections = [4000, 4100, 4200]
            ce_res = calculate(ce_rev, ce_settings, catalog.stock_classes, ce_project)
            assert ce_res.base.total == Decimal("12156.25"), ce_res.base.total
            assert ce_res.alternates[1].total == Decimal("13156.25"), ce_res.alternates[1].total
            ce_logo = ds.path(ce_settings.company.logo_path)
            ce_pdf = compile_document(build_document(ce_project, ce_rev, ce_settings, catalog, ce_bp), ce_logo)
            est_pdf = compile_document(build_estimate_document(ce_project, ce_rev, ce_settings, catalog), ce_logo)
            assert ce_pdf[:4] == b"%PDF" and est_pdf[:4] == b"%PDF", "CE proposal / estimate PDF"
            lines.append(f"ce total {ce_res.base.total}, proposal {len(ce_pdf)} bytes, estimate {len(est_pdf)} bytes")
            # Detailed depth: consultant-bought hardware line, milestone schedule, BOM and timeline tables
            from . import ce
            from .ce_models import CONSULTANT, DETAILED, BomItem
            ce.set_depth(ce_rev, DETAILED, ce_bp, ce_settings)
            ce_rev.bom = [BomItem(description="Safety relay", manufacturer="Test", model="T1", qty=Decimal(2),
                                  unit_cost=Decimal(500), buyer=CONSULTANT)]
            ce.sync_hardware_line(ce_rev, catalog, ce_settings, lambda sec, code: ce_rev.new_line_id(sec))
            ce_res = calculate(ce_rev, ce_settings, catalog.stock_classes, ce_project)
            assert ce_res.base.total == Decimal("13256.25"), ce_res.base.total
            rows, left = ce.milestone_schedule(ce_rev, ce_res.base, ce_settings, catalog)
            assert left == 0 and sum(r.amount for r in rows) == ce.split(ce_res.base, catalog).fixed, "milestones"
            det_pdf = compile_document(build_document(ce_project, ce_rev, ce_settings, catalog, ce_bp), ce_logo)
            assert det_pdf[:4] == b"%PDF", "CE detailed proposal PDF"
            lines.append(f"ce detailed total {ce_res.base.total}, proposal {len(det_pdf)} bytes")
            # appendix images: Pillow scales a photo down; the PDF prints it
            import io
            from PIL import Image
            from .images import add_image
            from .proposal import ProposalImage
            buf = io.BytesIO()
            Image.new("RGB", (3000, 2000), (168, 123, 32)).save(buf, "JPEG")
            img_dir = ProjectStore(ds).project_dir("99999") / "images"
            name = add_image(img_dir, buf.getvalue(), "photo.jpg")
            cw_rev.images = [ProposalImage(file=name, caption="Self test")]
            img_pdf = compile_document(build_document(cw_project, cw_rev, cw_settings, catalog, cw_bp,
                                                      image_dir=img_dir), ds.path(cw_settings.company.logo_path))
            assert img_pdf[:4] == b"%PDF" and len(img_pdf) > len(cw_pdf), "appendix image"
            lines.append(f"appendix image ok ({(img_dir / name).stat().st_size} bytes stored)")
            from .spelling import check as spell_check
            from .spelling import suggestions
            rev.lines[-1].notes = "Install the cabinetery and recieve {project_name}"
            bad = [f.word for f in spell_check(project, rev)]
            assert bad == ["cabinetery", "recieve"], bad
            assert "cabinetry" in [s.lower() for s in suggestions("cabinetery")]
            lines.append("spelling ok")
            from .ui import closeout, crm_pages, editor, pages, projects, summary_page  # noqa: F401  UI modules import cleanly
            lines.append("ui modules ok")
            json.dumps({"ok": True})
        lines.append("SELF-TEST PASSED")
        return True, "\n".join(lines)
    except Exception:  # noqa: BLE001
        lines.append("SELF-TEST FAILED")
        lines.append(traceback.format_exc())
        return False, "\n".join(lines)
