# Changes

## Released in 1.5.0 (2026-10-19)

Collected until Nick says to release. Status: [ ] open, [x] built, not released, [x] released.

1. [x] Income tab: Kept Spec, Convenient Woodworking and Combined columns with Share of Price, Estimate/Actual toggle. Rows not tied to a performer (overhead, profit, change order management, change order and variance overhead and profit) count as Kept Spec. Income by option shows the split too.
2. [x] Income summary page (left menu): timeframe presets or from/to, status filter (default Accepted, In-Process, Completed, Closed), Estimate/Actual, one row per project with totals, win/loss/open counts and win rate, CSV export (saved to the data folder's exports/ and downloaded). Projects are placed by acceptance date; never-accepted proposals by issue date.
   - Projects now record an acceptance date (Mark accepted, or setting an accepted-type status) and a close date.
   - New status Closed. "Close project" on the change orders & ledger page (warns about balance due and open change orders) makes change orders, costs and payments read-only; Reopen sets Completed.
3. [x] Catalog: Customers. Fields: name, contacts (several: spouse, property manager...), phone/email per contact, mailing address, several addresses (site picked per project from a dropdown), lead source, notes, linked projects. Project picker on New project / Project info. Existing projects (and Excel imports) are linked by matching names; renaming a customer or editing an address updates linked projects. Later: follow-up flags.
4. [x] Catalog: Contractors (company, trades, contact, phone, email, license number/type, insurance expiry, W-9, rating, notes, linked projects/lines). Lines and change order items pick a contractor instead of typing the internal sub name. Insurance expired, expiring within 30 days, or missing shows on the Issues tab (warning once the project is accepted) and on the change order page. Existing typed sub names became contractors.
5. [x] Catalog: Suppliers, own page (name, contact, phone, email, account number, website, notes). Line vendor and actual-cost vendor pick from suppliers and contractors.
6. [x] Sub quote package (Sub quotes tab): PDF of the lines assigned to one contractor (title, description, notes, unit, quantity; no prices; no client name), project number, name and site address in the header; blank price / valid until / lead time / exclusions for the sub to fill in. Text before the scope is in Settings (rfq_note). Export only.
7. [x] Quote comparison (Sub quotes tab): log quotes from several contractors for the same scope; PDF comparison for the client (separate from the proposal). Lowest first; note under the table is in Settings (comparison_note). Winner entered manually on the lines.
8. [x] Projects list: Delete and Archive.
   - Delete (for mistakes and test projects): type the project number to confirm; the folder moves to backups/deleted-projects in the data folder, so it can be recovered. Accepted projects get a note suggesting Archive. Deleting the newest project number hands that number out again.
   - Archive / restore: hides a project from the list (Show archived brings it back); archived projects still count in the income summary and show an Archived badge in the editor.
10. [x] Variance billing (option A, cost-plus): every line is billed at actual cost; overhead and profit apply to the net variance on all lines (the ledger already did this). Terms brought in line: the Scope Clarifications "Allowances" block no longer limits overhead and profit to allowances, and a new "Billing at Actual Cost" block says so. The library updates itself if its Allowances text is unedited; existing proposals use Terms & options (Reset to library text on Allowances, Add from library for Billing at Actual Cost).

## Released in 1.5.2 (2026-10-20)

11. [x] Alternates tab: each alternate has Add from catalog, Custom line and Copy removed lines (copies each base line it removes into the alternate as an editable starting point). New lines open their form right away when one line is added. Lines the alternate adds show as chips: click to edit, x to delete. A custom line starts in the section of the first removed line.
12. [x] Fix: dialogs opened from a panel that refreshes on save (e.g. the line form after adding from the Alternates tab) no longer fail to appear.
13. [x] Settings: Dark mode switch (saved in settings; the page reloads in the chosen theme). Grids, tiles, alternate and percent row colors, banners and buttons all have dark versions.

## Released in 1.6.0 (2026-10-20)

14. [x] Alternates: when an alternate changes owner-supplied items, the alternate card and its tile show the owner-supplied difference (owner-supplied costs are outside the Total Price, so the Total difference alone can read $0).
15. [x] Settings > Lists: edit dropdown choices without code.
   - Performers: name, printed note, and Income (KS, CW or blank). New performers work everywhere (lines, catalog, change order items) and count in the matching Income column; renaming one updates catalog items; old names on saved proposals still print their note.
   - Change order actions, contact roles, how they found you, contractor trades, quote scopes, address labels. "How they found you", trades and the new-address label also accept a typed one-off value.
16. [x] Naming: the "allowance" price basis is shown as "range" everywhere on screen (Basis column, line form, catalog item form and list, catalog picker), and allowance ranges are called price ranges (catalog page "Price ranges", "Price range" picker, "Default range tier"). "Allowance" now only means the flag that prints "Allowance." Saved files are unchanged.
17. [x] Line form: previous / next buttons beside the title, labeled with the neighboring line IDs (same order and section filter as the grid). They grey out as soon as anything in the form changes. "Save" keeps the form open on the saved line (so you can move on); "Save & close" closes it; Cancel asks before discarding unsaved changes.

## Released in 1.6.1 (2026-10-21)

18. [x] Line form shows only the fields that apply.
   - Price basis is a set of buttons (Fixed | Rate | Range | Percent) and the row below shows only that basis's fields: Fixed = unit price (or bind to variable); Rate = rate, price shown read-only "from rate" with an Override button that switches to Fixed; Range = price range + tier, price read-only unless the tier is Custom, with low/mid/high shown; Percent = percent (or variable).
   - Quantity is Typed | Variable | Takeoff (stick goods), showing only that source's fields.
   - Percent lines hide quantity, unit, performer, contractor and the Allowance / Not included / Owner-furnished flags. Not included lines hide quantity and price (saved as 1 x $0).
   - On save, fields that don't apply are cleared (stale tier, rate key, range, variable, takeoff / stock class).
   - Catalog item form: same Price buttons; Price, Rate, or Linked ranges + Default tier shown only for their basis (hidden links are kept).
   - Issues tab: Range basis with no range picked (warning); rate line whose unit differs from the rate's unit; stock class with no takeoff (info).

## Next release

19. [x] Right-click menu in the app window: in text fields and on selected text it shows Edge's spelling suggestions, Add to dictionary, and cut / copy / paste (pywebview had it turned off). Elsewhere right-click does nothing, so Back / Refresh can't drop an open form. Developer tools stay off.
20. [x] Spelling check (Issues tab, offline English dictionary plus trade terms):
   - Checks the printed text: project name, line titles, catalog descriptions, line notes, alternate names and descriptions, terms that are on. Skips words in all capitals (GFCI, LVP), words with inner capitals, {variables}, web and email addresses, unchecked sections and internal notes. Client name and site address are not checked.
   - Each unknown word shows where it is and up to 3 suggestions. Clicking a suggestion replaces the word everywhere in the revision (case kept); a word in a catalog description is also fixed in the catalog item, and a word in the terms is also fixed in the terms library.
   - Add to dictionary accepts a word in every proposal; the list is in Settings > Lists (Spelling dictionary).
   - The Issue dialog lists the count and words; spelling never blocks issuing.
   - Also fixed: long warnings in the Issue dialog no longer push their icon onto a separate line.
