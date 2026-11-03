# Convenient Enterprises (engineering) profile: requirements draft

Version 0.3 | 2026-11-03 | Owner: Nick
Source: intake in the claude.ai Project "Automation Proposal Software" (URS_RFQ Template.docx, URS_Response_Form.docx, URS_RFQ Data workbooks, MGM Proposal_20260828_Rev1.0 and Estimate 2026-02). Open items are in section 15.

## 1. Purpose and scope

Add Convenient Enterprises (CE) engineering proposals to Proposal Builder as a third company profile (`ce`), beside Kept Spec Advisors and Convenient Woodworking.

One proposal model whose depth scales with the job:

| Depth | What it is | Reference |
|---|---|---|
| Letter | Narrative proposal: scope, deliverables, client responsibilities, exclusions, timetable, cost, terms, acceptance | MGM Tandem Jig Phase 1 |
| Detailed | Letter plus hours buildup, hardware BOM, milestone payments, timeline, assumptions | Larger retrofit or controls job |
| URS response | Detailed plus a requirement-by-requirement response to a full spec, Response Form, system description, qualification documents | Turnkey cell against a complete URS/RFQ |

Depth is a preset that turns modules on (section 5). Any module can be turned on by hand, so a Letter proposal can grow into a URS response at the next revision without re-entry.

**Two entry paths**
- **A. Client has no spec.** A requirements intake (Word questionnaire or in-app interview, section 8.3) in plain language builds the URS. The URS can be issued to the client as a URS/RFQ package (usable to buy from any integrator) and CE can quote against it.
- **B. Client provides a complete spec.** Enter it manually (section 8.4), on site or on a call through the in-app interview, or in the entry grid. Then give every requirement a compliance status and build a full-scope proposal plus the Response Form.

**Acceptance tests**
1. Rebuild MGM Proposal Rev 1.0 and Estimate 2026-02:
   - Fixed fee $10,000.00 (80 h x $125).
   - Support estimate $2,956.25 (2.5 h travel x $62.50 + 16 h onsite x $125 + 1 night x $300 + 4 h remote x $125).
   - Option (SISTEMA) $1,000.00, shown outside the base total. Base total $12,956.25; with option $13,956.25. (The Wave estimate puts the option in its Grand Total; this corrects that.)
   - PDF matches the current CE look.
   - MGM predates the CE mileage rule (section 6); the rebuild leaves the mileage line off.
2. Generate URS/RFQ Template Rev 1.0 from the requirement library with no manual edits: same sections and numbering, Response Form and acknowledgement page.
3. Respond to a complete URS: every requirement has a status, and the Response Form lists every Deviate and Clarify item by section number.
4. Time: a Letter proposal like MGM is built in 1 hour or less.

**Out of scope (for now)**
- Invoicing (Wave), e-signature, multi-user, client web portal or hosted forms.
- PE-stamped calculations or certification.
- Parsing prints, CAD or photos (attached for reference only).
- Automatic import of client spec documents (.docx or PDF). Client specs vary too much for a parser to be worth it; they are entered manually (section 8.4).

## 2. Branch, release and data plan

- **Branch** `ce` in Rook730/Proposal. `main` stays the stable app. Merge after stage 1 (see Merge below).
- **Step 0: 1.10.1 on main (forward compatibility).** Today every persisted model uses `extra="forbid"`, so a file saved by the branch build would stop 1.10.0 from reading the folder.
  - Persisted models keep unknown fields on load and write them back on save (not dropped, not rejected).
  - Projects with an unknown profile (`ce`) list with their company and open read-only. No new CE projects.
  - `profiles/ce/` is ignored. Unknown catalog section profiles are kept and hidden.
  - Numbering: unchanged shared YYNNN sequence. Stable picks up the counter the branch build advanced.
  - Tests: load a folder saved by the branch build, edit a KS project and a CW project, confirm CE files are byte-identical and unknown fields survive.
  - Every PC runs 1.10.1 before the first branch build touches the live folder.
- **Branch builds:** prerelease tags `v1.11.0-ce.N` from `build-windows.yml`. Stable's updater reads `releases/latest`, which skips prereleases, so stable is never offered a branch build. The branch build's updater checks prereleases on its own channel so it does not offer stable as an "update".
- **Rollback:** stop running the branch exe. 1.10.1 still reads the whole folder; CE projects stay viewable read-only.
- **Merge:** after stage 1 is accepted (decided 2026-11-03). CE ships in the next minor release from `main`; stages 2 to 4 continue on new branches or on `main`.

## 3. Branding (every company, every document)

