"""Tests for the configurable eligibility rule engine."""
from app.services import rule_engine

NFST_RULES = {
    "combinator": "all",
    "rules": [
        {"field": "category", "op": "==", "value": "ST", "label": "Must be ST"},
        {"field": "age", "op": "<=", "value": 35, "label": "Age <= 35"},
        {"field": "family_income", "op": "<=", "value": 600000, "label": "Income limit"},
        {"field": "qualifying_marks", "op": ">=", "value": 55, "label": "Marks >= 55"},
        {"field": "course_level", "op": "in", "value": ["M.Phil", "Ph.D"], "label": "Course"},
    ],
}


def _profile(**over):
    base = {"category": "ST", "age": 28, "family_income": 200000,
            "qualifying_marks": 70, "course_level": "Ph.D"}
    base.update(over)
    return base


def test_eligible_when_all_rules_pass():
    ctx = rule_engine.build_context(_profile())
    res = rule_engine.evaluate(NFST_RULES, ctx)
    assert res["eligible"] is True
    assert all(r["pass"] for r in res["results"])


def test_income_over_limit_fails_with_reason():
    ctx = rule_engine.build_context(_profile(family_income=900000))
    res = rule_engine.evaluate(NFST_RULES, ctx)
    assert res["eligible"] is False
    failed = [r for r in res["results"] if not r["pass"]]
    assert len(failed) == 1
    assert failed[0]["field"] == "family_income"
    assert "900000" in failed[0]["reason"] or "9,00,000" in failed[0]["reason"] \
        or "900000" in str(failed[0]["actual"])


def test_wrong_category_fails():
    ctx = rule_engine.build_context(_profile(category="OBC"))
    res = rule_engine.evaluate(NFST_RULES, ctx)
    assert res["eligible"] is False


def test_course_not_in_list_fails():
    ctx = rule_engine.build_context(_profile(course_level="B.Sc"))
    res = rule_engine.evaluate(NFST_RULES, ctx)
    assert res["eligible"] is False


def test_missing_field_is_not_eligible_and_explained():
    ctx = rule_engine.build_context({"category": "ST"})  # missing others
    res = rule_engine.evaluate(NFST_RULES, ctx)
    assert res["eligible"] is False
    missing = [r for r in res["results"] if not r["pass"]]
    assert any("missing" in r["reason"].lower() for r in missing)


def test_any_combinator():
    rules = {"combinator": "any", "rules": [
        {"field": "a", "op": "==", "value": 1},
        {"field": "b", "op": "==", "value": 2},
    ]}
    assert rule_engine.evaluate(rules, {"a": 1, "b": 99})["eligible"] is True
    assert rule_engine.evaluate(rules, {"a": 0, "b": 0})["eligible"] is False


def test_no_rules_means_open_to_all():
    assert rule_engine.evaluate(None, {})["eligible"] is True
    assert rule_engine.evaluate({"rules": []}, {})["eligible"] is True


def test_build_context_flattens_nested_and_form_overrides_profile():
    ctx = rule_engine.build_context(
        {"bank": {"account": "123"}, "family_income": 100000},
        {"family_income": 500000},
    )
    assert ctx["account"] == "123"       # lifted from nested
    assert ctx["family_income"] == 500000  # form overrides profile
