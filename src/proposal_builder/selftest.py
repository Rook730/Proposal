"""End-to-end check used by the Windows build: data folder, catalog, calculation, PDF.

    python -m proposal_builder --self-test
    "KeptSpec Proposal Builder.exe" --self-test   (writes selftest.log next to the exe)
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
