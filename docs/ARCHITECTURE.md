# Architecture

## Component view
```mermaid
flowchart TB
  subgraph FE["Frontend — Next.js 14 (App Router)"]
    L[Login + demo logins]
    AP[Applicant portal]
    OF[Officer workbench]
    CO[Committee]
    ADM[Admin dashboards + scheme config]
  end
  FE -->|/api/* JWT, i18n| BE

  subgraph BE["Backend — FastAPI (RBAC on every route)"]
    AUTH[auth] ; SCH[schemes/config] ; APPL[applications+docs]
    SCR[scrutiny] ; SEL[selection] ; FEL[fellowship]
    DASH[dashboard] ; AUD[audit] ; GOV[gov mocks] ; NOT[notifications]
    subgraph SVC["Services"]
      RE[rule_engine] ; MR[merit] ; EX[extractor] ; CVf[crossverify]
      CLf[classify] ; DPf[duplicate] ; RKf[risk] ; DFf[deficiency] ; PP[pipeline]
    end
  end
  BE --> DB[(PostgreSQL / SQLite)]
  BE --> ST[(Uploads / Storage iface)]
```

## Entity-Relationship diagram
```mermaid
erDiagram
    USER ||--o{ APPLICATION : submits
    USER ||--o{ AUDIT_LOG : acts
    USER ||--o{ NOTIFICATION : receives
    ROLE ||--o{ USER : has

    SCHEME ||--o{ SCHEME_DOCUMENT : requires
    SCHEME ||--o{ APPLICATION : receives
    SCHEME ||--|| ELIGIBILITY_RULESET : defines
    SCHEME ||--|| MERIT_CRITERIA : defines

    APPLICATION ||--o{ APPLICATION_DOCUMENT : includes
    APPLICATION ||--o{ DEFICIENCY : has
    APPLICATION ||--o{ AI_FLAG : flagged_by
    APPLICATION ||--o{ STATUS_EVENT : transitions
    APPLICATION ||--o| MERIT_SCORE : scored
    APPLICATION ||--o| FELLOWSHIP : becomes

    APPLICATION_DOCUMENT ||--o{ EXTRACTED_FIELD : yields
    SCHEME_DOCUMENT ||--o{ APPLICATION_DOCUMENT : slot

    FELLOWSHIP ||--o{ PROGRESS_REPORT : tracks
    FELLOWSHIP ||--o{ DISBURSEMENT : schedules
    USER ||--o{ GRIEVANCE : raises

    USER {
        int id PK
        string email
        string mobile
        int role_id FK
        json profile "tribe, income, academics, bank(enc+masked)"
        bool campus_verified
    }
    ROLE { int id PK  string name }
    SCHEME {
        int id PK  string code  string name  int slots
        date window_open  date window_close  bool is_active  bool is_sample
    }
    ELIGIBILITY_RULESET { int id PK  int scheme_id FK  json rules }
    SCHEME_DOCUMENT { int id PK  int scheme_id FK  string doc_type  bool mandatory  json extract_fields }
    MERIT_CRITERIA { int id PK  int scheme_id FK  json weights  json tiebreak  json quotas }
    APPLICATION {
        int id PK  int user_id FK  int scheme_id FK  string status
        json form_data  float risk_score  datetime submitted_at
    }
    APPLICATION_DOCUMENT { int id PK  int application_id FK  string doc_type  string detected_type  float readability  string sha256 }
    EXTRACTED_FIELD { int id PK  int app_document_id FK  string key  string value  float confidence }
    AI_FLAG { int id PK  int application_id FK  string type  string severity  text reason  float confidence  bool overridden }
    DEFICIENCY { int id PK  int application_id FK  string doc_type  text message  string status }
    STATUS_EVENT { int id PK  int application_id FK  string from_status  string to_status  int actor_id FK  datetime at }
    MERIT_SCORE { int id PK  int application_id FK  float total  json breakdown  int rank  string quota_tag }
    FELLOWSHIP { int id PK  int application_id FK  string stage  date joining_date  string status }
    PROGRESS_REPORT { int id PK  int fellowship_id FK  string period  string status }
    DISBURSEMENT { int id PK  int fellowship_id FK  string period  float amount  string status }
    GRIEVANCE { int id PK  int user_id FK  string subject  string status }
    NOTIFICATION { int id PK  int user_id FK  string channel  text message  bool read }
    AUDIT_LOG { int id PK  int actor_id FK  string entity  string action  json before  json after  datetime at }
```

## Application status lifecycle
```mermaid
stateDiagram-v2
    [*] --> DRAFT
    DRAFT --> SUBMITTED: submit
    SUBMITTED --> AUTO_VERIFIED: passes auto-checks
    SUBMITTED --> DEFICIENCY_RAISED: auto issues found
    AUTO_VERIFIED --> UNDER_SCRUTINY: officer opens
    UNDER_SCRUTINY --> DEFICIENCY_RAISED: officer raises
    UNDER_SCRUTINY --> SCREENED: verify
    UNDER_SCRUTINY --> REJECTED: reject
    DEFICIENCY_RAISED --> RESUBMITTED: applicant resubmits
    RESUBMITTED --> AUTO_VERIFIED: re-check clean
    RESUBMITTED --> DEFICIENCY_RAISED: still deficient
    SCREENED --> SELECTED: published within slots
    SCREENED --> REJECTED: not selected
    SELECTED --> FELLOWSHIP_ACTIVE: joining report
    FELLOWSHIP_ACTIVE --> [*]
```

## Design principles
- **Configuration over code** — schemes are data (rules, documents, weights).
- **AI assists, humans decide** — every flag has a reason + confidence, is overridable,
  and overrides are audited.
- **Transparency** — eligibility and merit always show *why* (per-rule / per-criterion).
- **Security & privacy** — RBAC everywhere; PII encrypted at rest, matched via
  fingerprint, masked in every response.
- **Swappable integrations** — storage, extractor and gov APIs sit behind interfaces;
  mocks are clearly labelled and drop-in replaceable.
