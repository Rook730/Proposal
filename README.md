# Proposal

Proposal builder for Kept Spec Advisors (Convenient Enterprises LLC). Standalone Windows app that replaces the Excel proposal workflow: catalog, proposals with revisions and alternates, change orders, and whole-project reconciliation, exported to PDF.

Requirements: [docs/requirements.md](docs/requirements.md)

## Status

| Milestone | Scope | State |
|---|---|---|
| 1 | Data model, file storage, Excel import, catalog manager | done |
| 2 | Proposal editor, calculations, variables, snapshot rule | next |
| 3 | PDF engine (Typst), pagination rules | |
| 4 | Revisions, alternates, boilerplate per proposal, validation | |
| 5 | Change orders, schedule of values, reconciliation | |
| 6 | Windows .exe packaging | |

## Run on Windows

1. Install Python 3.12 or newer from python.org (check "Add python.exe to PATH").
2. Clone this repo (GitHub Desktop is fine).
3. Double-click `setup.bat` once.
4. Double-click `run.bat`. The app opens in its own window. `run.bat --browser` opens it in a browser tab instead.

On first start the app creates `%USERPROFILE%\KeptSpec Proposals` and fills it with the catalog imported from Proposal_Template4.xlsx. To keep data in Proton Drive, open Settings, paste the Proton Drive folder path under Data folder, and click "Use this folder". An empty folder is seeded automatically.

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
