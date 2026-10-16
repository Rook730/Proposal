# Proposal Builder: Requirements Spec

Version 1.0 | 2026-10-15 | Owner: Nick (Kept Spec Advisors)
All open questions are resolved. Section 15 records the assumptions made.

## 1. Purpose and success criteria

Replace the Excel proposal workflow (Proposal_Template4.xlsx) with a standalone Windows application.

- Build a typical renovation proposal in about 20 minutes, down from about 3 hours.
- **Acceptance test:** rebuild proposal 26005 (Hotch Kitchen).
  - The rebuilt proposal must reproduce: Subtotal $32,818.00, Total $41,186.59, Alternate Subtotal $30,438.00, Alternate Total $38,199.69.
  - The PDF must match the current look.
- Catalog edits never alter a saved proposal.

## 2. Scope

**In scope**
- Catalog management:
  - sections (categories)
  - items
  - rates
  - allowance ranges
  - units
  - stock sizes
  - boilerplate library
- Proposals:
  - revisions
  - 0 to 3 alternates
  - variables (global and per proposal)
  - payment schedule with dollar amounts
  - schedule of values
- Change orders.
- Whole-project reconciliation (final project ledger).
- An internal (non-printing) view.
- PDF export of proposal, change orders, SOV and reconciliation.

**Out of scope**
- Invoicing (handled in another app).
- E-signature.
- Excel/CSV export.
- Multi-user use.
- Lamp restoration catalog items (codes 2000 to 2690).
- Convenient Woodworking (CW) proposal template.

## 3. Platform and architecture

| Topic | Decision |
|---|---|
| OS / users | Windows, single user, single PC, fully offline |
| Language | Python 3.12 |
| UI | NiceGUI in a native window (pywebview). Can also open in a browser tab. |
| PDF engine | Typst via the `typst` Python package. No system dependencies. Gives explicit page-break control (keep-together blocks, repeating table headers, no orphans). |
| Storage | Plain JSON files in a Proton Drive synced folder (one folder per project; catalog and settings files at the root). Sync-safe, human readable, diffable. Issued revisions are write-once files. |
| Packaging | Single Windows .exe built with PyInstaller |
| Source | GitHub repo under Rook730 |

Storage layout (proposed):
```
<Proton Drive>/KeptSpec Proposals/
  settings.json          company info, defaults, global variables, rates
  catalog.json           sections, items, allowance ranges, units, stock sizes
  boilerplate.json       clause library
  projects/26005_Hotch_Kitchen/
    project.json         client, address, status
    rev_1.0.json         issued revisions are locked
    rev_1.1.json
    co_26005-01.json
    reconciliation.json
    pdf/                 exported PDFs
  backups/               automatic timestamped copies
```

## 4. Data model

### 4.1 Settings (global)
- Company: legal name (Convenient Enterprises LLC), DBA (Kept Spec Advisors), address, phone, email, logo.
- Proposal numbering: YYNNN (26005), auto-increment.
- Default percent items and rates (see 5.3).
- Default boilerplate selection.
- Global variables (see 4.8).

### 4.2 Units
These are imported from the Definitions tab: DY, EA, HR, LF, LS, MO, SF, TON, WK. PR (pair) is used in the Allowances tab, so it is added. The list is editable, and the unit definitions table in the proposal prints from it.

### 4.3 Rate table
Each rate has a code, a name, a unit and a rate. Catalog items and proposal lines reference a rate instead of typing a price. When a rate changes, catalog items that reference it change too; existing proposals keep their snapshot (see 4.9).

Rates derived from the current catalog and 26005:

