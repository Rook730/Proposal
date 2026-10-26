# Handoff: woodworking proposals (company profiles)

Written 2026-10-25 at v1.7.2, updated after stage 1. For the sessions that add Convenient Woodworking proposals to this app.

## Decision

Approach A: same app, a second **company profile**. Kept Spec Advisors (project management: subs and trades on site) and Convenient Woodworking (building or restoring a physical thing) each have their own terms library, settings, branding and PDF identity. The catalog, customers, contractors, suppliers, numbering, updater and Windows build are shared. Nick picked this over a fork or a shared core package (2026-10-25).

Intake with Nick (2026-10-25) is done: answers in the claude.ai Project (`claude/proposal-builder-cw-intake.md`), requirements in `docs/cw-requirements.md`, summary in `docs/requirements.md` section 16.

**Status:** stages 1 to 3 are released (1.8.0 and 1.9.0; PENDING items 43 to 69). Stage 4 (actual hours by phase for calibration, wholesale) waits until the app is in use. Open values: profit percent (10% placeholder), real hardware prices for the square box template, storage defaults to confirm.

## Read first

- `CLAUDE.md`: layout, conventions, test and release commands.
- `docs/requirements.md`: the spec (source of truth) with a per-version change log at the end.
- `docs/PENDING.md`: the running change list. Nick decides when to release ("release" means bump, build, publish).
- `docs/ux-review.md`: UX review and what was done from it.
- Project docs in the claude.ai Project mirror PENDING and requirements (`claude/proposal-builder-*.md`); update both when they change.

## Working agreements with Nick

- Keep a running list in `docs/PENDING.md`; release only when he says so.
- User-facing text: no em dashes. Terse, direct, no inflated language.
- Ask when an instruction is not completely clear; use AskUserQuestion for real choices (formats, naming).
- Catalog edits never change saved proposals (snapshot rule). Library text migrations update only unedited text.
- Verify UI changes with screenshots (Playwright against `python -m proposal_builder --browser --no-show --port N --data <copy>`), run `python -m pytest -q` and the self-test before committing.

## Release process (changed 2026-10-21)

Pushing tags from a session is blocked (HTTP 403 from the proxy); pushing commits to `main` works. To release:

1. Bump `__version__` in `src/proposal_builder/__init__.py` and `version` in `pyproject.toml`; move PENDING items under "Released in X.Y.Z"; add a line to the change log at the end of `docs/requirements.md`.
2. Commit and push `main`.
3. `gh workflow run build-windows.yml -R Rook730/Proposal --ref main -f release_tag=vX.Y.Z`. The workflow builds the exe, runs `--self-test` and the self-update check, then creates the tag and the GitHub release.
4. `gh run watch <id> --exit-status`, then confirm with `gh api repos/Rook730/Proposal/releases/latest`.

The in-app updater reads the latest GitHub release of `Rook730/Proposal` (public repo; a private repo would need a token).

## Architecture in one page

- Python 3.13, NiceGUI 3 (Quasar + AG Grid), pydantic v2 with Decimal money, Typst for PDFs (Carlito font), PyInstaller one-file exe in a pywebview window (WebView2 on Windows).
- Data folder (Proton Drive synced): `settings.json`, `catalog.json`, `boilerplate.json` (Terms library), `customers.json`, `contractors.json`, `suppliers.json`, `projects/<number>_<client>_<name>/` (project.json, rev_X.Y.json, change_orders.json, reconciliation.json, quotes.json, pdf/), `backups/`. Writes are atomic with rotating backups (`store.py`); `store.SAVE_HOOKS` drives the "Saved" indicator.
- Core modules: `models.py` (catalog, settings), `proposal.py` (Project, Revision, Line, Alternate, ProposalBlock), `calc.py` (totals, percent items, alternates, combinations, stock rounding), `revisions.py` (issue, new revision, finalize to 2.0, accept, diffs), `closeout.py` (change orders, ledger), `income.py` / `summary.py` (internal income), `crm.py`, `quotes.py`, `preflight.py` + `spelling.py` (Issues tab), `render/` (document data + Typst templates).
- UI: `ui/editor.py` (proposal editor), `ui/pages.py` (catalog pages, Settings), `ui/crm_pages.py`, `ui/closeout.py`, `ui/projects.py`, `ui/summary_page.py`, shared pieces in `ui/widgets.py` (layout and menu, page frame, EditableGrid, date and money formats).

## Where the single-company assumptions live

These are the places a profile has to reach. Roughly in order of impact. Items 1 to 3 and 11 are handled in stage 1; the rest are stage 2.

