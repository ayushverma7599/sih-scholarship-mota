"""Tests for deficiency detection and cross-verification (AI-assist layer)."""
from types import SimpleNamespace as NS

from app.services import crossverify, deficiency


def _scheme():
    return NS(documents=[
        NS(doc_type="st_certificate", label="ST Certificate", mandatory=True),
        NS(doc_type="income_certificate", label="Income Certificate", mandatory=True),
        NS(doc_type="research_proposal", label="Research Proposal", mandatory=False),
    ])


def _app(docs, flags=None):
    return NS(documents=docs, flags=flags or [])


def test_missing_mandatory_document_flagged():
    scheme = _scheme()
    app = _app([NS(doc_type="st_certificate", detected_type="st_certificate", readability=0.9)])
    defs = deficiency.detect_deficiencies(app, scheme)
    msgs = " ".join(d["message"] for d in defs)
    assert "Income Certificate" in msgs
    assert any(d["doc_type"] == "income_certificate" for d in defs)


def test_optional_document_not_required():
    scheme = _scheme()
    app = _app([
        NS(doc_type="st_certificate", detected_type="st_certificate", readability=0.9),
        NS(doc_type="income_certificate", detected_type="income_certificate", readability=0.9),
    ])
    defs = deficiency.detect_deficiencies(app, scheme)
    assert defs == []  # research proposal is optional


def test_wrong_document_type_flagged():
    scheme = _scheme()
    app = _app([
        NS(doc_type="st_certificate", detected_type="aadhaar", readability=0.9),
        NS(doc_type="income_certificate", detected_type="income_certificate", readability=0.9),
    ])
    defs = deficiency.detect_deficiencies(app, scheme)
    assert any("looks like" in d["message"] for d in defs)


def test_low_readability_flagged():
    scheme = _scheme()
    app = _app([
        NS(doc_type="st_certificate", detected_type="st_certificate", readability=0.2),
        NS(doc_type="income_certificate", detected_type="income_certificate", readability=0.9),
    ])
    defs = deficiency.detect_deficiencies(app, scheme)
    assert any("read clearly" in d["message"] for d in defs)


def test_high_severity_flag_becomes_deficiency():
    scheme = _scheme()
    app = _app(
        [NS(doc_type="st_certificate", detected_type="st_certificate", readability=0.9),
         NS(doc_type="income_certificate", detected_type="income_certificate", readability=0.9)],
        flags=[NS(type="income_exceeded", overridden=False, reason="Income too high")],
    )
    defs = deficiency.detect_deficiencies(app, scheme)
    assert any("Income too high" in d["message"] for d in defs)


def test_overridden_flag_not_a_deficiency():
    scheme = _scheme()
    app = _app(
        [NS(doc_type="st_certificate", detected_type="st_certificate", readability=0.9),
         NS(doc_type="income_certificate", detected_type="income_certificate", readability=0.9)],
        flags=[NS(type="income_exceeded", overridden=True, reason="Income too high")],
    )
    defs = deficiency.detect_deficiencies(app, scheme)
    assert defs == []


# --- cross-verification ---

def test_name_mismatch_flag():
    extracted = {"name": {"value": "Ramesh Kumar", "confidence": 0.9}}
    flags = crossverify.cross_verify(extracted=extracted,
                                     form_data={"full_name": "Suresh Munda"})
    assert any(f["type"] == "name_mismatch" for f in flags)


def test_name_match_no_flag():
    extracted = {"name": {"value": "Ramesh Kumar Munda", "confidence": 0.9}}
    flags = crossverify.cross_verify(extracted=extracted,
                                     form_data={"full_name": "Ramesh Munda"})
    assert not any(f["type"] == "name_mismatch" for f in flags)


def test_income_exceeded_flag():
    extracted = {"income_amount": {"value": "900000", "confidence": 0.9}}
    flags = crossverify.cross_verify(extracted=extracted, form_data={}, income_limit=600000)
    assert any(f["type"] == "income_exceeded" for f in flags)


def test_expired_certificate_flag():
    extracted = {"valid_upto": {"value": "01-01-2020", "confidence": 0.9}}
    flags = crossverify.cross_verify(extracted=extracted, form_data={})
    assert any(f["type"] == "expired_certificate" for f in flags)
