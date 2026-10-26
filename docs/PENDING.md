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

## Released in 1.6.2 (2026-10-21)

19. [x] Right-click menu in the app window: in text fields and on selected text it shows Edge's spelling suggestions, Add to dictionary, and cut / copy / paste (pywebview had it turned off). Elsewhere right-click does nothing, so Back / Refresh can't drop an open form. Developer tools stay off.
20. [x] Spelling check (Issues tab, offline English dictionary plus trade terms):
   - Checks the printed text: project name, line titles, catalog descriptions, line notes, alternate names and descriptions, terms that are on. Skips words in all capitals (GFCI, LVP), words with inner capitals, {variables}, web and email addresses, unchecked sections and internal notes. Client name and site address are not checked.
   - Each unknown word shows where it is and up to 3 suggestions. Clicking a suggestion replaces the word everywhere in the revision (case kept); a word in a catalog description is also fixed in the catalog item, and a word in the terms is also fixed in the terms library.
   - Add to dictionary accepts a word in every proposal; the list is in Settings > Lists (Spelling dictionary).
   - The Issue dialog lists the count and words; spelling never blocks issuing.
   - Also fixed: long warnings in the Issue dialog no longer push their icon onto a separate line.
21. [x] More Issues checks (also listed in the Issue dialog):
   - Placeholders left in printed text or variable values: TBD, TBA, TODO, XX / XXX, ??, [ ] (warning).
   - Allowance wording: description starts with "Allowance" while the Allowance flag is on (prints twice), or the line is worded as an allowance with the flag off (info).
   - Lines added twice: same title and notes in one section and alternate (warning). Same catalog item with different notes is not flagged.
   - Project info: blank client name or site address (warning); not linked to a customer, or the customer has no contact with a phone or email (info).
22. [x] $0 lines are included at no charge.
   - Terms block "$0 and owner-supplied lines" is now "Not included, $0 and owner-supplied lines": a line marked Not included is work outside this proposal; a line with a $0 cost (shown as $ -) is included at no charge. The library updates itself if that block is unedited; existing proposals use Terms & options > Reset to library text on that block.
   - Lines marked Not included print "Not included" in the Cost column instead of $ -.

## Released in 1.7.0 (2026-10-21)

UX review items (numbers from docs/ux-review.md):

23. [x] (3) Line form: header and Save / Save & close / Cancel stay in view; the form between them scrolls.
24. [x] (4) Terms & options: each block knows the library text it was copied from. Labels: "edited for this proposal", "library text updated since; open it and Reset to library text to use it" (orange), or both. The group heading counts library updates. Proposals copied before this version are recognised from the replaced library texts (e.g. the $0 block).
25. [x] (5) Editor: one compact header row (back, title, revision, state, date, status, Preview, Issue, and a menu with Project info, Export PDF, Change orders & ledger); totals in one strip; the lines grid and sections panel fill the window. About 16 lines show at 900 px (was about 14 with page scrolling, 8 at 720 px).
26. [x] (8) Suppliers: list plus a form like Contractors (was edited in the grid).
27. [x] (9) Same frame on every list page: title, one line of help, toolbar with the main button and filter, grid. Projects gets a filter; Archive / restore and Delete enable once a project is selected.
28. [x] (10) Delete selected stays disabled until rows are ticked.
29. [x] (11) Dates show as 2026.10.20 everywhere (header, grids, lists). Every date field has a calendar picker: project date, change order requested date, insurance expiry, income summary From / To, and date cells in grids (double-click opens the calendar). Typed dates accept 2026.10.20, 2026-10-20, 10/20/2026 or 10/20. Money in every grid shows as $1,234.00 (rates, price ranges, quotes, change order items, actual costs, payments).
30. [x] (12) Terminology: "Basis" everywhere for Fixed / Rate / Range / Percent (catalog list, catalog picker, item and line forms; values capitalised); "Terms library" in the menu (was Boilerplate); change order items say Performer; the price range column "Basis" is now "Includes". Menu groups: Proposals / Catalog / Contacts / Settings.
31. [x] (18) "Saved 6:41 PM" in the top bar after every write to the data folder.
32. [x] (19) Empty states say what to do: every grid has its own message; Sub quotes explains how to assign a contractor (request controls hidden until one is) and when the comparison becomes available; Change orders before acceptance has an Open the proposal button.
33. [x] (20) Read-only revisions: the sections panel shows a print / not printed icon instead of checkboxes and arrows.
34. [x] (21) Change orders page: "Projected final cost" (if nothing else changes); Balance due stays neutral until a payment is received or the project is closed.
35. [x] (22) Change order form footer: Delete on the left, Preview and Export together, then Cancel, Save and one button for the next step (Mark issued, or Approve) with the other outcomes in its menu.
36. [x] (23) Settings in tabs: Company, Proposals, Sub quotes, Lists, Variables, App and data. % / $ / days markers on number fields; the two cut-off labels are shorter with help text below.
37. [x] (25) New contractor, customer, supplier, custom line and alternate start blank with an example hint instead of "New contractor", "New line", "Alternate 1".
38. [x] (26) Dark mode: primary buttons are a mid blue with white text (was white on light blue).
39. [x] (27) Issues tab shows a count badge (red with errors, orange with warnings); the totals strip shows "N errors, N warnings" and opens the Issues tab when clicked.
40. [x] Custom line and New change order create nothing until Save; Cancel leaves no blank line or draft behind.

