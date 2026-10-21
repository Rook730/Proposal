# UX review (2026-10-21, v1.6.2)

Reviewed every page, tab and dialog at 1400x900 (the app window) and 1280x720, light and dark, on a copy of the 26005 data plus an older accepted copy for change orders and the ledger.

## Design language

- Material Design through Quasar (NiceGUI). Roboto in the app, Carlito in PDFs.
- Navy app bar with the page name and version on the right. Left nav with two groups (Proposals, Catalog). The editor and the change order page hide the nav and use a back arrow.
- Buttons in Quasar's uppercase default: filled navy for primary, outlined for secondary, flat for tertiary, red for destructive, green for Approve. Toolbars use icon-only buttons with tooltips.
- AG Grid for nearly every list. Quasar tables for read-only summaries (Income, Variables in effect).
- KPI tiles: small uppercase label, large navy value, gray sub-line. Used on the editor, Income summary and change orders.
- Underlined inputs with floating labels, dense. Segmented toggles for modes (price basis, quantity source, Estimate / Actual). Checkboxes for flags, chips for lists.
- Gray helper text under most headings.
- Expansion panels for grouped text (terms, boilerplate, income detail).
- Color meaning: red for errors, delete, threshold and balance due; orange for warnings; blue for info; tinted rows for alternates (blue) and percent items (gray).
- Editing happens in dialogs with Save. Grid cells and Settings save instantly.

## Bugs found

1. Project info does not open on 26005. The project's customer_id (c06e347b5b) is not in customers.json, so the customer dropdown rejects the value and the dialog never appears. The customer also shows 0 projects, and the Issues check stays silent. Fix: tolerate a missing customer, relink by name, and add an Issues warning.
2. Records are created before Save. Custom line, Add row on sub quotes, and New change order write a blank record immediately; Cancel leaves it behind. A cancelled custom line is a "New line" at $0, which now prints as included at no charge.
3. The line form's Save buttons are below the bottom of a 900 px window for most lines; you have to scroll inside the dialog to reach them.
4. Terms & options marks a block "(edited for this proposal)" when the library changed, not the proposal (the $0 block after the 1.6.2 update).

## UX improvements

### Layout and density
5. Editor: the header, tiles and tabs take about 430 px before the first line, leaving about 14 rows at 900 px and 8 at 720 px. Combine the title, revision and totals into one compact sticky bar. Put secondary actions (Project info, Change orders, Export) in a menu. Let the grid fill the rest of the window (today the page and the grid both scroll).
6. Line form: replace the 20 variable chips with an "Insert variable" dropdown, or offer suggestions when you type {. Hide the Preview box when there are no notes.
7. Wide grids cut off columns (catalog Flags; contractors W-9 and Rating) and some have unlabeled columns (customers, contractors, suppliers). Fix widths, label everything, and hide rarely used columns behind a column chooser.

### Consistency
8. Two editing patterns: dialog forms (items, customers, contractors) and inline grids (sections, rates, ranges, units, stock, suppliers, quotes, change order items). Suppliers is inline while contractors uses a dialog. Rule: a dialog for records with more than about five fields, inline for short lookup lists.
9. Page frames differ. Some pages have a title (Customers, Income summary) and catalog pages do not. The filter sits beside the buttons on some pages and below on others, with different placeholder text. Use one frame for every list page: title, one-line help, toolbar, filter, grid.
10. Delete selected is a red button that is always enabled. Disable it until rows are selected.
11. Formats. Editable grids show 75, 6.5 and 0 instead of $75.00. Dates appear four ways: 2026.10.20 (header), 2026-10-19 (grids), mm/dd/yyyy (pickers), and typed YYYY-MM-DD (change order). Use one date format and a date picker everywhere; format money in every grid.
12. Terms. Source / Basis / Price all mean the price basis. Boilerplate (nav) and Terms & options (editor) mean the same text. Performer vs Performed by. The price ranges "Basis" column (Material only, Installed) clashes with price basis; rename it "Includes". The Catalog nav group holds Customers, Contractors, Suppliers and Settings: split it into Catalog, Contacts, Settings.
13. Uppercase buttons are loud and wide. Use sentence case everywhere (already used on toggles).
14. Project status can be set by hand and disagree with the revision (status Presented while Rev 1.2 is Draft). Derive status from the revision workflow and allow only Lost / Closed / Archived by hand.

### Workflow and feedback
15. Lines grid: "Double-click ID, notes or cost to open; other cells edit in place" is a hidden rule. Make double-click anywhere or Enter open the form, and keep in-place edits for a few columns with a visible cue.
16. The icon toolbar (edit, duplicate, up, down, delete) needs a selected row and gives no hint. Add a right-click menu on rows and keyboard shortcuts: Ctrl+S save, Ctrl+Enter save and close, Delete, Ctrl+D duplicate, Alt+Up / Alt+Down to move.
17. No undo. Add Undo on the toast after a delete, a spelling fix-everywhere (it also touches the catalog and library), or a section toggle.
18. Silent autosave. Grids and Settings save without feedback. Show a small "Saved" indicator in the app bar.
19. Empty states. Sub quotes shows an empty contractor list with Preview and Export enabled. Suppliers shows AG Grid's "No Rows To Show". Change orders before acceptance shows text with no way forward. Each should say what to do and offer the button.
20. Read-only revisions still show section checkboxes and arrows that look active. Grey them out.
21. Change orders before any work: Final cost ($36,480.68) is below the contract and Balance due is red, because unused contingency and change order management are credited up front. Label it "Projected final cost" and keep Balance due neutral until something is invoiced.
22. Change order dialog footer has 9 buttons. Put Delete on the left, Preview and Export together, then Cancel, Save and one status button for the next step (Mark issued, then Approve or Reject).
23. Settings is one long page mixing company, numbering, money defaults, appearance, RFQ text, data folder, backups, updates, lists and variables. Split into tabs. Two labels are truncated. Add % and $ markers to the number fields.
24. Import from Excel: the Sheet dropdown sits above the upload and stays disabled, and the uploader shows "0.0B / 0.00%". Upload first, then pick the sheet.
25. New records start with placeholder values typed in ("New contractor", "New line", "Alternate 1") that you must delete. Start blank with a hint.
26. Dark mode: primary buttons are white text on light blue, low contrast.
27. Issues tab: show a count badge. The Issues tile counts only calculation errors.
