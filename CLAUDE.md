# CLAUDE.md — Architecture & Conventions

AI-Enabled Scholarship & Fellowship Management System for Scheduled Tribes.
**Smart India Hackathon 2026 · Problem Statement 26239 · Ministry of Tribal Affairs.**

This file persists architectural context for future work. Keep it up to date.

## What this is
One configurable, transparent platform for MoTA's ST scholarship/fellowship schemes
(NFST, NOS). Scheme eligibility rules, required documents and selection criteria are
**configuration (JSON), not code**. An AI layer assists verification but **never
decides** — every automated flag is human-reviewable, overridable and audited.

## Monorepo layout
```
backend/     FastAPI + SQLAlchemy + Pydantic (Python 3.13)
  app/core/      config, database, security (JWT + Fernet PII), rbac deps
  app/models/    all ORM models (one module) + Roles/AppStatus constants
  app/schemas/   Pydantic request/response models
  app/services/  business logic (see below)
  app/api/       routers (auth, schemes, applications, scrutiny, selection,
                 fellowship, grievance, dashboard, audit, govmock, notifications)
  app/seed/      synthetic data + sample document generator
  app/tests/     pytest (rule engine, merit, deficiency, cross-verify)
frontend/    Next.js 14 App Router + TS + Tailwind + Recharts
  app/           routes by role: /applicant /officer /committee /admin
  components/    AppShell, RoleLayout, Timeline, Charts, ui primitives
  lib/           api client, auth context, i18n (en/hi), utils
docs/        ARCHITECTURE.md, API.md, DEMO.md
```

## Key services (backend/app/services)
- `rule_engine.py` — evaluates a JSON ruleset against a flattened context; returns
  per-rule pass/fail + human reasons. Powers applicant pre-check AND officer view.
- `merit.py` — configurable weighted scoring (normalizers per criterion), tie-breaks,
  reservation quotas, ranking + slot selection. Transparent breakdown per applicant.
- `extractor/` — `Extractor` interface. `TesseractExtractor` (default) reads a
  ground-truth **sidecar** (`<file>.truth.json`) when present so the OCR demo runs
  offline; else real Tesseract; else degrades to "manual review". `LLMExtractor`
  (Claude) is an off-by-default stub behind the same interface.
- `classify.py` — document-type detection (sidecar `_doc_type` or keyword heuristics).
- `crossverify.py` — extracted-vs-form checks → name mismatch, income exceeded,
  expired cert, low readability. Each flag carries reason + confidence.
- `duplicate.py` — same Aadhaar/bank (via **fingerprint**, no decryption) or identical
  document (SHA-256) across applications.
- `risk.py` — explainable triage score from active (non-overridden) flags.
- `deficiency.py` — plain-language deficiency generation (missing/wrong/unreadable
  docs + high-severity flags).
- `pipeline.py` — orchestrates auto-verification on submit/resubmit: duplicates →
  eligibility → deficiencies → risk → status transition (AUTO_VERIFIED / DEFICIENCY_RAISED).
- `govmocks.py` — DigiLocker / e-District / DBT-PFMS **mocks** (`"mock": true`).
- `audit.py` — append-only audit writer. `notifications.py` — in-app + mocked email/SMS.
- `storage.py` — local file storage behind an interface (S3-ready). `serialize.py` —
  output serialization with **PII masking** (Aadhaar/bank never returned in clear).
- `pdfgen.py` — selection letter + report PDFs (reportlab), watermarked PROTOTYPE.

## Data model (see docs/ARCHITECTURE.md for the ER diagram)
User/Role → Application → {ApplicationDocument→ExtractedField, AIFlag, Deficiency,
StatusEvent, MeritScore, Fellowship→{ProgressReport, Disbursement}}. Scheme →
{EligibilityRuleset, SchemeDocument[], MeritCriteria}. Cross-cutting: Notification,
AuditLog, Grievance.

Application status pipeline:
`DRAFT → SUBMITTED → AUTO_VERIFIED → UNDER_SCRUTINY → DEFICIENCY_RAISED →
RESUBMITTED → SCREENED → SELECTED/REJECTED → FELLOWSHIP_ACTIVE`

## Conventions
- **RBAC on every endpoint** via `require_roles(...)` / `get_current_user`.
- Roles: `applicant`, `scrutiny`, `committee`, `admin` (see `models.Roles`).
- Configurable data lives in JSON columns; never hardcode scheme-specific logic.
- Sample values are flagged `is_sample=True` and shown with a **SAMPLE** badge.
- Mocks/stubs are always labelled (`mock: true` + **MOCK** badge in UI).
- PII (Aadhaar, bank a/c) is encrypted at rest (Fernet), matched via fingerprint,
  masked in every response. Never log raw PII.
- Every override / status change / config change writes an `AuditLog` row.
- DB: SQLite by default (`DATABASE_URL`), PostgreSQL via docker-compose.
- Frontend talks to `/api/*` (Next rewrite → FastAPI :8000). Token in localStorage.
- i18n: `lib/i18n.tsx` dictionary (en/hi), extend by adding keys.

## Run
- No Docker: `make setup && make seed && make dev` (backend :8000, frontend :3000).
- Docker: `docker compose up --build`.
- Tests: `make test` (or `cd backend && pytest app/tests`).
- Demo logins (password `demo1234`): admin@ / scrutiny@ / committee@ / applicant@demo.gov.in.
- OpenAPI: http://localhost:8000/docs.

## Notes / deferrals
- Tesseract binary is optional (sidecars keep OCR demo working). Install
  `tesseract-ocr` + `poppler-utils` for real OCR (already in backend Dockerfile).
- Real DigiLocker/PFMS/DBT, real SMS/email, production S3 + KMS are out of scope.
