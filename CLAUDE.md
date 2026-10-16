# Proposal Builder

Requirements: docs/requirements.md (source of truth; update it when a decision changes).

## Layout
- src/proposal_builder/models.py: pydantic models. Money and percents are Decimal; percents stored as fractions.
- src/proposal_builder/store.py: JSON file store (atomic writes, rotating backups in backups/).
- src/proposal_builder/importer.py: one-time Excel import; regenerates src/proposal_builder/seed/*.json.
- src/proposal_builder/proposal.py: Project/Revision/Line/Alternate, snapshot + pull update.
- src/proposal_builder/calc.py: totals, percent items, alternates, variables, stock rounding.
- src/proposal_builder/revisions.py: issue / new revision / finalize (2.0) / mark accepted; revision diffs.
- src/proposal_builder/closeout.py: change orders (pricing, contingency draws) and the final ledger math.
- src/proposal_builder/import_proposal.py: import a KS template proposal sheet as a project.
- src/proposal_builder/render/: document.py builds print data and compiles; templates/ holds proposal.typ, co.typ, ledger.typ (+ common.typ); closeout_docs.py builds CO and ledger data; markup.py converts note Markdown to Typst; fonts/ bundles Carlito (OFL, Calibri metrics).
- src/proposal_builder/ui/: NiceGUI pages (projects.py, editor.py, closeout.py, pages.py for catalog). Run with `python -m proposal_builder --browser`.
- tests/fixtures/26005_anon.json: anonymized 26005 import; acceptance totals 41,186.59 / 38,199.69.
- packaging/: build.py (PyInstaller, then --self-test), launcher.py, icon.ico. .github/workflows/build-windows.yml builds releases on version tags.
- src/proposal_builder/selftest.py: end-to-end check behind `--self-test`.

## Conventions
- Catalog edits must never change saved proposals (snapshot rule, spec 4.9).
- User-facing text: no em dashes.
- Tests: `python -m pytest -q`. Importer parity test needs PROPOSAL_XLSX=<path to workbook>.
- Release: bump __version__ (src/proposal_builder/__init__.py) and pyproject version, then push a tag vX.Y.Z.
- Regenerate seed: `python -m proposal_builder.importer <workbook.xlsx> --out src/proposal_builder/seed`.
