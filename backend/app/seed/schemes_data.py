"""Seed definitions for the two flagship schemes: NFST and NOS.

All numeric thresholds are SAMPLE values (is_sample=True) and are surfaced in the
UI as 'sample — to be updated per official MoTA guidelines'. Everything here is
data: eligibility rules, documents and merit weights are fully configurable.
"""
from __future__ import annotations

NFST = {
    "code": "NFST",
    "name": "National Fellowship for Scheduled Tribe Students",
    "description": ("Fellowship for ST students pursuing M.Phil / Ph.D research "
                    "programmes in India. (Sample configuration for prototype.)"),
    "academic_year": "2025-26",
    "slots": 30,
    "window_open": "2025-08-01",
    "window_close": "2026-03-31",
    "is_active": True,
    "is_sample": True,
    "rules": {
        "combinator": "all",
        "rules": [
            {"field": "category", "op": "==", "value": "ST",
             "label": "Applicant must belong to a Scheduled Tribe"},
            {"field": "age", "op": "<=", "value": 35,
             "label": "Age must be 35 years or below"},
            {"field": "family_income", "op": "<=", "value": 600000,
             "label": "Annual family income within Rs. 6,00,000"},
            {"field": "qualifying_marks", "op": ">=", "value": 55,
             "label": "Qualifying examination marks at least 55%"},
            {"field": "course_level", "op": "in", "value": ["M.Phil", "Ph.D"],
             "label": "Enrolled in M.Phil or Ph.D"},
        ],
    },
    "documents": [
        {"doc_type": "st_certificate", "label": "Scheduled Tribe Certificate", "mandatory": True,
         "extract_fields": ["name", "certificate_number", "issuing_authority", "valid_upto"], "order": 1},
        {"doc_type": "income_certificate", "label": "Income Certificate", "mandatory": True,
         "extract_fields": ["name", "income_amount", "certificate_number", "valid_upto"], "order": 2},
        {"doc_type": "aadhaar", "label": "Aadhaar Card", "mandatory": True,
         "extract_fields": ["name", "aadhaar", "dob"], "order": 3},
        {"doc_type": "marksheet", "label": "Qualifying Degree Marksheet", "mandatory": True,
         "extract_fields": ["name", "marks", "certificate_number"], "order": 4},
        {"doc_type": "net_gate_scorecard", "label": "NET / GATE Scorecard", "mandatory": True,
         "extract_fields": ["name", "marks", "certificate_number"], "order": 5},
        {"doc_type": "admission_letter", "label": "Ph.D/M.Phil Admission Letter", "mandatory": True,
         "extract_fields": ["name", "issuing_authority", "certificate_number"], "order": 6},
        {"doc_type": "research_proposal", "label": "Research Proposal / Synopsis", "mandatory": False,
         "extract_fields": ["name"], "order": 7},
    ],
    "merit_weights": {"marks": 0.40, "income_bracket": 0.20,
                      "research_proposal": 0.25, "interview": 0.15},
    "merit_tiebreak": ["marks", "age_asc"],
    "merit_quotas": {"women": 0.30, "pvtg": 0.10},
}

NOS = {
    "code": "NOS",
    "name": "National Overseas Scholarship",
    "description": ("Scholarship for ST students pursuing Master's / Ph.D programmes "
                    "abroad at top-ranked universities. (Sample configuration.)"),
    "academic_year": "2025-26",
    "slots": 15,
    "window_open": "2025-09-01",
    "window_close": "2026-02-28",
    "is_active": True,
    "is_sample": True,
    "rules": {
        "combinator": "all",
        "rules": [
            {"field": "category", "op": "==", "value": "ST",
             "label": "Applicant must belong to a Scheduled Tribe"},
            {"field": "family_income", "op": "<=", "value": 800000,
             "label": "Annual family income within Rs. 8,00,000"},
            {"field": "qualifying_marks", "op": ">=", "value": 60,
             "label": "Qualifying examination marks at least 60%"},
            {"field": "course_level", "op": "in", "value": ["Masters", "Ph.D"],
             "label": "Admitted to a Master's or Ph.D programme"},
            {"field": "university_rank", "op": "<=", "value": 500,
             "label": "University within top 500 (QS World Ranking)"},
        ],
    },
    "documents": [
        {"doc_type": "st_certificate", "label": "Scheduled Tribe Certificate", "mandatory": True,
         "extract_fields": ["name", "certificate_number", "issuing_authority", "valid_upto"], "order": 1},
        {"doc_type": "income_certificate", "label": "Income Certificate", "mandatory": True,
         "extract_fields": ["name", "income_amount", "certificate_number", "valid_upto"], "order": 2},
        {"doc_type": "aadhaar", "label": "Aadhaar Card", "mandatory": True,
         "extract_fields": ["name", "aadhaar", "dob"], "order": 3},
        {"doc_type": "marksheet", "label": "Qualifying Degree Marksheet", "mandatory": True,
         "extract_fields": ["name", "marks", "certificate_number"], "order": 4},
        {"doc_type": "admission_letter", "label": "Foreign University Admission Letter", "mandatory": True,
         "extract_fields": ["name", "issuing_authority", "certificate_number"], "order": 5},
        {"doc_type": "research_proposal", "label": "Statement of Purpose / Research Proposal",
         "mandatory": False, "extract_fields": ["name"], "order": 6},
    ],
    "merit_weights": {"marks": 0.35, "university_rank": 0.30,
                      "income_bracket": 0.15, "research_proposal": 0.20},
    "merit_tiebreak": ["marks"],
    "merit_quotas": {"women": 0.30},
}

SCHEMES = [NFST, NOS]