| Rate | $/HR | Current use |
|---|---|---|
| Project management | 75 | 210 |
| Pre-construction / admin / inspections | 60 | 220, 230, 240 |
| Client meetings / punchlist / as-built | 75 | 250, 1210, 1230 |
| Protection labor | 45 | 310 |
| Cleanup labor | 35 | 330, 340 |
| Demolition labor | 50 | 510 |
| Convenient Woodworking trade labor | 75 | 616, 626, 636, 860, 920, 941, 1150 in 26005 |
| Electrical / plumbing labor (catalog) | 95 | 626, 636 |
| Doors/frames labor | 50 | 820 |
| Fixtures labor | 45 | 1150 (catalog) |

### 4.4 Sections (categories)
Each section has a number (100, 200 ... 1400), a name, a print order and a short key. Sections can be added, renamed and reordered. A proposal includes an ordered subset of sections, set per proposal.

### 4.5 Catalog items
- **Code:** unique in the catalog.
- **Section.**
- **Title.**
- **General description:** fixed text, printed on every line that uses the item.
- **Unit.**
- **Price source**, one of:
  - fixed price
  - rate reference
  - allowance range reference
  - percent of subtotal
- **Default performer.**
- **Stock sizes** for quantity rounding (see 5.5).
- **Flags:**
  - percent item
  - allowance
  - "not included" ($0 scope line)
  - owner-furnished
  - credit-if-unused (contingency, CO management, painting sub)
- **Internal notes.**

### 4.6 Allowance ranges
Each range has a category, a description, a unit, low and high values, and a basis note (e.g., "Material only"). Mid is computed as (low + high) / 2. A range is linked to one or more catalog items. On a proposal line, pick Low, Mid or High, or override the price.

### 4.7 Boilerplate library
Blocks are grouped under headings. Each block has a default on/off state, can use variables, and can be edited per proposal; per-proposal edits are snapshotted with the revision.

| Heading | Blocks (each toggleable) |
|---|---|
| Intro | Cover letter, Cost-plus reminder |
| How to read this proposal | Sections, Units table, Hourly, Allowances, Who performs, $0 lines, Gray lines, Blue lines, Exclusions note |
| Totals | Alternate note |
| Payment Schedule | Contract Execution/Mobilization, Construction Progress Payments, Allowances & Change Orders, Substantial Completion, Final Payment |
| Payment Terms & Contract Cancellation | Payment Schedule, Labor/Management/Time-Based Services, Contract Cancellation or Termination, Materials and Special Orders, Net Refund Calculation |
| Scope Clarifications & Exclusions | Exclusions, Concealed Conditions, Owner-Furnished Items, Allowances, Schedule/Lead Times/Selections, Room Availability, Owner Responsibilities, Lead-Based Paint, Warranty, Contracting Parties, Proposal Validity |
| Signature | Acknowledgement + signature boxes |

The Exclusions block is a checklist of library bullets plus free text. Example bullet: "Make-up air for the range hood (hood limited to {hood_cfm} CFM)".

### 4.8 Variables
- **Scope:** global (company info, payment percentages, validity days, tax rate) and per proposal (pull count, duct length, hood CFM, crown LF, countertop SF, working weeks, etc.).
- **Fields:** name, value, unit.
- **Use:**
  - Referenced in any text as `{name}`.
  - Can be bound to a line's quantity or price.
- **Editing:** changing a variable once updates every text and bound field.
- **Checks:** undefined references and unused variables are flagged.

### 4.9 Project, proposal revision, lines

**Project**
- Number (26005)
- Client name(s), site address, project name
- Status: Draft, Presented, Accepted, Rejected, In-Process, Completed (replaces the Tracking tab)

**Revision**
- Numbering:
  - 1.0, 1.1, 1.2 ... are revisions issued before acceptance.
  - 2.0 is the final revision, created once the client has chosen (Finalize). It is base only: the alternates the client selected are merged into the base, and the rest are removed. It is issued for signature; 2.1, 2.2 ... are allowed if it needs another pass before signing.
  - Mark accepted records the signature on the latest issued 2.x. After acceptance, scope changes go through change orders only.
