"""All scoring weights and thresholds in one place.

Weights are properties of *finding types*, never of individual documents. They were set by
judgement of how serious each signal is for the supervisor and then checked against the
calibration set in `samples/eval` (see `scripts/run_eval.py`).
"""

from __future__ import annotations

# Weight of a failed criterion of the UKNF attachment (module 2). 1.0 would mean "this
# alone saturates the module".
RULE_WEIGHTS: dict[str, float] = {
    "1": 0.20,
    "2": 0.45,
    "3": 0.90,
    "4": 0.30,
    "5": 0.25,
    "6": 0.40,
    "7": 0.40,
    "8": 0.20,
    "9": 0.15,
    "10": 0.35,
    "11": 0.25,
    "12a": 0.30,
    "12b": 0.25,
    "13": 0.25,
    "14": 0.35,
    "15": 0.40,
    "16": 0.20,
    "17": 0.60,
    "18": 0.55,
}
# A rule that could not be assessed keeps a share of its weight as residual risk, and a
# passed rule keeps a share proportional to the detector's doubt (1 - confidence).
UNKNOWN_RULE_FACTOR = 0.10
PASS_DOUBT_FACTOR = 0.30

FINDING_WEIGHTS: dict[str, float] = {
    # module 1
    "PROMOTED_FIRM_NOT_LISTED": 0.90,
    "WARNING_LISTED": 2.00,
    "COOPERATION_NOT_NOTIFIED": 0.25,
    "UNMARKED_THIRD_PARTY_AD": 0.30,
    "DISGUISED_AD": 0.30,
    "LEGAL_ADVISER_INACTIVE": 0.15,
    "LEGAL_ADVISER_NOT_FOUND": 0.15,
    "TAX_ADVISER_INACTIVE": 0.20,
    "TAX_ADVISER_NOT_FOUND": 0.20,
    # module 2 (RULE_<id> comes from RULE_WEIGHTS)
    "PROFIT_RISK_IMBALANCE": 0.15,
    # module 3
    "ADVISORY_PHRASE": 0.55,
    "PORTFOLIO_MANAGEMENT": 0.60,
    "ADVISORY_SERVICE_OFFER": 0.20,
    "GUARANTEED_RETURN": 0.60,
    "REGISTRY_NOT_LISTED": 0.90,
    "UNREGISTERED_SERVICE_PROVIDER": 0.45,
    "ENTITY_UNIDENTIFIED": 0.35,
    "FAKE_LICENCE": 0.70,
    "BRAND_IMPERSONATION": 0.90,
    "NAME_SIMILAR_TO_REGISTERED": 0.15,
    # graph / KRS
    "PR_CONFLICT_PATH": 0.90,
    "PERSONAL_TIE_PATH": 0.50,
    "COMPANY_YOUNG": 0.20,
    "LOW_SHARE_CAPITAL": 0.15,
    "NO_FINANCIAL_STATEMENTS": 0.20,
    "FOREIGN_SHELL": 0.60,
    # opinion forensics
    "OPINION_SPIKE": 0.50,
    "FRESH_ACCOUNT_CLUSTER": 0.70,
    "NAME_PATTERN_CLUSTER": 0.50,
    "FOREIGN_ORIGIN_CLUSTER": 0.40,
    # LLM-proposed claims are shown in the debate but do not move the score by default,
    # so the score stays reproducible with and without a model.
    "LLM_CLAIM": 0.0,
}
DEFAULT_FINDING_WEIGHT = 0.25
SEVERITY_FACTOR = {"high": 1.0, "medium": 1.0, "low": 1.0, "info": 0.0}

# Share of the total risk a plugin can contribute on its own (aggregator weights).
PLUGIN_WEIGHTS: dict[str, float] = {
    "m1_finfluencer": 0.60,
    "m2_risk_disclosure": 0.50,
    "m3_shadow_advisory": 0.85,
    "graph_intel": 0.15,
    "opinion_forensics": 0.15,
}
DEFAULT_PLUGIN_WEIGHT = 0.40

# Mitigating circumstances raised by the critic: each reduces the aggregated risk by this
# fraction (times the claim confidence); the total reduction is capped.
MITIGATION_WEIGHTS: dict[str, float] = {
    "FIRM_REGISTERED": 0.12,
    "PARENT_REGISTERED": 0.25,
    "COOPERATION_NOTIFIED": 0.08,
    "AD_MARKED": 0.06,
    "RISK_WARNING_ADJACENT": 0.08,
    "RISK_INFO_PRESENT": 0.05,
    "ORGANIC_OPINIONS": 0.05,
    "NO_HIDDEN_TIES": 0.05,
    "NOT_ON_WARNING_LIST": 0.06,
    "ADVICE_DISCLAIMER": 0.03,
    "LEGAL_ADVISER_ACTIVE": 0.03,
    "REPORTING_CONTEXT": 0.25,
    "ADVISOR_LICENCE_VALID": 0.08,
}
MITIGATION_CAP = 0.30

# Derived level at default thresholds (the dashboard recomputes it from risk_score).
T_ORANGE = 35.0
T_RED = 70.0

# Recommendation thresholds on the final risk score.
RECOMMEND_MONITOR = 18.0
RECOMMEND_EXPLAIN = 35.0
RECOMMEND_ESCALATE = 70.0
