# 5-Minute Demo Runbook

> Tells the story from the problem statement: *admin configures a scheme → applicant
> applies → AI flags a deficiency → applicant resubmits → officer verifies → merit list
> → committee approves → dashboard updates.*

## Before you start
- Run `make seed` (loads NFST/NOS + ~200 synthetic applicants) then start the app.
- **For a smooth demo, serve the production build** (`cd frontend && npm run build && npm start`)
  or `docker compose up`. Dev mode compiles each route on first visit and can be slow.
- Have all four demo logins handy (password `demo1234`). Open the login page — they're
  listed there as one-click buttons.

## Script

### 0. Landing (15s)
Open **http://localhost:3000**. Point out: Government-appropriate design, English/हिंदी
toggle, and one-click demo logins for all four roles.

### 1. Admin configures a scheme (60s) — *the headline feature*
1. Click **Ministry Admin**.
2. **Schemes → NFST → Configure.**
3. Show that eligibility is **pure configuration**: rules like `family_income <= 600000`,
   `course_level in [M.Phil, Ph.D]`, each with a human label. Documents and their OCR
   fields are listed. Merit weights (marks 40%, income 20%, proposal 25%, interview 15%),
   tie-breaks and reservation quotas (women 30%, PVTG 10%) are all editable.
4. Change a value (e.g. slots or income limit) → **Save**. No code changed. Note the
   **SAMPLE** badge — values are placeholders pending official MoTA guidelines.

### 2. Applicant applies (75s)
1. Logout → **Applicant (ST student)**.
2. **Eligible schemes with reasons** — click *"Why? eligibility check"* to show the
   per-rule pass/fail evaluation driving the recommendation.
3. **Apply** on a scheme → the multi-step form is **generated from the scheme config**
   (it asks exactly what the rules & merit need).
4. **Documents step** — upload a PDF; watch **instant AI feedback**: detected document
   type, readability %, and extracted fields (name, certificate number, income…).
   > Tip: use the generated sample PDFs under `backend/uploads/app_*/` — they carry a
   > ground-truth sidecar so extraction works even without Tesseract installed.
5. **Submit.**

### 3. AI flags a deficiency & applicant resubmits (45s)
- On submit, the **auto-verification pipeline** runs (duplicates → eligibility →
  deficiencies → risk). If something's missing/mismatched, a **plain-language deficiency**
  appears in the **Deficiency Inbox** on the tracker.
- Show the **visual timeline** (Submitted → Auto-Verified → … → Deficiency Raised).
- **Re-upload only the flagged document**, add a note, and **Resubmit**. The timeline
  advances. (To force a deficiency live, skip a mandatory document in step 2.)

### 4. Officer verifies (60s)
1. Logout → **Scrutiny Officer**.
2. **Queue** is prioritised by **risk score** with **SLA timers** and filters
   (scheme/status/risk).
3. Open an application → **split-screen**: document preview on the left; extracted data,
   form data and **AI flags with reasons + confidence** on the right.
4. Emphasise **AI assists, human decides**: click **Override** on a flag — a mandatory
   justification is required and the override is **logged**. Then **Verify** (or **Raise
   Deficiency** / **Reject**). Mention **Bulk verify** for clean, auto-verified cases.

### 5. Merit list & committee approval (60s)
1. Logout → **Committee Member** → pick **NFST**.
2. **Generate merit list** — every applicant shows a **transparent score breakdown**
   (raw → normalized → weight → contribution). Reservation quota tags are visible.
3. **Adjust** an entry — a **justification is mandatory** and audited.
4. **Publish results** → selected applicants are notified; a **selection-letter PDF** is
   generated (download from the applicant's tracker).

### 6. Dashboard & audit update (30s)
1. Logout → **Ministry Admin → Dashboard**: KPIs (auto-verified %, deficiency rate,
   processing time, funds committed), the selection **funnel**, and charts by
   scheme/state/gender/tribe/course update with the activity. Export **CSV/PDF**.
2. **Audit Log**: show the immutable trail — every status change, **AI override** and
   **config change** with actor, timestamp and before/after.

## Talking points to land
- **Configurable, not hardcoded** — new schemes/rules without code.
- **Explainable everywhere** — eligibility and merit always show *why*.
- **AI assists, humans decide** — every flag reviewable, overridable, audited.
- **Transparent & secure** — RBAC, PII encrypted + masked, full audit trail.
- **Clearly-labelled mocks** — DigiLocker/e-District/DBT, OTP, email/SMS.