1. **One catalog, one terms library, one settings file**: `store.py` (`FILES`, `load_catalog`, `load_boilerplate`, `load_settings`), `ui/state.py` (`AppState` holds one of each).
2. **Company identity**: `Settings.company` (legal name, DBA, address, phone, email, logo), `Settings.recommended_by`, PDF header in `render/templates/proposal.typ` and `common.typ`.
3. **Numbering**: `Settings.proposal_year` / `next_proposal_seq` / `next_proposal_number()`; project folders are keyed by number (`store.ProjectStore.project_dir`). Decided: one shared sequence (shared setting).
4. **GC-specific catalog roles**: `Settings.co_markup_codes` (1410, 1420), `contingency_code` (1310), `co_management_code` (1320), `co_management_rate_key`; percent items and credit-if-unused in `importer.py`; change order pricing and the ledger in `closeout.py` assume these exist.
5. **Payment terms**: `Settings.deposit_pct`, `retainage_pct`, `payment_schedule()` in `calc.py`, labels in `render/document.py` ("Construction progress payments").
6. **License threshold warning**: `Settings.license_threshold`, Issues tab and change orders page. A GC concern; probably off for furniture.
7. **Performers and income**: `Performer` enum and `default_performers()` in `models.py`; KS / CW entities in `income.py`; Income tab and Income summary columns hard-code "Kept Spec" / "Convenient Woodworking" (`ui/editor.py` income_panel, `ui/summary_page.py`, `summary.py` CSV).
8. **Terms text**: `added_terms.py` and `migrations.py` carry Kept Spec wording (hourly rates, lien waivers, allowances, actual cost); the seed `boilerplate.json` is GC text.
9. **Hard-coded names in the UI and docs**: app title (`ui/widgets.py`, `__main__.py`), closeout labels ("Absorbed by Kept Spec", payments text), `render/closeout_docs.py`, `rates_table()` docstring, `import_proposal.py` (CW prefix).
10. **Seed and importer**: `seed/*.json` and `importer.py` come from the KS Excel workbook; a woodworking seed needs its own source.
11. **Packaging names**: exe name, `APP_DIR_NAME`, `DEFAULT_DATA_DIR_NAME`, updater User-Agent. Can stay as they are (one app), or be renamed to a neutral name.

## As built (stages 1 to 3)

- `models.py`: `KS`, `CW`, `PROFILES`, `Section.profile` ("ks", "cw", "both"), `Catalog.sections_for()` / `items_for()`, `SHARED_SETTINGS`.
- `proposal.py`: `Project.profile` (default "ks").
- `store.py`: `DataStore.profile_file()`; Kept Spec files at the root, others in `profiles/<key>/`; seed from `seed/cw/`; `load_settings(profile)` shares the root's shared fields (`share_settings`, same objects); backups of profile files named `profiles_cw_settings.<time>.json`; `%APPDATA%\ProposalBuilder` with a one-time copy from `KeptSpecProposal`.
- `ui/state.py`: `settings_for(profile)`, `boilerplate_for(profile)`, `save_settings(profile)`, `save_boilerplate(profile)`. `st.settings` / `st.boilerplate` are Kept Spec.
- Editor: `self.settings`, `self.library`, `self.sections` follow the project's profile. Closeout: `self.settings`. Projects list: Company column and filter; New project asks the company. Settings and Terms library: `?profile=` switch. Sections page: Company column.
- `render/document.py`: logo keeps its extension (SVG works). `proposal.typ`: paragraph break between intro blocks.
- Stage 2: `buildsheet.py` (BuildSheet, PricingPolicy, rough thickness), `cw_catalog.py` (one-time catalog additions and the seed's CW content), `models.PriceReferences` on the catalog, `Settings.pricing` / `payment_rule` / `tax_counties`, `Revision.pieces` / `rush_pct` / `taxable` / `tax_rate`, `Project.attention` / `po_number`, `Customer.is_company`. Calc: Built lines, rush, tax, `deposit_pct()`. Income: `cw_estimate_report`. Closeout: CW markup and tax on change orders. UI: `ui/build_ui.py` (build sheet dialog), Price references page, CW settings, pricing card in Terms & options, pieces in the sections panel. PDF: `_cw_totals`, `company_signature`, `compact_terms`.
- Stage 3: `cw_catalog.apply_restoration` / `apply_terms` (markers in Catalog.migrations and Boilerplate.migrations), `images.py` (Pillow scaling, store in projects/<folder>/images), `Revision.images`, appendix in `render/document.py` (`appendix()`, copied by `compile_document`) and `proposal.typ`, `preflight.blocking()` used by the Issue dialog, MAX_ALTERNATES = 6.
- Tests: `tests/test_profiles.py`, `tests/test_cw_pricing.py`, `tests/test_stage3.py`. Self-test prices the square box template (10 at $305, $3,263.50 with Buncombe tax) and renders a CW proposal with the SVG logo.

## Open questions for Nick

See `docs/cw-requirements.md` section 16: profit percent default, storage rate (proposed $2.00/SF of footprint per month, $25 minimum), box job inputs.
