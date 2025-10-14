
# AGENTS Instructions — Hana Table Inventory

These instructions apply to the entire repository.

---

## 1) Scope & Goals
- Track nationwide movement of Hana operating tables via QR → Google Forms → Google Sheet → Apps Script alerts.
- Keep the system **reproducible**, **portable**, and **safe to hand off** to another operator.

---

## 2) Architecture
```
Driver scans QR  --> Google Form (H1..H19, Training)
                     |
                     v
Google Sheet: "Mizuho Inventory" / tab "Table Inventory"
                     |
                     v
Apps Script (weekly trigger): checkInventory()
  - Reads configured ranges
  - Compares actual vs expected
  - Emails alerts ("there is X of Y") with sheet link
```
Key IDs:
- **Spreadsheet ID**: `1xzymMh5ijyPTwa1CS0blqxno89uI33QFgVs2tFTKA2Y`
- **Sheet Name**: `Table Inventory`

---

## 3) Code Style & Conventions
- **Apps Script**: ES2020+, 2-space indent, single quotes, trailing commas where valid.
- **Structure**: Small, pure helpers; side effects only in orchestration (email/send/trigger).
- **Docs**: JSDoc on public functions; explain inputs/outputs and external dependencies.
- **Commits**: Conventional commits (`feat:`, `fix:`, `chore:`, `docs:`). Keep PRs focused.

---

## 4) Repository Layout (recommended)
```
/apps-script/
  src/
    checkInventory.js     # main entry
    sheet.js              # getSheet, header access
    alerts.js             # email compose/send, throttling
  appsscript.json         # manifest

/docs/
  INVENTORY.md            # process flows, ranges, expected levels
  FORMS_INDEX.md          # H1–H19 + Training URLs and QR notes
  SHEET_SCHEMA.md         # column headers & validation rules
  INCIDENTS.md            # postmortems

/forms/
  H1..H19/                # optional per-form notes or exports
  training/

AGENTS.md
README.md
```

---

## 5) Configuration (single source of truth)
- **Audited Ranges** (must exist in `Table Inventory`):
  - `B7:T7`, `B14:T14`, `B22:T22`, `B8:T12`, `B15:T21`, `B23:T23`
- **Expected vs Threshold**: Each range has `expected` and `threshold` (default 2 for single rows; 1 for multi-row blocks).
- **Email recipients**: Configure in `CONFIG.email` (use a Google Group; avoid personal emails in code).
- **Form URLs**: Keep `docs/FORMS_INDEX.md` current for H1–H19 + Training.

---

## 6) Triggers & Operations
- **Primary job**: `checkInventory()` (time-driven **weekly**, e.g., Monday 06:00).
- **On failure**: Admin email is sent; check Apps Script **Executions** for stack traces.
- **Rate limits**: Sleep between emails to prevent quota issues.

---

## 7) Development Workflow
1. Create branch: `feat/<short-name>` or `fix/<short-name>`.
2. Update code **and** docs in the same PR when behavior changes.
3. Validate locally (optional, if editing via clasp):
   ```bash
   npm i -g @google/clasp
   clasp login
   clasp pull   # or clasp push if you're updating
   ```
4. Open PR with:
   - Summary, test notes, screenshots of sample alert email (if format changed).
   - Any trigger or config migrations.
5. After merge to `main`, deploy via Apps Script UI or `clasp deploy`.

---

## 8) Testing Strategy
- Isolate `getAlerts()` so it can be tested with mocked `getValues()` matrices.
- Add **dry-run** mode to route emails to dev list only.
- Maintain golden CSVs in `/tools/testdata/` to validate known states.

---

## 9) Security & Access
- Restrict edit access to Sheet + Script; most users should be view-only.
- No PHI/PII in free text fields. Keep driver names minimal (first + last initial).
- Prefer group aliases for notification recipients (change membership, not code).

---

## 10) Incident Response
1. Disable weekly trigger to stop noise.
2. Review Apps Script **Executions**; capture error + stack.
3. Verify headers/ranges and that forms still feed the sheet.
4. Re-run `checkInventory()` manually; re-enable trigger when green.
5. Log the RCA in `/docs/INCIDENTS.md`.

---

## 11) Migration Notes (Airtable / Microsoft 365 / Custom App)
- **Airtable**: Replace Forms with Airtable Forms; Automations for weekly checks; Interface for dashboards.
- **Microsoft 365**: Microsoft Forms → Excel Online; Power Automate weekly flow for counts + alerting.
- **Custom App**: Simple web UI; scheduled job reproduces `expected vs actual` logic; email via SMTP/Graph.

---

## 12) Checklists
**Before merge**
- [ ] Logic & thresholds validated on a copy of the sheet
- [ ] Docs updated (ranges/URLs/triggers, recipients)
- [ ] Dry-run verified (if changing email format)
- [ ] Script version tagged in Apps Script

**After deploy**
- [ ] Trigger present and correct cadence
- [ ] First run succeeds; email looks correct
- [ ] Stakeholders notified

---

## 13) How to add this file to `main`
From a local clone of `hana-table-inventory`:
```bash
# ensure you're on main and up to date
git checkout main
git pull --ff-only

# add AGENTS.md at repo root, then commit and push
git add AGENTS.md
git commit -m "docs: add AGENTS guide for Hana inventory system"
git push origin main
```
