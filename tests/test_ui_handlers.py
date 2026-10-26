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
