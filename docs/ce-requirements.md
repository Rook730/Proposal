# Convenient Enterprises (engineering) profile: requirements draft

Version 0.7 | 2026-11-03 | Owner: Nick (stage 0 released in 1.10.1; stages 1 to 3 merged and released as 2.0.0)
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
4. Time: a Letter proposal like MGM is built in 1 hour or less (a target, not a gate: decided 2026-11-03).

**Out of scope (for now)**
- Invoicing (Wave), e-signature, multi-user, client web portal or hosted forms.
- PE-stamped calculations or certification.
- Parsing prints, CAD or photos (attached for reference only).
- Automatic import of client spec documents (.docx or PDF). Client specs vary too much for a parser to be worth it; they are entered manually (section 8.4).

## 2. Branch, release and data plan

- **Branch** `ce` in Rook730/Proposal. `main` stays the stable app. Merge after stage 1 (see Merge below).
- **Step 0: 1.10.1 on main (forward compatibility).** Today every persisted model uses `extra="forbid"`, so a file saved by the branch build would stop 1.10.0 from reading the folder.
  - Persisted models keep unknown fields on load and write them back on save (not dropped, not rejected).
  - Projects with an unknown profile (`ce`) are listed with their company but not opened (as built: a read-only view would show a stripped-down proposal, since CE content is invisible to 1.10.1). No new CE projects. They are left out of income, customer linking and Copy from.
  - `profiles/ce/` is ignored. Unknown catalog section profiles are kept and hidden, with their items; their codes and numbers count as taken.
  - Numbering: unchanged shared YYNNN sequence. Stable picks up the counter the branch build advanced.
  - Tests: load a folder saved by the branch build, edit a KS project and a CW project, confirm CE files are byte-identical and unknown fields survive.
  - Every PC runs 1.10.1 before the first branch build touches the live folder.
- **Shared-file contract for the `ce` branch** (what 1.10.1 can tolerate):
  - Shared files (root `settings.json`, `catalog.json`, `boilerplate.json`, `customers.json`, `contractors.json`, `suppliers.json`): add fields only. No renamed or removed fields, no changed meaning, no new enum values in existing fields.
  - Exception: catalog sections with `profile: "ce"` and the items in them may use anything (new price bases, new fields); 1.10.1 keeps them raw.
  - CE sections and item codes: 4000 to 4900 (KS uses 100 to 1400, CW 2000 to 3xxx, pieces 9000+).
  - CE settings and terms live in `profiles/ce/`; CE projects in their own folders. 1.10.1 never reads either.
  - A KS or CW project gains new fields only (e.g. brand data); KS and CW revisions must keep loading in 1.10.1.
- **Branch builds:** prerelease tags `v1.11.0-ce.N` from `build-windows.yml`. Stable's updater reads `releases/latest`, which skips prereleases, so stable is never offered a branch build. The branch build's updater checks prereleases on its own channel so it does not offer stable as an "update".
- **Rollback:** stop running the branch exe. 1.10.1 still reads the whole folder; CE projects stay listed (not opened).
- **Merge:** after stage 1 is accepted (decided 2026-11-03). CE ships in the next minor release from `main`; stages 2 to 4 continue on new branches or on `main`. The 1-hour target (test 4) does not hold up the merge. As built: stages 2 and 3 continued on `ce`, then `ce` merged into `main` as 2.0.0 (decided 2026-11-03); stage 4 continues on `main` or a new branch.

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

**Travel destinations** (CE list): name, one-way hours, round-trip miles beyond the zone, overnight default. Seed: Murphy, NC, 2.5 h, 110 round-trip miles beyond the zone (about 116 road miles from 224 Rutledge Rd; the one-hour zone ends near mile 61 on US 74 past Sylva).

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
2. **Detailed depth:** M12 to M16, ECNs, travel destinations, hardware price references (as built: 13b).
3. **Requirements engine:** library seeded from the template, project URS, URS/RFQ package export, Word questionnaire and in-app interview, manual spec entry, compliance matrix, Response Form, M17 to M19. Acceptance: tests 2 and 3 (as built: 13c).
4. **Calculators, qualification and tracking:** TAKT, cycle time, PDA, 3P, FAT/SAT (M20); turnkey commercial items; Clockify actuals.

## 13a. As built: stage 1 (branch `ce`, prerelease 1.11.0-ce.1)