## Released in 1.7.1 (2026-10-21)

41. [x] Issues tab: double-click an issue, or use the button on its right, to open where it is fixed: the line's form (Open line 8.01), the terms block, the Variables or Alternates tab, the section in the Lines tab, Project info, or the customer or contractor form.

## Released in 1.7.2 (2026-10-22)

42. [x] Alternates tab > Combinations: a switch per pair of alternates, "Offer Alt 1 + Alt 2 together" (on by default). Off: the combination drops out of the totals strip, the proposal's Total Price lines, Income by option and the license check, and Finalize won't accept both. Pairs that remove the same base line show as "cannot be combined" as before.

## Released in 1.8.0 (2026-10-25)

Convenient Woodworking proposals, stages 1 and 2 (spec: docs/cw-requirements.md). Kept Spec proposals are unchanged.

Stage 1: company profiles and rename

43. [x] Company profiles: every project belongs to Kept Spec Advisors or Convenient Woodworking. New project asks which company (no default, cannot be changed later); Start from lists only that company's projects. Projects saved before this version are Kept Spec.
44. [x] Settings and Terms library have a Company switch. Company, Proposals (payment, validity, license warning), Sub quotes and Variables are per company; numbering (one sequence for both), stick goods waste, Lists, performers, the spelling dictionary and App and data are shared.
45. [x] Data folder: Kept Spec files stay where they are (settings.json, boilerplate.json); Convenient Woodworking gets profiles/cw/settings.json, profiles/cw/boilerplate.json and profiles/cw/logo.svg, created on first start. No files are moved, so an older copy of the app still opens the folder. Backups of profile files are named profiles_cw_settings.<time>.json.
46. [x] Shared catalog: each section has a Company (KS, CW, KS and CW) on the Sections page; the catalog items list shows it. The editor's sections panel, Add from catalog, the line form's catalog code and section lists, and a blank new project's percent items only offer the project's company's sections. Existing sections are KS.
47. [x] Editor, change orders page, PDFs, income and the projects list use the project's company settings and terms. The editor header shows the company. Convenient Woodworking starts with its identity (Convenient Enterprises LLC dba Convenient Woodworking, 224 Rutledge Rd, Nick@ConvenientWoodworking.com), the textmark logo in dark gold #A87B20 and black, and a starter terms library (cover letter, about, How to read, signature). Payment terms, tax and the CW layout come in stage 2.
48. [x] PDF logos can be SVG (kept as vector in the PDF). Consecutive intro blocks print as separate paragraphs.
49. [x] Renamed to Proposal Builder: window title, top bar, exe ("Proposal Builder.exe"), folder zip, updater User-Agent. The settings folder moves from %APPDATA%\KeptSpecProposal to %APPDATA%\ProposalBuilder (copied once; the old one is left). The in-app updater still finds the renamed exe; an existing install keeps its own file name.

Stage 2: Convenient Woodworking proposals