- Date.
- State: Draft, Issued, Accepted, Superseded. Issuing a revision locks it; editing after that creates the next revision.
- Included sections (ordered).
- Variables.
- Boilerplate selection and edits.

**Line**
- Line ID: section number plus sequence, e.g. 11.04. IDs never renumber once a revision is issued; a deleted ID is retired and new lines take the next number.
- Catalog code
- Title
- General description: snapshot from the catalog, read-only on the line
- Detail notes: Markdown with variables, for assumptions, locations and specifics
- Performer. The client PDF shows one of: Kept Spec Advisors, Convenient Woodworking, Licensed Sub, Client (owner-furnished). The actual sub name is stored internally.
- Unit
- Quantity: typed, bound to a variable, or computed from a takeoff with stock rounding
- Price source and price
- Cost
- Alternate membership
- Internal fields (see 10)

**Snapshot rule.** Adding a catalog item to a proposal copies all of its fields into the line. Later catalog edits do not change the line. When the line differs from the current catalog, it shows an indicator with a "pull update" action.

**Alternates**
- 0 to 3 per revision.
- An alternate is a set of operations of three kinds:
  - swap: remove base lines, add lines
  - add: lines added only
  - deduct: base lines removed only
- Alternates can be combined.
- Each alternate prints its own net change (percent items included) and the total with that alternate. Combined totals are additive.
- An optional table can print every combination.
- Two alternates that touch the same base line are flagged as mutually exclusive.
- Alternate lines print blue.

## 5. Calculations

1. Line cost = qty x unit price, rounded to cents.
2. Subtotal = sum of all base lines that are not percent items.
3. Each percent item = its rate x Subtotal. All are flat on the subtotal, with no compounding. Current set:
   - Builder's risk 0.5%
   - Contingency 5%
   - CO management 5%
   - Overhead 5%
   - Profit 10%

   That is 25.5% in total.
4. Total = Subtotal + sum of percent items.
5. Each alternate:
   - Alternate subtotal = Subtotal minus the removed lines plus the added lines.
   - The percent items are recomputed on the alternate subtotal, giving the alternate total.

   This replaces the hardcoded -606.90 adjustment in 26005 cell J386 (2,380.00 x 25.5%).
6. Section totals are shown excluding and including percent items, where a section contains them.
7. Payment schedule dollars are computed on the base total only. The percentages are held as global variables.
   - Deposit = 25% of Total.
   - Retainage = 5% of Total, due at final.
   - Progress payments = Total minus deposit minus retainage.

### 5.5 Quantity rounding to stock lengths (stick goods only)
- **Stock lengths:** a lookup table of available lengths per material class. Catalog items are linked to a class. The default class is trim, at 8, 10, 12, 16 and 20 ft.
- **Input:** a single takeoff total, e.g. 50 LF.
- **Need** = takeoff x (1 + waste %). The waste % is a global variable (default 10%), with a per-line override.
- **Pick:** the software chooses the combination of stock lengths that covers the need with the least excess. On a tie, it picks fewer pieces.
- **Line quantity** = total purchased LF.
- **Internal view:** shows the piece list and the excess.
- **Detail notes:** the takeoff can optionally print, e.g. "~50 LF incl. waste".

### 5.6 Validation (shown before issue)
- Undefined or unused variables.
- Empty sections.
- Lines priced differently from the catalog.
- Duplicate line IDs.
- Allowance lines priced outside their linked range.
- Alternate references to lines that no longer exist.

## 6. Revisions
- Issuing locks the revision file (write-once), marks earlier issued revisions Superseded, sets the project status to Presented and saves the PDF to the project's pdf folder. Validation results are shown first; errors need an explicit "Issue anyway".
- New revision copies the latest issued one, increments the number and starts as a Draft dated today.
- Finalize (from the latest issued 1.x): choose the alternates the client selected; creates Draft 2.0, base only.
- Mark accepted (latest issued 2.x): state Accepted, project status Accepted, no further revisions.
- Older revisions stay viewable read-only from the revision selector.
- Differences are computed between a revision and the one it was copied from: lines added, removed and changed (qty, unit price, description, performer, section, alternate), section and alternate changes, terms changes, and the change in subtotal and total.
- Every revision after 1.0 can include a client-facing "Changes from Rev X" page in the PDF (on by default, toggle under Terms & options).
- Terms & options also toggles a Schedule of Values summary page (section totals and percent items with % of contract).

