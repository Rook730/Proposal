# Proposal Builder

Requirements: docs/requirements.md (source of truth; update it when a decision changes).

## Layout
- src/proposal_builder/models.py: pydantic models. Money and percents are Decimal; percents stored as fractions.
- src/proposal_builder/store.py: JSON file store (atomic writes, rotating backups in backups/).
- src/proposal_builder/importer.py: one-time Excel import; regenerates src/proposal_builder/seed/*.json.
- src/proposal_builder/ui/: NiceGUI pages. Run with `python -m proposal_builder --browser`.

## Conventions
- Catalog edits must never change saved proposals (snapshot rule, spec 4.9).
- User-facing text: no em dashes.
- Tests: `python -m pytest -q`. Importer parity test needs PROPOSAL_XLSX=<path to workbook>.
- Regenerate seed: `python -m proposal_builder.importer <workbook.xlsx> --out src/proposal_builder/seed`.
