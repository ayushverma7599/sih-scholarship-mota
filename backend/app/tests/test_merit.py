"""Tests for the configurable merit scoring + ranking service."""
from app.services import merit


def test_score_is_weighted_and_normalized():
    weights = {"marks": 0.5, "family_income": 0.5}
    # marks 80 -> 80; income 0 -> 100. Equal weights -> (80+100)/2 = 90
    out = merit.score(weights, {"marks": 80, "family_income": 0})
    assert out["total"] == 90.0
    assert len(out["breakdown"]) == 2
    assert sum(b["weight"] for b in out["breakdown"]) == 1.0


def test_income_normalizer_lower_is_better():
    weights = {"family_income": 1.0}
    low = merit.score(weights, {"family_income": 100000})["total"]
    high = merit.score(weights, {"family_income": 500000})["total"]
    assert low > high  # lower income scores higher


def test_rank_orders_by_total_desc():
    weights = {"marks": 1.0}
    scored = [
        {"application_id": 1, "total": merit.score(weights, {"marks": 60})["total"],
         "values": {"marks": 60}, "attributes": {}},
        {"application_id": 2, "total": merit.score(weights, {"marks": 90})["total"],
         "values": {"marks": 90}, "attributes": {}},
        {"application_id": 3, "total": merit.score(weights, {"marks": 75})["total"],
         "values": {"marks": 75}, "attributes": {}},
    ]
    ranked = merit.rank_applicants(scored, {"tiebreak": [], "quotas": {}}, slots=2)
    order = [r["application_id"] for r in ranked]
    assert order == [2, 3, 1]
    assert ranked[0]["rank"] == 1
    # slots=2 -> top two selected
    assert sum(1 for r in ranked if r["selected"]) == 2
    assert ranked[0]["selected"] and ranked[1]["selected"]
    assert not ranked[2]["selected"]


def test_tiebreak_uses_secondary_field():
    scored = [
        {"application_id": 1, "total": 50, "values": {"age": 30}, "attributes": {}},
        {"application_id": 2, "total": 50, "values": {"age": 25}, "attributes": {}},
    ]
    # age_asc -> younger (smaller age) wins the tie
    ranked = merit.rank_applicants(scored, {"tiebreak": ["age_asc"], "quotas": {}}, slots=1)
    assert ranked[0]["application_id"] == 2


def test_quota_reserves_subslots():
    scored = [
        {"application_id": 1, "total": 95, "values": {}, "attributes": {"women": False}},
        {"application_id": 2, "total": 90, "values": {}, "attributes": {"women": False}},
        {"application_id": 3, "total": 40, "values": {}, "attributes": {"women": True}},
    ]
    # 2 slots, 50% women quota -> 1 reserved for a woman (app 3) despite lower score
    ranked = merit.rank_applicants(scored, {"tiebreak": [], "quotas": {"women": 0.5}}, slots=2)
    selected = {r["application_id"] for r in ranked if r["selected"]}
    assert 3 in selected  # woman got the reserved sub-slot
    assert len(selected) == 2


def test_empty_weights_returns_zero():
    out = merit.score({}, {"marks": 90})
    assert out["total"] == 0.0