Decided 2026-11-02: one brand per company, applied to all of its outputs.

**Brand fields (Settings > Company, per profile)**
- Legal line and dba lines.
- Contact line (address, phone, email, website).
- Logo (SVG or PNG) and wordmark text with style (plain, or letter-spaced caps as on the CE proposal).
- Colors: primary, secondary, table header, alternate/option rows, rules.
- Heading style: band, rule, or spaced caps.
- Body font from the bundled set (Carlito default; bundled OFL fonts only, so output is identical on every PC).
- Footer text (e.g. "Convenient Woodworking and KeptSpec Advisors are trade names of Convenient Enterprises LLC") and page number format.

**Applies to:** proposal, estimate, change order / ECN, ledger, sub RFQ, quote comparison, purchase list, URS/RFQ package, Response Form, compliance matrix, FAT/SAT plan, questionnaire (.docx template).

**Rules**
- `common.typ` reads the brand. Hard-coded colors (e.g. the CW dark gold band) move into the KS and CW brand seeds.
- KS and CW outputs must not change visually: render regression test on the 26005 fixture and the CW box template.

## 4. CE identity (seed)

- Convenient Enterprises LLC, 224 Rutledge Rd, Fletcher NC 28732 | 423.218.6067 | nick@convenient.enterprises
- Logo: `seed/ce/logo.svg` (supplied 2026-11-03). Black wordmark, "CONVENIENT" letter-spaced over "ENTERPRISES" in a box outline. The SVG wraps a 1081 x 171 px PNG (not vector): about 430 ppi at a 2.5 in print width, enough for letterhead.
- Colors: black (#000000) primary; neutral grays for table headers, bands and option rows. No accent color unless one is added later.
- Client is "Client", CE is "Consultant" in proposal text (variables, so a URS-response proposal can say "Provider" and "Consumer" to match the client's spec).

## 5. Modules

| # | Module | Letter | Detailed | URS response |
|---|---|---|---|---|
| M1 | Introduction, machine and process, objective (narrative) | on | on | on |
| M2 | Scope: narrative plus bullet scope items | on | on | on |
| M3 | Deliverables (numbered, from library) | on | on | on |
| M4 | Client responsibilities (numbered, from library) | on | on | on |
| M5 | Material: who procures, pass-through clause | on | on | on |
| M6 | Labor: rate, ECNs, included revision rounds | on | on | on |
| M7 | Exclusions (checklist from library plus free text) | on | on | on |
| M8 | Timetable: gates and dependencies (e.g. "design begins on receipt of existing BOM and sketch") | on | on | on |
| M9 | Cost: fee items (section 6) | on | on | on |
| M10 | Terms (library) | on | on | on |
| M11 | Acceptance: signature blocks, both parties | on | on | on |
| M12 | Hours buildup (internal): tasks x role x hours drive fixed fees | | on | on |
| M13 | Hardware BOM: make, model, PN, qty, cost, supplier, lead time, who buys | | on | on |
| M14 | Milestone payment schedule | | on | on |
| M15 | Timeline: phases, durations, gates | | on | on |
| M16 | Assumptions and risks | | on | on |
| M17 | Requirements and compliance matrix (section 8) | | | on |
| M18 | System description per URS 1.5: loading/unloading, machine and cell layout, data scheme, controls and modes, HMI screens, order of operations (auto and manual), quality checks, cycle time breakdown, recipes | | | on |
| M19 | Commercial items per URS 1.5, 11, 12: capital vs tooling split, components over $10k, training and post-install support days, extended warranty, crating, insurance and shipping, ongoing support (resources, base, response times, breakdown and emergency rates) | | | on |
| M20 | Qualification documents: FAT/SAT plan, TAKT, cycle time, PDA, 3P (section 9) | | | on |

Each narrative module is a terms-library-style block: library text with `{variables}`, edited per proposal, snapshotted with the revision, "library updated" indicator, reset to library.

## 6. Cost model

**Fee item types**
- **Fixed fee:** amount, or hours x rate. In Detailed depth the hours come from M12. Invoiced by milestone.
- **T&M estimate:** engineering hours, onsite hours, remote hours x rate; travel hours x travel rate; lodging nights x lodging rate. Printed as an estimate ("actual time billed").
- **Option:** priced, printed with its own price, excluded from the base total. Uses the existing alternates machinery (add-only), so "Total with options" lines and Finalize work as they do for KS.
- **Pass-through hardware:** only when CE procures. Invoiced cost + sourcing fee (10%).
- **Category tag** on every line: engineering, support, travel, hardware, capital equipment, tooling. Tooling and capital totals print separately when M19 is on.

**CE settings (defaults from the MGM proposal)**
- Engineering rate $125/hr; out-of-scope rate $125/hr.
- Travel time at 50% of the rate ($62.50/hr), one way per trip.
- Lodging $300/night.
- Sourcing fee 10%.
- Deposit: 10% of the fixed fee, due at approval.
- Hourly work invoiced weekly; fixed fee by milestone.
- Validity 30 days. Included revision rounds 3.

**Mileage** (decided 2026-11-03, same as CW): free within 1 hour of 224 Rutledge Rd; beyond that, round-trip miles beyond the zone x $0.725 (IRS 2026 rate, CE setting). Travel time stays at the CE travel rate above.

**Travel destinations** (CE list): name, one-way hours, round-trip miles beyond the zone, overnight default. Seed: Murphy, NC, 2.5 h (miles to be entered).

**Reused from KS/CW:** revisions (1.x, Finalize 2.0, accept), alternates as options, variables, Issues tab, customers and contacts, numbering, income (CE column).

**No percent items** (no contingency or OH&P lines); margin is in the rate.

## 7. Estimate document (PO)

Decided by default (no preference given): the app produces the Estimate, and Wave is used for invoicing only.
- Itemized table (Item, Qty, Price, Amount) with the same text as the cost section, estimate number = proposal number, date, valid-until, deposit requested, bill-to with attention.
- Options listed below the base total, never inside it.
- Exported beside the proposal PDF; same brand.

## 8. Requirements (URS) engine

### 8.1 Requirement library
Seeded from URS_RFQ Template.docx (sections 1 to 15 and the FAT/SAT appendix). Each entry:
- ID (section number), heading, text with `{variables}` and placeholders.
- Kind: requirement, information, instruction, data field.
- Applies-when tags: PLC, HMI, robot, vision, hydraulics, pneumatics, safety PSD, recipes, data collection, turnkey, etc.
- Default on/off.
- Plain-language question(s) for the intake, with an example and answer type (text, number + unit, choice, yes/no/don't know, list, table, file).

### 8.2 Project URS
- Selected and edited copy of the library (snapshot rule), with URS/RFQ revision history and approvals tables.
- Answers fill variables and turn sections on or off (no hydraulics: section 6 drops out).
- Issued by CE. Intake and URS preparation are not billed but are noted (decided 2026-11-03): a no-charge line on the CE proposal (prints at $0, "included at no charge") and hours logged internally for estimate vs actual.
- Output: URS/RFQ package as .docx and PDF, matching the template structure, with CDA note, package contents list, Response Form and acknowledgement page. Attachments: TAKT, layout constraints, 3P, PDA, FAT/SAT.

### 8.3 Intake for clients without a spec
Both formats write the same answer set.
- **Word questionnaire:** plain-language .docx grouped by topic (your product, your process today, what the machine must do, volumes and shifts, plant utilities, safety, documentation, timeline and budget). Examples, checkboxes, units and a "don't know" choice. Built with content controls so the import is reliable. Import maps answers back; blanks and "don't know" become open items on the Issues tab.
- **In-app interview:** same questions, one topic per page, skip logic from applies-when tags, notes and file/photo attachments per answer, progress indicator.

### 8.4 Manual entry of a client's complete spec
Decided 2026-11-02: no automatic import. Client documents vary too much for a reliable parser.
- **Entry:** the in-app interview (8.3) on site or on a call, or an entry grid with one row per client requirement: client section number, heading, text (pasted or summarized), kind.
- **Starting point:** blank, or the library tree when the client's spec is built on our template (or close to it). Library rows are then edited, removed or renumbered to match the client.
- **Numbering:** the client's section numbers are the requirement IDs, so the compliance matrix and Response Form cite them directly.
- **Source document:** attached to the project for reference, not parsed. Recorded: title, reference number, revision, date.
- **Client revisions:** entering a new revision number keeps the rows. Rows edited after that are marked changed, and every compliance status is flagged for review until confirmed.

### 8.5 Compliance matrix and Response Form
- Each requirement: Comply, Comply with clarification, Deviate (with proposed alternative), N/A, Information only, By client.
- Response text and links to proposal modules, deliverables and BOM lines.
- Response Form generated from Deviate and Clarify rows, with URS reference number and revision. Always our form, even when the client's package includes its own (decided 2026-11-03).
- Issues: unanswered requirements, Deviate with no text, client URS revised since the response.

## 9. Engineering calculators and qualification documents

- **TAKT:** hours per shift, scheduled breaks and downtime, shifts per day, days per year, annual demand, machine count, allowance factor (the sheet's 0.6 "fudge factor", editable per project). Outputs takt (s/pc), required cycle time, current vs proposed. Results become variables (`{takt_s}`, `{cycle_req_s}`).
- **Cycle time breakdown:** manual and automatic elements, total vs takt.
- **PDA:** force, work environment and mobility tables with S/O/F/C frequency, comments, recommendation checkboxes.
- **3P checklist:** the 23 qualifiers (S-1 to S-4, Q-1 to Q-3, C-1 to C-7, L-1 to L-9), scored per concept for side-by-side comparison.
- **FAT/SAT plan:** from the URS appendix and the FAT_SAT workbook tabs. Rows generated from project data: each e-stop, door, light curtain and scanner; each alarm on the alarm list; reset/recovery cases; KPIs from process data; metrology rows by measurement type. Punch list, sign-off and corrective action log. Export .docx, .xlsx and PDF.
- **Safety:** target PL as a variable; SISTEMA modeling stays an option line (no PL calculation engine).

## 10. Change management and post-award

- **ECN** is the CE change order: either party initiates, written acknowledgement by both, hours x rate, affects fixed fee or T&M. Branded PDF.
- Revision rounds used against the included count (3), per deliverable.
- Deliverable and milestone status, with an invoice-due prompt (no invoicing).
- Actual vs estimated hours: Clockify CSV import by job code (CE-YYNNN), per task and phase.

## 11. CE libraries

- Catalog sections tagged CE.
- Task templates: each with default hours and role, deliverable text, implied client responsibilities and exclusions. Seed from MGM: safety control system design, pneumatic schematic, safety wiring schematic, PLC wiring schematic, BOM, PLC programming (by platform: Allen-Bradley, Unitronics, AutomationDirect), program delivery, advisory review, SISTEMA modeling, onsite day, remote support. Add: HMI development, robot programming (Fanuc, Staubli, Yaskawa Motoman), vision setup, commissioning, training, documentation package, risk assessment template.
- Deliverables, client responsibilities, exclusions and terms libraries seeded from the MGM proposal text.
- Hardware price references: manufacturer, model, PN, supplier, price, date, lead time (price age warning reused).
- Standards picklist: OSHA, NEC, NFPA 79, ISO 13849-1, ISO 4414, ANSI B11.19, ANSI/RIA R15.06.

## 12. Issues tab additions (CE)

- Unanswered requirements; Deviate without text; client URS revision changed.
- Fee items with no hours or rate; options counted in the base total.
- Hardware over $1k without make/model; over $10k not listed separately (URS response).
- Wording that implies certification: "certify", "stamped", "guarantee", "PE" outside the standard-of-care block.
- Placeholders block Issue (as KS and CW).

## 13. Stages

0. **1.10.1 on main:** forward compatibility (section 2).
1. **CE profile, branding, Letter depth:** profile plumbing, brand settings for all three companies, modules M1 to M11, cost model, Estimate PDF, CE terms library seeded from MGM, mileage as a fee line. Acceptance: tests 1 and 4. Then merge to `main`.
2. **Detailed depth:** M12 to M16, ECNs, travel destinations, hardware price references.
3. **Requirements engine:** library seeded from the template, project URS, URS/RFQ package export, Word questionnaire and in-app interview, manual spec entry, compliance matrix, Response Form, M17 to M19. Acceptance: tests 2 and 3.
4. **Calculators, qualification and tracking:** TAKT, cycle time, PDA, 3P, FAT/SAT (M20); turnkey commercial items; Clockify actuals.

## 14. Defaults chosen (no preference given)

- Wave: the app makes the PO estimate; Wave invoices only (section 7).
- Work type: engineering services now, turnkey later. The category tag and pass-through pricing exist from stage 1 and 2 so turnkey jobs need no data changes; turnkey workflow ships in stage 4.

## 15. Decisions log (open items resolved 2026-11-03)

1. CE logo supplied (`seed/ce/logo.svg`); black, no accent color.
2. Target time for a Letter proposal: 1 hour (acceptance test 4).
3. Mileage: same as CW (section 6).
4. URS/RFQ packages and intake are issued by CE; not billable, but noted on the proposal as a no-charge line.
5. URS responses always use our Response Form.
6. TAKT 0.6 is a fudge factor (allowance factor, editable).
7. Merge `ce` into `main` after stage 1.

**Open**
- Murphy, NC round-trip miles for the destination seed.
