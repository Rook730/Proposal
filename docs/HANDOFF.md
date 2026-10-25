# Handoff: woodworking proposals (company profiles)

Written 2026-10-25 at v1.7.2. For the session that adds Convenient Woodworking proposals to this app.

## Decision

Approach A: same app, a second **company profile**. Kept Spec Advisors (general contracting) and Convenient Woodworking (custom furniture) each get their own catalog, terms library, rates, numbering, branding and PDF layout. Customers, contractors, suppliers, the updater and the Windows build are shared. Nick picked this over a fork or a shared core package (2026-10-25).

Not decided yet: what a woodworking proposal contains. Get a current woodworking proposal or spreadsheet from Nick before designing the data model; see Open questions.

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

These are the places a profile has to reach. Roughly in order of impact:

1. **One catalog, one terms library, one settings file**: `store.py` (`FILES`, `load_catalog`, `load_boilerplate`, `load_settings`), `ui/state.py` (`AppState` holds one of each).
2. **Company identity**: `Settings.company` (legal name, DBA, address, phone, email, logo), `Settings.recommended_by`, PDF header in `render/templates/proposal.typ` and `common.typ`.
3. **Numbering**: `Settings.proposal_year` / `next_proposal_seq` / `next_proposal_number()`; project folders are keyed by number (`store.ProjectStore.project_dir`), so two profiles must not hand out the same number (e.g. separate prefixes or one shared sequence).
4. **GC-specific catalog roles**: `Settings.co_markup_codes` (1410, 1420), `contingency_code` (1310), `co_management_code` (1320), `co_management_rate_key`; percent items and credit-if-unused in `importer.py`; change order pricing and the ledger in `closeout.py` assume these exist.
5. **Payment terms**: `Settings.deposit_pct`, `retainage_pct`, `payment_schedule()` in `calc.py`, labels in `render/document.py` ("Construction progress payments").
6. **License threshold warning**: `Settings.license_threshold`, Issues tab and change orders page. A GC concern; probably off for furniture.
7. **Performers and income**: `Performer` enum and `default_performers()` in `models.py`; KS / CW entities in `income.py`; Income tab and Income summary columns hard-code "Kept Spec" / "Convenient Woodworking" (`ui/editor.py` income_panel, `ui/summary_page.py`, `summary.py` CSV).
8. **Terms text**: `added_terms.py` and `migrations.py` carry Kept Spec wording (hourly rates, lien waivers, allowances, actual cost); the seed `boilerplate.json` is GC text.
9. **Hard-coded names in the UI and docs**: app title (`ui/widgets.py`, `__main__.py`), closeout labels ("Absorbed by Kept Spec", payments text), `render/closeout_docs.py`, `rates_table()` docstring, `import_proposal.py` (CW prefix).
10. **Seed and importer**: `seed/*.json` and `importer.py` come from the KS Excel workbook; a woodworking seed needs its own source.
11. **Packaging names**: exe name, `APP_DIR_NAME`, `DEFAULT_DATA_DIR_NAME`, updater User-Agent. Can stay as they are (one app), or be renamed to a neutral name.

## Suggested shape (to confirm with Nick)

- `profiles/<key>/` inside the data folder holding that profile's `settings.json`, `catalog.json`, `boilerplate.json`; shared files stay at the root. Migrate the current files into `profiles/ks/` on first start, keeping a backup.
- `Project.profile` (default "ks" for existing projects). The editor, catalog pages, Terms library and Settings read the active project's or the selected profile's files.
- A profile switch in the menu (or per page) for catalog, terms and settings; New project asks which profile.
- One PDF template per profile (`proposal.typ` stays for KS; a woodworking template with its own header and sections), chosen by `Project.profile`.
- GC-only features (change order management allowance, contingency, license threshold, retainage) become profile settings that can be off.
- Income: map each profile to its entity so a woodworking project's income lands in the CW column and summary.

## Open questions for Nick

- A sample of a current woodworking proposal (or spreadsheet), to see line structure and pricing.
- Pricing basis: line items like the GC proposal, or materials (species, board feet, sheet goods, hardware) plus shop hours and finishing, or a fixed price per piece?
- Do woodworking jobs need revisions, alternates (e.g. species or finish options), change orders and a closeout ledger, or a simpler accept-and-invoice flow?
- Drawings or renderings attached to the proposal?
- Deposit and payment schedule for furniture (e.g. 50 percent to order materials, balance on delivery)?
- Numbering: separate sequence or prefix (e.g. W26001), or one shared sequence?
- Terms: lead time, wood movement and natural variation, finish care, delivery and installation, cancellation after materials are ordered.
- Should a GC project be able to include a woodworking proposal (cabinets for a remodel), or stay separate?