50. [x] Build sheets: a line priced Built gets its unit price from an internal build sheet (never printed): materials (lumber parts at finished size become board feet at nominal thickness x yield, sheet goods, dimensional, hardware, finish SF x coats, outsourced, typed rows), labor hours by phase, setup rows counted once per line, cost x (1 + overhead + profit), unit price rounded up to $5. The sheet keeps its own copy of the policy and of every unit cost; Pull prices refreshes them. Summary shows cost, overhead, profit, line total, per-shop-hour figure and the price for 1.
51. [x] Price references (Catalog > Price references): lumber ($/BF by species and nominal), sheet goods, dimensional, hardware, finishes ($/SF per coat from container price and coverage) and outsourced services, each with supplier, price date and notes. Seeded from Costing.xlsx (pressure-treated prices that look swapped are noted), plus Ringsend 1/2" prefinished maple at $118.
52. [x] Settings > Proposals (Convenient Woodworking): shop rate $75, overhead 15%, profit 10% (placeholder), round up to $5, yield low/medium/high 1.25/1.5/1.8, rough thickness map, labor phases; deposit rule (60%, or 25% under $500; balance at delivery or completion of installation); sales tax counties (Buncombe, Haywood and Madison 7.00%, Henderson 6.75%) and "new proposals charge sales tax".
53. [x] Pieces: New piece in the sections panel creates a section for one piece (table, cabinet, box) in this proposal; pieces print first, then Delivery & Installation. Add from catalog puts items into the piece being viewed.
54. [x] Rush fee and sales tax per revision (Terms & options): rush % of the subtotal and the delivery county; the rate is copied into the revision. Totals, every alternate and change orders include them; the totals strip shows Rush, Sales tax and Deposit/balance.
55. [x] Catalog additions (applied once to existing catalogs): units BF, SHT, PC, SET, MI; rates cw_shop $75/HR, cw_drive $35/HR, cw_mileage $0.725/MI; sections 3000 Delivery & Installation (Delivery, Mileage beyond the local area, Drive time beyond the local area, Installation, Crating) and 3100 Shop-built pieces with template 3101 Square box 12 x 12 x 10 (the Borg Warner box: 10 at $305, placeholder hardware prices).
56. [x] Save as template (line form, Built lines): adds the line to Shop-built pieces with a copy of its build sheet. Catalog items priced Built have a template build sheet button.
57. [x] Convenient Woodworking PDF: client signature only; totals Subtotal, Rush fee, Sales tax (county, rate), Total Price, then the same for each alternate; Payment Schedule table with deposit and balance; terms groups run on without a page break each; Attn: and PO # in the client block.
58. [x] Starter terms library for Convenient Woodworking (draft for Nick to edit): How to read (pieces, fixed prices, hourly lines, rush and tax, $0 lines, alternates), Payment Schedule (deposit, balance, payment methods and the 3% PayPal/Venmo fee), Payment Terms & Cancellation (materials + hours + 15%, no returns, changes after acceptance), Terms & Conditions (lead time, rush, delivery and installation, crating and freight, natural variation, wood movement and care, warranty, contracting parties, validity).
59. [x] Customers can be a Company: proposals print the company with Attn: its first contact (editable in Project info, with a PO number).
60. [x] Income for Convenient Woodworking projects: line totals less build sheet materials and outsourced work, plus the rush fee; tax passes through. Change orders on Convenient Woodworking contracts: cost change x (1 + overhead + profit) plus sales tax.
61. [x] Issues: sales tax on with no county, no-tax note, Built line with an empty build sheet, build sheet lumber priced for another thickness, materials with no cost. Woodworking words added to the spelling list.

## Released in 1.9.0 (2026-10-26)

Convenient Woodworking, stage 3 (docs/cw-requirements.md section 15).

62. [x] Restoration items from the Items sheet (2000 to 2690) added to the catalog once, as Convenient Woodworking sections: Assessment & Documentation, Metalcraft, Woodcraft, Glasscraft, Electrical, Allowances. Prices from 26003 / 26004 where they had one; Fabricate and the Restore items with no price are left blank (price per job). 2620 White glove installation and 2630 Installation - exterior join 3000 Delivery & Installation; 2610 is covered by 3010 Delivery. Qty is the fixture count.
63. [x] Appendix images (Terms & options): add PNG, JPG, GIF or SVG files; each gets a caption and the piece or section it shows, and can be reordered or removed. They print after the terms, two per row. Photos are scaled to 2000 px on the long side (camera rotation applied) and saved in the project's images folder, which the app never changes, so issued revisions keep their pictures. Both companies.
64. [x] Client property (Project info, Convenient Woodworking): date received and condition when received (internal; {property_received} is available as a variable).
65. [x] Storage of client property: Settings > Proposals (Convenient Woodworking) rate per SF per month ($2.00), minimum per month ($25), free days after notice (15). New terms block "Client property in our care" (Terms & Conditions) uses them; added once to existing Convenient Woodworking libraries.
66. [x] Veneer: Price references > Veneer ($/SF by species and thickness); build sheet material kind Veneer, square feet from pieces x W x L x yield.
67. [x] Up to 6 alternates (both companies), with three more colors on screen and in the PDF. Offer all together / Offer none together buttons; on Convenient Woodworking proposals a new alternate starts as one-or-the-other with the existing ones. Issues warns when more than 8 combinations would print. Alternates that replace the same line are an info note now, not a warning.
68. [x] Placeholders (TBD, XX, ??, [ ]) and printed lines with no unit price are errors and block Issue for both companies: the Issue dialog lists them and the Issue button is disabled. A line included at no charge needs $0.
69. [x] Pillow added (image scaling); the self-test scales and prints an image so the Windows build checks it.

## Next release

(nothing yet)

Open values: profit percent (10% placeholder), real McMaster prices for the square box template, actual hours (stage 4, calibration).