## 7. Change orders
Modeled on the 26001 ECN tab.

**Header**
- Proposal #, proposal date, revision, client, address, project.
- CO number in the form {proposal}-{nn}, e.g., 26001-01.
- Requested date.

**Itemized changes**, per item:
- Condition / description.
- Add, Delete or Modify, with the linked proposal line IDs.
- Original cost, final cost, delta.

**Narrative fields**
- SOW modifications: which section/item covers the change.
- Payment impacts.
- Schedule impacts.

**Funding source**
- Contingency.
- Added cost to client.
- Absorbed by Kept Spec.

**Markup**
- CO price = cost delta x (1 + overhead % + profit %). That is 15% at current rates.
- Builder's risk, contingency and CO management do not apply to change orders.
- A CO funded from contingency draws contingency down by the CO price. Any amount beyond the remaining contingency is billed to the client.

**Other**
- Status: Draft, Issued, Approved, Rejected.
- Signature block: Recommended by, Accepted and Approved by (Name / Signature / Date).
- Exports to PDF in the same visual style as the proposal.

**As built (M5)**
- Change orders live in the project's change_orders.json; numbers are {proposal}-{nn}.
- Contingency is drawn in CO number order by approved orders only.
- Approved and rejected orders are read-only; drafts can be deleted.
- Overhead/profit, contingency and CO management are found on the accepted revision by catalog code (Settings: co_markup_codes 1410/1420, contingency_code 1310, co_management_code 1320).

## 8. Schedule of values
- The proposal layout (sections, lines, section totals) serves as the schedule of values. There is no separate SOV document.
- An optional summary page can be toggled on in the proposal. It lists section totals and percent items, each with % of contract.
- Billing happens in the other app.

## 9. Reconciliation (whole project)
Modeled on the 26001 Reconciliation tab and the 26001 side tracking table.

1. **Contract summary**
   - Accepted revision total, including any selected alternate.
   - Allowance amounts.
2. **Approved change orders**
   - Total.
   - Net of contingency used.
3. **Actual costs**, entered per line (no receipt attachments)
   - Fields: vendor/sub, date, amount, tax, paid by (Client direct or Kept Spec).
   - Hourly lines: actual hours x rate.
4. **Variance**
   - Proposed vs actual per line and per section.
   - Allowance variance has OH&P applied to the net variance, per the Allowances clause.
5. **Credits**
   - Unused contingency.
   - CO management when no COs were issued.
   - Any line flagged credit-if-unused (e.g., painting sub).
6. **Payments received**
   - Draw, milestone, date, amount.
7. **Final balance**
   - Total final project cost
   - minus client-direct payments to subs/suppliers
   - minus payments to Kept Spec
   - = balance due.
8. **PDF export** titled "Final Project Ledger", in the same style.

