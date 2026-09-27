"""Configurable eligibility rule engine.

Rules are stored as JSON on each scheme (no scheme logic is hardcoded). The same
evaluator powers the applicant's instant eligibility pre-check AND the officer's
verification view — both get human-readable pass/fail reasons for every rule.

Ruleset shape::

    {
      "combinator": "all",           # "all" | "any"
      "rules": [
        {"field": "category", "op": "==", "value": "ST",
         "label": "Must belong to a Scheduled Tribe"},
        {"field": "family_income", "op": "<=", "value": 250000,
         "label": "Annual family income within limit"}
      ]
    }
"""
from __future__ import annotations

from typing import Any

OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: _num(a) < _num(b),
    "<=": lambda a, b: _num(a) <= _num(b),
    ">": lambda a, b: _num(a) > _num(b),
    ">=": lambda a, b: _num(a) >= _num(b),
    "in": lambda a, b: a in b if isinstance(b, (list, tuple, set)) else False,
    "not_in": lambda a, b: a not in b if isinstance(b, (list, tuple, set)) else True,
    "contains": lambda a, b: b in a if isinstance(a, (list, tuple, str)) else False,
}

# Human-friendly phrasing for each operator, used to build reasons.
_OP_PHRASE = {
    "==": "should equal", "!=": "should not equal",
    "<": "should be less than", "<=": "should be at most",
    ">": "should be more than", ">=": "should be at least",
    "in": "should be one of", "not_in": "should not be one of",
    "contains": "should contain",
}


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def _fmt(v: Any) -> str:
    if isinstance(v, (list, tuple, set)):
        return ", ".join(str(x) for x in v)
    return "—" if v is None else str(v)


def evaluate_rule(rule: dict, context: dict) -> dict:
    """Evaluate a single rule against the flattened context."""
    field = rule.get("field")
    op = rule.get("op")
    expected = rule.get("value")
    label = rule.get("label") or f"{field} {op} {expected}"
    actual = context.get(field)

    fn = OPS.get(op)
    if fn is None:
        return {
            "label": label, "field": field, "op": op, "expected": expected,
            "actual": actual, "pass": False, "reason": f"Unknown operator '{op}'.",
        }

    if actual is None:
        passed = False
        reason = f"{label}: value for '{field}' is missing in the profile."
    else:
        try:
            passed = bool(fn(actual, expected))
        except Exception as exc:  # defensive: never let a bad rule crash evaluation
            return {
                "label": label, "field": field, "op": op, "expected": expected,
                "actual": actual, "pass": False, "reason": f"Could not evaluate: {exc}",
            }
        phrase = _OP_PHRASE.get(op, op)
        if passed:
            reason = f"{label}: satisfied ({field} = {_fmt(actual)})."
        else:
            reason = (
                f"{label}: not satisfied — {field} is {_fmt(actual)}, "
                f"but it {phrase} {_fmt(expected)}."
            )

    return {
        "label": label, "field": field, "op": op, "expected": expected,
        "actual": actual, "pass": passed, "reason": reason,
    }


def evaluate(ruleset: dict | None, context: dict) -> dict:
    """Evaluate a full ruleset. Returns eligibility + per-rule explanations."""
    if not ruleset or not ruleset.get("rules"):
        return {"eligible": True, "combinator": "all", "results": [],
                "summary": "No eligibility rules configured — open to all."}

    combinator = ruleset.get("combinator", "all")
    results = [evaluate_rule(r, context) for r in ruleset["rules"]]
    passes = [r["pass"] for r in results]

    eligible = all(passes) if combinator == "all" else any(passes)
    failed = [r for r in results if not r["pass"]]
    if eligible:
        summary = "Eligible — all applicable criteria are met."
    else:
        summary = f"Not eligible — {len(failed)} criterion/criteria not met."

    return {
        "eligible": eligible,
        "combinator": combinator,
        "results": results,
        "summary": summary,
    }


def build_context(profile: dict | None, form_data: dict | None = None) -> dict:
    """Flatten a user profile (+ optional form data) into a rule-evaluation context.

    Later keys win, so form_data overrides profile where both provide a field.
    Nested dicts are flattened one level with their own keys preserved too.
    """
    ctx: dict = {}
    for source in (profile or {}, form_data or {}):
        for k, v in source.items():
            if isinstance(v, dict):
                # keep the nested dict AND lift its scalar children to top level
                ctx[k] = v
                for nk, nv in v.items():
                    if not isinstance(nv, (dict, list)):
                        ctx.setdefault(nk, nv)
            else:
                ctx[k] = v
    return ctx
