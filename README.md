# Proposal

Proposal builder for Kept Spec Advisors (Convenient Enterprises LLC). Standalone Windows app that replaces the Excel proposal workflow: catalog, proposals with revisions and alternates, change orders, and whole-project reconciliation, exported to PDF.

Requirements: [docs/requirements.md](docs/requirements.md)

## Status

| Milestone | Scope | State |
|---|---|---|
| 1 | Data model, file storage, Excel import, catalog manager | done |
| 2 | Proposal editor, calculations, variables, snapshot rule | done |
| 3 | PDF engine (Typst), pagination rules | done |
| 4 | Revisions, alternates, boilerplate per proposal, validation | done |
| 5 | Change orders, reconciliation | next |
| 6 | Windows .exe packaging | |

## Run on Windows

1. Install Python 3.12 or newer from python.org (check "Add python.exe to PATH").
2. Clone this repo (GitHub Desktop is fine).
3. Double-click `setup.bat` once.
4. Double-click `run.bat`. The app opens in its own window. `run.bat --browser` opens it in a browser tab instead.

On first start the app creates `%USERPROFILE%\KeptSpec Proposals` and fills it with the catalog imported from Proposal_Template4.xlsx. To keep data in Proton Drive, open Settings, paste the Proton Drive folder path under Data folder, and click "Use this folder". An empty folder is seeded automatically.

## Using it

- **Projects**: New project starts blank (percent items only) or as a copy of an existing project. "Import from Excel" converts a proposal sheet from the old workbook (e.g. "26005 Proposal").
- **Editor**: tick sections on the left (order arrows set print order), add lines from the catalog, edit title, performer, unit, qty and price in the grid, double-click an ID, notes or cost cell for the full line form.
- **Line form**: detail notes with {variables}, quantity bound to a variable or computed from a takeoff and stock lengths, price from a rate, allowance tier, fixed value or variable, flags, internal fields, and "Pull update" when the catalog changed.
- **Variables** tab: per-proposal values; every {name} and bound field updates when a value changes.
- **Alternates** tab: up to 3; each removes base lines and/or adds lines assigned to it.
- **Terms & options** tab: this proposal's copy of the boilerplate (toggle, edit, reorder, reset to library, add from library or custom), plus page options (Changes page, Schedule of Values page).
- **Issues** tab: undefined variables, excluded lines, catalog changes, unused variables, zero quantities, missing prices.
- **Revisions**: Issue Rev locks the draft and saves its PDF. New revision copies it (1.0, 1.1, ...). Finalize creates 2.0 with the client's chosen alternates merged; issue it for signature, then Mark accepted. Older revisions open read-only from the Revision selector.
- **Preview / Export PDF** (editor header): preview renders every page in the app; Export writes `projects/<project>/pdf/<number>_<client>_<project>_Proposal_V<rev>.pdf` and offers to open it.
  Boilerplate can also use `{total_price}`, `{subtotal}`, `{deposit_amount}`, `{progress_amount}` and `{retainage_amount}`.

Every edit saves immediately to the data folder; previous versions go to `backups/`.

## Re-import from Excel

```
.venv\Scripts\python -m proposal_builder.importer "C:\path\Proposal_Template4.xlsx" --out "C:\path\to\data folder"
```

This overwrites catalog.json, settings.json and boilerplate.json in that folder.

## Development

```
python -m pytest -q
python -m proposal_builder --browser --data ./devdata
```