**As built (M5)**
- Line variance applies to every contract line with actual costs entered, or marked Unused (credited in full). Lines without actuals stay at their contract amount; blank entries are ignored.
- Overhead and profit apply to the net line variance.
- Hourly entries may give hours instead of an amount (hours x the line's rate).
- Warnings flag credit-if-unused lines that have no actuals and are not marked unused.

## 10. Internal view
A toggle shows fields that never print:
- Internal notes.
- Vendor / quote reference and quote amount.
- Allowance range and selected tier.
- Takeoff math and stock rounding.
- Hours basis.
- Margin summary (overhead + profit in $ and %).
- Actuals vs proposed.

## 11. PDF output

**Keep the current look**
- Logo header and contact line.
- Proposal #, date and revision block.
- Client / address / project block.
- Section tables with columns Items | Description | Unit | Qty | Unit Price | Cost, with the item code under the title.
- Gray rows for percent items, blue rows for alternates.
- Section total rows and gray divider bars.
- Total Proposed Costs block.
- Signature boxes.
- Page "x of y".
- Letter, portrait.

**Pagination rules**
- A section heading and table header always print with at least the first two lines of the section.
- A line row never splits across pages. The only exception is a description longer than half a page, which may split, and then the table header repeats.
- A section total stays with the last line of its section.
- A boilerplate subheading stays with its first paragraph.
- The signature block and the totals block are never split.

**Other**
- File name: `{number}_{Client}_{Project}_Proposal_V{rev}.pdf`.
- The same template system produces the CO, SOV and Reconciliation PDFs.
- The new layout removes the alignment fault seen in 26005 Millwork, where the 941 cost is misplaced.

## 12. UI

**Projects list**
- Number, client, project, status, latest total.
- New project, copy from an existing project.

**Proposal editor**
- Left: section list. Add, remove and reorder sections for this proposal.
- Center: line grid with inline edit of qty, price, performer and tier. Add, duplicate, delete, move.
- Right: line detail.
  - General description (read-only).
  - Detail notes editor with a variable picker.
  - Pricing source.
  - Internal fields.
- Catalog picker: search by code, title or section; multi-select and add.
- Persistent totals bar: Subtotal, Total, and each alternate total.

**Other proposal screens**
- Variables panel.
- Boilerplate panel: checkbox tree; edit per proposal; reset to library text.
- Live PDF preview.

**Catalog manager**
- Sections, items, rates, allowance ranges, units, stock sizes, boilerplate library.

**Project-level screens**
- Change order editor, SOV view, reconciliation editor.

## 13. Migration
- **Import** Items codes 100 to 1420 (2000+ dropped), Allowances, Definitions, and all boilerplate text from 26005.
- **Fixes at import:**
  - 450 description duplicates 410 ("temporary power").
  - 130 description says "subtotal"; confirm wording.
  - Unit PR added.
  - Placeholder codes with no title are dropped.
- **New catalog items** for allowance categories that had no matching item:

  | Code | Title | Linked allowance category |
  |---|---|---|
  | 1121 | Tile material | Tile |
  | 1141 | Cabinet hardware | Hardware |
  | 1142 | Lighting fixtures | Lighting |
  | 1143 | Plumbing fixtures | Plumbing Fixtures |
  | 1144 | Glass and mirrors | Glass |
  | 1171 | Ventilation equipment | Ventilation |

- **Existing items linked** to allowance categories:

  | Code | Linked allowance category |
  |---|---|
  | 627 | Electrical |
  | 1010 | Flooring |
  | 940 | Millwork |
  | 1110 | Paint |
  | 617 | Ventilation (duct kit) |
- **Test case:** 26005 rebuilt as the first project, used as the regression test.

## 14. Milestones
1. Data model, file storage, catalog manager, Excel import.
2. Proposal editor, calculation engine, variables, snapshot rule. Acceptance: 26005 totals match.
3. PDF engine matching the current look, with pagination rules. Acceptance: 26005 PDF review.
4. Revisions, alternates, boilerplate panel, validation.
5. Change orders, SOV, reconciliation. Acceptance: 26001 rebuilt and its ledger matches.
6. Windows .exe packaging, backups, install notes.

## 15. Assumptions (correct if wrong)
- **Contingency draws:** a contingency-funded CO draws contingency down at CO price (cost + OH&P), not at raw cost.
- **Trim stock lengths:** 8, 10, 12, 16 and 20 ft (12 and 20 added to the original 8/10/16). All lengths are editable in the catalog manager.
- **Rate assignments** in 4.3 are a starting point. Rates and their links to items are editable.
