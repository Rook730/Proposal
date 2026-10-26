"""UI handler regressions (1.9.1)."""

import ast
from pathlib import Path

UI = Path(__file__).parents[1] / "src" / "proposal_builder" / "ui"


def test_warn_ignores_non_list_results():
    from proposal_builder.ui.widgets import warn

    class Handle:                       # what refreshable.refresh() returns: truthy, not a list
        pass
    warn(Handle())                      # used to raise and stop the grid from redrawing after a delete
    warn(None)
    warn([])


def test_no_unawaited_async_calls_in_lambdas():
    """A lambda like `lambda: (dlg.close(), self.export_pdf())` creates the coroutine and never runs it."""
    problems = []
    for f in UI.glob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        async_methods = {n.name for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef)}
        for lam in (n for n in ast.walk(tree) if isinstance(n, ast.Lambda)):
            for c in ast.walk(lam.body):
                if (c is not lam.body and isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                        and isinstance(c.func.value, ast.Name) and c.func.value.id == "self"
                        and c.func.attr in async_methods):
                    problems.append(f"{f.name}:{lam.lineno} self.{c.func.attr}()")
    assert problems == []


def test_lines_grid_shows_print_order(tmp_path):
    """Header sorting would hide Move up / Move down (and sorts IDs as text: 10.01 before 2.01)."""
    import json
    from proposal_builder.proposal import Project, Revision
    from proposal_builder.store import ProjectStore
    from proposal_builder.ui import state as state_mod
    from proposal_builder.ui.editor import Editor
    st = state_mod.set_data_dir(tmp_path / "data")
    data = json.loads((Path(__file__).parent / "fixtures" / "26005_anon.json").read_text(encoding="utf-8"))
    ProjectStore(st.store).create(Project.model_validate(data["project"]), Revision.model_validate(data["revision"]))
    opts = Editor("26005")._grid_options()
    assert opts["defaultColDef"]["sortable"] is False
    assert not any(c.get("sortable") or c.get("sort") for c in opts["columnDefs"])
