# Proposal

Proposal Builder for Kept Spec Advisors and Convenient Woodworking (Convenient Enterprises LLC). Standalone Windows app that replaces the Excel proposal workflow: catalog, proposals with revisions and alternates, change orders, and whole-project reconciliation, exported to PDF.

Requirements: [docs/requirements.md](docs/requirements.md)

## Status

| Milestone | Scope | State |
|---|---|---|
| 1 | Data model, file storage, Excel import, catalog manager | done |
| 2 | Proposal editor, calculations, variables, snapshot rule | done |
| 3 | PDF engine (Typst), pagination rules | done |
| 4 | Revisions, alternates, boilerplate per proposal, validation | done |
| 5 | Change orders, reconciliation | done |
| 6 | Windows .exe packaging | done |

## Install on Windows

1. Open the repo's **Releases** page and download `Proposal Builder.exe` from the latest release.
2. Put it wherever you like (Desktop, or a folder such as `C:\Users\<you>\Apps`) and double-click it.
3. Windows may say "Windows protected your PC" (the app is not code-signed): **More info**, then **Run anyway**.
4. First run: Settings, Data folder, paste your Proton Drive folder path, click "Use this folder". The setting is kept in `%APPDATA%\ProposalBuilder\config.json` (copied once from `%APPDATA%\KeptSpecProposal` when upgrading from an older version), so updates keep it.

The first start takes 10 to 20 seconds while the single file unpacks. If that is too slow, or antivirus objects, use `Proposal-Builder-folder.zip` from the same release: unzip it and run the `.exe` inside.

**Update**: download the newer `.exe` and replace the old one. Data lives in your data folder, not next to the program.

**Backups**: every save keeps the previous version in `backups/` inside the data folder. Settings, "Create full backup (.zip)" zips the whole data folder.

**Check an install**: `"Proposal Builder.exe" --self-test` writes `selftest.log` next to the exe (data folder, calculation, PDF output).

### Building a release

Push a version tag (`git tag v1.0.1 && git push origin v1.0.1`). The GitHub Actions workflow `build-windows.yml` runs the tests on Windows, builds the one-file exe and the folder zip with PyInstaller, self-tests both, and attaches them to a GitHub release. To build locally on Windows: `pip install -e .[native] pyinstaller`, then `python packaging/build.py`.

### Running from source (development)

`setup.bat` once (needs Python 3.13 or 3.12), then `run.bat` (`run.bat --browser` for a browser tab).

## Using it

- **Companies**: every project belongs to Kept Spec Advisors or Convenient Woodworking (picked at New project, never changed). The catalog is shared and each section says which company uses it; Settings and the Terms library have a Company switch.
- **Convenient Woodworking**: New piece (sections panel) for each table, cabinet or box; lines priced Built open a build sheet (materials from Catalog > Price references, hours by phase, overhead, profit, rounding). Save as template reuses a piece. Rush fee and sales tax county are under Terms & options; the deposit rule and tax counties under Settings > Proposals.
- **Projects**: New project starts blank (Kept Spec: percent items only) or as a copy of an existing project of the same company. "Import from Excel" converts a proposal sheet from the old workbook (e.g. "26005 Proposal").
- **Editor**: tick sections on the left (order arrows set print order), add lines from the catalog, edit title, performer, unit, qty and price in the grid, double-click an ID, notes or cost cell for the full line form.
- **Line form**: detail notes with {variables}, quantity bound to a variable or computed from a takeoff and stock lengths, price from a rate, allowance tier, fixed value or variable, flags, internal fields, and "Pull update" when the catalog changed.
- **Variables** tab: per-proposal values; every {name} and bound field updates when a value changes.
- **Alternates** tab: up to 6; each removes base lines and/or adds lines assigned to it.
- **Terms & options** tab: appendix images (renderings, drawings, photos with captions), this proposal's copy of the boilerplate (toggle, edit, reorder, reset to library, add from library or custom), plus page options (Changes page, Schedule of Values page).
- **Issues** tab: undefined variables, excluded lines, catalog changes, unused variables, zero quantities, missing prices. Placeholders (TBD, XX) and unpriced lines block Issue.
- **Revisions**: Issue Rev locks the draft and saves its PDF. New revision copies it (1.0, 1.1, ...). Finalize creates 2.0 with the client's chosen alternates merged; issue it for signature, then Mark accepted. Older revisions open read-only from the Revision selector.
- **Preview / Export PDF** (editor header): preview renders every page in the app; Export writes `projects/<project>/pdf/<number>_<client>_<project>_Proposal_V<rev>.pdf` and offers to open it.
  Boilerplate can also use `{total_price}`, `{subtotal}`, `{deposit_amount}`, `{progress_amount}` and `{retainage_amount}`.

- **Change orders & ledger** (editor header, needs an accepted revision):
  - Change orders: itemized changes at direct cost (original and final), funding (client, contingency or absorbed), management hours, SOW / payment / schedule impacts, Approve or Reject, PDF. Price = cost change x (1 + overhead % + profit %); contingency-funded orders draw contingency at price and any overflow is billed. Management hours x the contract PM rate are drawn from the change order management allowance (1320); time beyond it is billed at the rate.
  - Actual costs: entries per line (amount + tax, or hours x the line rate), paid by Kept Spec or by the client directly; tick Unused to credit a line in full.
  - Payments: draws received.
  - Ledger: original contract + change orders billed + net line variance + overhead and profit on the variance - unused contingency - unused change order management = final cost; less client-direct costs and payments = balance due. Exports the Final Project Ledger PDF.

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
