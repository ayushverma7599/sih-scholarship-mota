# API Reference (curl tour)

Base URL: `http://localhost:8000` · Prefix: `/api` · Interactive docs: `/docs` (OpenAPI).
Auth: `Authorization: Bearer <token>` on every route except `/auth/*` and `/health`.
RBAC is enforced per endpoint; the required role is noted in `[...]`.

## Auth
```bash
# Login (any demo account, password demo1234)
curl -s localhost:8000/api/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"admin@demo.gov.in","password":"demo1234"}'
# -> { access_token, role, user_id, full_name }

TOKEN=$(curl -s localhost:8000/api/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"admin@demo.gov.in","password":"demo1234"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s localhost:8000/api/auth/me -H "Authorization: Bearer $TOKEN"
```
Other: `POST /auth/register`, `POST /auth/request-otp` (OTP printed to server console),
`POST /auth/verify-otp`, `PUT /auth/me` (profile; Aadhaar/bank are encrypted + masked).

## Schemes / configuration
```bash
curl -s localhost:8000/api/schemes -H "Authorization: Bearer $TOKEN"          # list
curl -s localhost:8000/api/schemes/1 -H "Authorization: Bearer $TOKEN"        # detail

# Dry-run eligibility against a profile (any authed user)
curl -s localhost:8000/api/schemes/1/eligibility-check -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"profile":{"category":"ST","age":28,"family_income":200000,"qualifying_marks":70,"course_level":"Ph.D"}}'
```
`POST /schemes` and `PUT /schemes/{id}` **[admin]** accept the full config
(rules, documents, merit_weights/tiebreak/quotas).

## Applicant
```bash
# Schemes you may be eligible for, with per-rule reasons
curl -s localhost:8000/api/me/eligible-schemes -H "Authorization: Bearer $APPLICANT"
curl -s localhost:8000/api/me/applications     -H "Authorization: Bearer $APPLICANT"

# Create draft -> save -> submit
curl -s localhost:8000/api/applications -H "Authorization: Bearer $APPLICANT" \
  -H 'Content-Type: application/json' -d '{"scheme_id":1,"form_data":{}}'
curl -s -X PUT localhost:8000/api/applications/1 -H "Authorization: Bearer $APPLICANT" \
  -H 'Content-Type: application/json' -d '{"form_data":{"full_name":"...","qualifying_marks":72}}'
curl -s -X POST localhost:8000/api/applications/1/submit -H "Authorization: Bearer $APPLICANT"

# Upload a document (classify + OCR + cross-verify happen inline)
curl -s -X POST localhost:8000/api/applications/1/documents \
  -H "Authorization: Bearer $APPLICANT" \
  -F doc_type=st_certificate -F file=@certificate.pdf

# Deficiency inbox + resubmit
curl -s localhost:8000/api/applications/1/deficiencies -H "Authorization: Bearer $APPLICANT"
curl -s -X POST localhost:8000/api/applications/1/resubmit -H "Authorization: Bearer $APPLICANT"
```

## Scrutiny officer [scrutiny]
```bash
curl -s "localhost:8000/api/scrutiny/queue?min_risk=25" -H "Authorization: Bearer $OFFICER"
curl -s localhost:8000/api/scrutiny/5 -H "Authorization: Bearer $OFFICER"    # split-screen payload
curl -s -X POST localhost:8000/api/scrutiny/5/verify -H "Authorization: Bearer $OFFICER" \
  -H 'Content-Type: application/json' -d '{"note":"ok"}'
curl -s -X POST localhost:8000/api/scrutiny/5/raise-deficiency -H "Authorization: Bearer $OFFICER" \
  -H 'Content-Type: application/json' -d '{"items":[{"doc_type":"income_certificate","message":"Illegible"}]}'
# Override an AI flag (mandatory justification, audited)
curl -s -X POST localhost:8000/api/scrutiny/ai-flags/3/override -H "Authorization: Bearer $OFFICER" \
  -H 'Content-Type: application/json' -d '{"note":"Verified manually against DigiLocker"}'
```
Also: `/reject`, `/escalate`, `POST /scrutiny/bulk-verify`.

## Selection [committee]
```bash
curl -s -X POST localhost:8000/api/schemes/1/generate-merit -H "Authorization: Bearer $COMMITTEE"
curl -s localhost:8000/api/schemes/1/merit-list -H "Authorization: Bearer $COMMITTEE"
curl -s -X POST localhost:8000/api/merit/5/adjust -H "Authorization: Bearer $COMMITTEE" \
  -H 'Content-Type: application/json' -d '{"selected":true,"justification":"PVTG special consideration"}'
curl -s -X POST localhost:8000/api/schemes/1/publish -H "Authorization: Bearer $COMMITTEE"
curl -s localhost:8000/api/selection/5/letter.pdf -H "Authorization: Bearer $COMMITTEE" -o letter.pdf
```

## Fellowship, grievance, dashboards, audit, mocks
```bash
curl -s localhost:8000/api/fellowships/me -H "Authorization: Bearer $APPLICANT"
curl -s localhost:8000/api/fellowships/1/disbursements -H "Authorization: Bearer $APPLICANT"  # mock DBT

curl -s localhost:8000/api/dashboard/kpis   -H "Authorization: Bearer $ADMIN"
curl -s localhost:8000/api/dashboard/charts -H "Authorization: Bearer $ADMIN"
curl -s "localhost:8000/api/reports/export?format=csv" -H "Authorization: Bearer $ADMIN" -o report.csv
curl -s "localhost:8000/api/audit?entity=ai_flag" -H "Authorization: Bearer $ADMIN"

# Gov mocks (labelled "mock": true)
curl -s -X POST localhost:8000/api/mock/digilocker/verify-st -H "Authorization: Bearer $OFFICER" \
  -H 'Content-Type: application/json' -d '{"certificate_number":"ST/12345","name":"..."}'
```