- **Profile:** `models.CE` ("ce", Convenient Enterprises) in `PROFILES`; settings, terms library and logo seeded from `seed/ce/` into `profiles/ce/`. Payment rule `fixed_fee`, deposit 10%, license warning off, global variables for the rates and terms wording (eng_rate, travel_rate, lodging_rate, mileage_rate, free_zone, sourcing_fee, revision_rounds, termination_notice). Performer "Convenient Enterprises" (income CE) added once to the shared Performers list (`Settings.migrations` marker "ce-performer").
- **Catalog (`ce_catalog.py`, marker "ce-stage1"):** sections 4000 Engineering (fixed fee, `billing: fixed`), 4100 Technical support and 4200 Travel (time and materials, `billing: estimate`); items 4010 to 4230 (design package, PLC, HMI, robot programming, SISTEMA, lump sum, no-charge requirements intake 4090, onsite, remote, out-of-scope, travel time, lodging, mileage); rates ce_eng $125, ce_travel $62.50, ce_lodging $300 (EA, so no new unit prints on KS/CW unit tables), ce_mileage $0.725/MI. Section gains `billing` (new field, allowed by the contract).
- **Billing (`ce.py`):** fee lines are ordinary lines; a section's billing says fixed fee or estimate. Deposit = deposit % of the fixed-fee lines. Options are add-only alternates, printed with their own price and a total with the option, never in the base total.
- **Proposal (`render/ce_document.py`, `ce_proposal.typ`):** the terms library modules in heading order (Intro on page 1, then Scope, Deliverables, Material, Labor, Exclusions, Time Table, Cost, Terms, Termination, Acceptance). `{cost_table}` prints the fee lines grouped by section (fixed fee / estimate, billed at actual), totals, deposit and options; `{signatures}` prints both parties' blocks. Variables available: {fixed_fee}, {estimate_total}, {deposit_amount}, {deposit_pct}, {fixed_balance}, {total_price}. TBD placeholders in the seed text block Issue until filled. `build_document` hands CE projects to it, and the document names its own template.
- **Estimate (`ce_estimate.typ`):** same cost data as an itemized document (bill to, estimate #, date, valid until, total, deposit requested), options listed under the total, note from Settings > Proposals (`estimate_note`). Exported with every proposal export and on Issue; also Preview / Export estimate in the editor menu.
- **Branding:** `models.Brand` (layout classic/band, text color, accent, header band color, body and heading font, spaced headings, logo width, footer) per company in Settings > Company > Brand. `Settings.brand` is None for existing KS and CW settings, which keeps their exact look (`default_brand`); CE's seed sets the band layout, black and grays, IBM Plex Sans (OFL, bundled), spaced headings. `common.typ` reads the brand for every document (header band on every page for "band"); `proposal.typ` reads text color, font, logo width and footer. Render regression: all KS and CW documents pixel-identical before and after (22 pages).
- **Editor for CE:** tabs Lines, Variables, Options, Proposal text (modules with TBD open), Issues, Income; no Sub quotes, no Change orders & ledger (ECNs are stage 2), no Changes or SOV page options, no appendix images. Totals strip: Fixed fee, T&M estimate, Total, each option (+amount, total with option), Deposit.
- **Income:** CE column in the Income tab, Income summary and CSV. CE income = Convenient Enterprises lines except lodging and mileage (reimbursed). Estimate only.
- **Updates:** a version with a dash (1.11.0-ce.1) reads all releases including prereleases; stable versions read releases/latest only. The workflow publishes a tag with a dash as a prerelease. Version order: 1.10.1 < 1.11.0-ce.1 < 1.11.0-ce.2 < 1.11.0.
- **Not in stage 1:** Changes from previous revision page and appendix images for CE; ECNs; travel destinations; hours buildup.
- **Acceptance:** test 1 is automated (`tests/test_ce.py`, `tests/ce_mgm.py`): fixed fee $10,000.00, estimate $2,956.25, total $12,956.25, option +$1,000.00 (total with option $13,956.25), deposit $1,000.00. Test 4 (1 hour) needs Nick's timing on a real proposal.

## 13b. As built: stage 2 (branch `ce`, prerelease 1.11.0-ce.2)

- **Depth (`Revision.depth`):** Letter or Detailed, toggled on the Project plan tab (`ce.set_depth`). Detailed turns on four terms blocks (Material: Bill of materials `{bom_table}`; Time Table: Schedule `{timeline_table}`; Cost: Milestone payments `{milestone_table}`; Assumptions: bullets with a TBD) and copies the milestone and schedule starting points from Settings when the revision has none. Letter turns those blocks off; nothing is deleted. Folders from stage 1 get the blocks and the Assumptions heading once (`ce_catalog.upgrade_library`, marker "ce-stage2").
- **M12 hours buildup:** line form, Quantity "Hours buildup" (CE only): tasks with hours and an internal note, added by hand or from Settings > Proposals > Task templates (16 seeded from MGM plus HMI, robot, vision, commissioning, training, documentation). Quantity = sum of task hours; the line's rate prices it. Never printed. Deviation from section 11: no role per task (one rate per line) and templates carry no implied client responsibilities or exclusions.
- **M13 bill of materials (`Revision.bom`, `ce_models.BomItem`):** make, model, part number, description, qty, unit, unit cost, supplier, lead time, bought by (Client or Consultant). Prints make/model, part number, qty, supplier, lead time and buyer, never prices. Consultant-bought items are billed through one line, 4310 in new section 4300 Hardware (estimate billing): invoiced cost x (1 + sourcing fee, Settings, 10%), kept in step on every BOM edit and removed when no such items remain (`ce.sync_hardware_line`). Income counts only the sourcing fee. Rows can be added from Price references, which gained make, model and lead time.
- **M14 milestone payments (`Revision.milestones`):** invoice, when (prints), share of the fixed fee. Deposit (Settings) is the first row; the last row takes any rounding cent. Seed: Design approval 40%, Documentation and program delivery 30%, Run-off 20%.
- **M15 schedule (`Revision.phases`):** phase, start week, weeks, gate. Prints as a bar chart. Seed: Design 0+3, Documentation and programming 2+3, Onsite validation and run-off 5+1.
- **Travel destinations (Settings > Proposals):** name, one-way hours, round-trip miles beyond the free zone, overnight. Project plan > Add trip makes the travel time (one way per trip, travel rate), lodging and mileage lines. Seed: Murphy, NC, 2.5 h, overnight, 110 round-trip miles beyond the zone ($79.75 per trip).
- **ECNs:** the change orders page for CE is titled ECNs; items take hours and a rate (default ce_eng) and the final cost follows (original + hours x rate, also when a saved file is read). No markup, no overhead and profit row; the PDF is an "Engineering Change Notice" with "ECN No." and "N HR at $rate" on each item, in the CE brand. Editor menu: ECNs.
- **Issues (section 12, partly):** payment schedule not adding to 100%; Consultant-bought BOM item without a cost; BOM item of $1,000 or more without make and model (info); certification or guarantee wording (certify, stamped, guarantee, warranty, PE) in a block or line note beyond what the library text already says (the library's own disclaimers are not flagged); a block saying the Client buys all hardware while the BOM has Consultant-bought items.
- **Checks:** 9 stage 2 tests (`tests/test_ce_stage2.py`); the self-test builds a Detailed proposal (total $13,256.25 with $1,100.00 hardware). KS and CW documents pixel-identical (22 pages, including change orders). A folder written by this build opened in 1.10.1: CE project listed and not opened, section 4300 and item 4310 kept, new fields on KS change orders, settings and price references kept through a 1.10.1 save; CE files untouched.
- **Not in stage 2:** category tag per line; revision rounds used; deliverable and milestone status with invoice prompt; Clockify actuals (stage 4); hours per role.

## 13c. As built: stage 3 (branch `ce`, prerelease 1.11.0-ce.3)

- **Requirement library (`ce_urs.py`, `seed/ce/requirements.md`):** the URS/RFQ Template Rev 1.0 as 120 sections (levels 1 to 3, numbered as in the template, 1 to 15 plus the FAT/SAT appendix as 16), each with a kind (requirement, instruction, data, information) and the yes/no questions it depends on. Seven yes/no questions (pneumatics, hydraulics, PLC/HMI, recipes, interfaces, tooling, FAT/SAT plan) and 36 variables with plain-language questions, examples and defaults (the template's own wording). Template notes are marked `[!...]`: blue in the template, dropped from an issued URS; other bracketed text is a blank to fill in. Interface Devices keeps both of the template's paragraphs until the interfaces question is answered. The data folder keeps `profiles/ce/requirements.json`, created from the seed on first use and edited on Catalog > Requirement library (sections, variables and questions, yes/no questions, front matter; Export blank template).
- **Project URS (`urs.json` in the project folder):** Requirements tab of a CE project. Two starts: *We write the URS/RFQ* (copy of the library; adds the no-charge intake line 4090) or *Respond to the client's spec* (blank, or the library tree with its numbers, then edited to the client's numbering; title, reference, revision, date of their document; their file is reference only, never parsed). Rows: number (automatic, or typed for client specs), level, heading, text, kind, on/off, compliance status (Comply, Comply with clarification, Deviate, N/A, Information only, By client), response, links. Grid with in-place status and response, double-click dialog, add/move/indent/delete, Comply to the rest. Sections turned off print "Not applicable" (numbers stay) or are left out (later sections renumber), per project. Library updated indicator per row.
- **Intake (8.3):** in-app interview (`/project/<n>/interview`, one topic per page, progress bar, saves as you type, "Don't know" leaves the question open) and the Word questionnaire with content controls (check boxes for yes/no, text boxes for answers, "Don't know" boxes); import reads the controls by tag, so notes typed elsewhere do no harm. Both write the same answers. A variable whose sections are all off is not asked.
- **URS/RFQ package (`render/urs_document.py`, `urs.typ`):** Word (.docx, python-docx) and PDF from one model: cover (client, address, title, subtitle, URS/RFQ and RFQ lines, revision and month, issued and due dates, confidential information), URS/RFQ revision history, table of contents (Word builds it when the file is opened), numbered sections with bullets, tables and signature lines, footer with revision, page X of Y, author and document number. The blank template adds the instructions page and Document Version History and Approvals, as the original does. Saved in the project's `urs` folder. Structure and wording follow the template; its exact Word formatting is not copied (not needed, decided 2026-11-03). Calibri in Word, Carlito in the PDF. The completed URS is the client's document: their name heads the cover and header, and a small gray footer credit ("Prepared by Convenient Enterprises LLC | email", also in the Word file's properties) keeps it traceable to CE without CE branding (decided 2026-11-03). The Response Form carries the same credit.
- **Response Form:** URS/RFQ reference, revision, completed by (default: the library author), completed date (default: today), the template instructions, and every Deviate and Clarify row by section number (Clarify text prefixed "Clarification:"), padded to 12 rows. Word and PDF.
- **URS response depth (M17 to M19):** third depth on the Project plan tab. Turns on the Detailed blocks plus new terms-library headings Requirements (intro naming the spec `{urs_reference}` and the compliance matrix `{compliance_table}`), System Description (loading/unloading, machine and cell layout, data, controls and modes, HMI screens, order of operations, quality checks, cycle time, recipes; each a TBD block) and Commercial (`{commercial_table}`: base totals by category with tooling apart from capital equipment, and bill of materials items of $10,000 or more; training and support, warranty, crating/insurance/shipment, ongoing support). Folders from stage 2 get the blocks once (marker "ce-stage3").
- **Category per line (6):** line form, CE only: engineering, support, travel, hardware, capital equipment, tooling; "From section" uses 4000 engineering, 4100 support, 4200 travel, 4300 hardware. `Line.category` is a new field (allowed by the contract).
- **Snapshot:** issuing a CE revision stores the URS and its compliance in the revision (`Revision.urs`); an issued revision prints its own copy, drafts print the live one. A new revision starts from the live one.
- **Issues (12):** interview questions open; blanks left in the URS (by section); with URS response depth or a client spec: requirements with no status, Deviate/Clarify with no response text, responses to review after a client revision; URS response depth with no requirements; bill of materials items of $10,000 or more while the Commercial table is off.
- **Checks:** 7 tests (`tests/test_ce_urs.py`): numbering matches the template's contents and appendix cross-references (acceptance test 2, with the blank template's Word headings and PDF); answers, yes/no questions and both omit modes; questionnaire round trip; compliance, Response Form order and client revision review (acceptance test 3); URS response proposal with compliance matrix, commercial table and the issue snapshot. Self-test builds the package, Response Form and questionnaire. KS and CW documents pixel-identical (22 pages). A stage 3 folder round-trips through 1.10.1 (CE files untouched; new revision and line fields kept).
- **Not in stage 3:** attaching the client's spec file from the app (type its name in Document details); M20 qualification documents and calculators (stage 4).

## 14. Defaults chosen (no preference given)

- Wave: the app makes the PO estimate; Wave invoices only (section 7).
- Work type: engineering services now, turnkey later. The category tag and pass-through pricing exist from stage 1 and 2 so turnkey jobs need no data changes; turnkey workflow ships in stage 4.

## 15. Decisions log (open items resolved 2026-11-03)

1. CE logo supplied (`seed/ce/logo.svg`); black, no accent color.
2. Target time for a Letter proposal: 1 hour (acceptance test 4); a target, not a gate for the merge.
3. Mileage: same as CW (section 6).
4. URS/RFQ packages and intake are issued by CE; not billable, but noted on the proposal as a no-charge line.
5. URS responses always use our Response Form.
6. TAKT 0.6 is a fudge factor (allowance factor, editable).
7. Merge `ce` into `main` after stage 1. As built: merged after stage 3 as 2.0.0.
8. Murphy, NC destination: 110 round-trip miles beyond the one-hour zone (estimated from about 116 road miles, 2 h 8 min; zone boundary near mile 61). Adjust in Settings > Proposals if a trip log says otherwise.
9. The completed URS is the client's document; CE appears only as a subtle footer credit. Exact template formatting need not be copied.
