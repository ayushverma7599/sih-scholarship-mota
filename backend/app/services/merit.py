"""Configurable, explainable merit scoring + ranking.

Weights, tie-break order, and reservation quotas all come from the scheme's
MeritCriteria (JSON) — nothing is hardcoded per scheme. Every score ships with a
per-criterion breakdown so applicants and committee members can see exactly how
it was computed.
"""
from __future__ import annotations

from typing import Any, Callable

# --- Per-criterion normalizers: map a raw value -> 0..100 (higher = better). ---
# `params` lets a scheme tune caps without code changes (stored under
# MeritCriteria.weights[key] as {"weight": w, "params": {...}} if desired).


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _norm_direct(v, params):           # already a 0..100 percentage/score
    return max(0.0, min(100.0, _to_float(v)))


def _norm_income(v, params):           # lower income -> higher score
    cap = _to_float(params.get("cap", 800000), 800000)
    income = _to_float(v)
    return max(0.0, min(100.0, 100.0 * (1 - income / cap))) if cap else 0.0


def _norm_rank(v, params):             # lower rank (e.g. QS) -> higher score
    worst = _to_float(params.get("worst_rank", 500), 500)
    rank = _to_float(v, worst)
    if worst <= 1:
        return 0.0
    return max(0.0, min(100.0, 100.0 * (1 - (rank - 1) / (worst - 1))))


NORMALIZERS: dict[str, Callable] = {
    "marks": _norm_direct,
    "marks_percentage": _norm_direct,
    "research_proposal": _norm_direct,
    "research_proposal_score": _norm_direct,
    "interview": _norm_direct,
    "income_bracket": _norm_income,
    "family_income": _norm_income,
    "university_rank": _norm_rank,
    "qs_rank": _norm_rank,
}


def _weight_spec(raw) -> tuple[float, dict]:
    """A weight entry may be a plain number or {"weight":w,"params":{...}}."""
    if isinstance(raw, dict):
        return _to_float(raw.get("weight", 0)), dict(raw.get("params", {}))
    return _to_float(raw), {}


def score(weights: dict, values: dict) -> dict:
    """Compute a weighted 0..100 total with a transparent breakdown.

    weights: {criterion_key: weight}   (weights are normalized to sum to 1)
    values:  {criterion_key: raw_value}
    """
    if not weights:
        return {"total": 0.0, "breakdown": []}

    specs = {k: _weight_spec(w) for k, w in weights.items()}
    total_weight = sum(w for w, _ in specs.values()) or 1.0

    breakdown = []
    total = 0.0
    for key, (weight, params) in specs.items():
        raw = values.get(key)
        normalizer = NORMALIZERS.get(key, _norm_direct)
        normalized = round(normalizer(raw, params), 2)
        wnorm = weight / total_weight
        contribution = round(normalized * wnorm, 2)
        total += contribution
        breakdown.append({
            "criterion": key,
            "raw": raw,
            "normalized": normalized,      # 0..100
            "weight": round(wnorm, 4),     # share of total
            "contribution": contribution,  # points added to total
        })

    return {"total": round(total, 2), "breakdown": breakdown}


def _tiebreak_key(item: dict, tiebreak: list[str]):
    """Build a sort key from tie-break spec, e.g. ['marks','age_asc'].

    Suffix '_asc' means ascending (smaller is better) for that field; default is
    descending (larger is better). Values pulled from item['values'].
    """
    key = []
    for spec in tiebreak or []:
        asc = spec.endswith("_asc")
        field = spec[:-4] if asc else (spec[:-5] if spec.endswith("_desc") else spec)
        val = _to_float(item["values"].get(field), 0.0)
        key.append(val if asc else -val)
    return tuple(key)


def rank_applicants(scored: list[dict], criteria: dict, slots: int) -> list[dict]:
    """Order applicants, apply tie-breaks, tag reservation quotas, mark selected.

    `scored` items: {"application_id", "total", "values", "attributes"}
      - values: raw criterion values (for tie-breaks)
      - attributes: e.g. {"women": True, "pvtg": False} for quota matching
    Returns the same items enriched with rank / selected / quota_tag.
    """
    tiebreak = criteria.get("tiebreak", [])
    quotas: dict = criteria.get("quotas", {})

    ordered = sorted(
        scored,
        key=lambda x: (-_to_float(x["total"]), _tiebreak_key(x, tiebreak)),
    )
    for i, item in enumerate(ordered, start=1):
        item["rank"] = i
        item["selected"] = False
        item["quota_tag"] = None

    if slots and slots > 0:
        selected_ids: set = set()

        # 1) Reserve quota sub-slots first (e.g. women 30%, PVTG 10%).
        for qkey, share in quotas.items():
            reserve = int(round(slots * _to_float(share)))
            picked = 0
            for item in ordered:
                if picked >= reserve:
                    break
                if item["application_id"] in selected_ids:
                    continue
                if item.get("attributes", {}).get(qkey):
                    item["selected"] = True
                    item["quota_tag"] = qkey
                    selected_ids.add(item["application_id"])
                    picked += 1

        # 2) Fill remaining slots by pure merit.
        for item in ordered:
            if len(selected_ids) >= slots:
                break
            if item["application_id"] not in selected_ids:
                item["selected"] = True
                selected_ids.add(item["application_id"])

    return ordered
