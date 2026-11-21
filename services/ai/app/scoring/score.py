"""The scoring function: findings after critique -> continuous risk score 0-100.

1. Signal strength of one plugin:        S_p = sum_i  w_i * c_i  (+ rule residuals for M2)
     w_i  weight of the finding type (scoring/weights.py)
     c_i  confidence of the finding *after* the critic: detector confidence x critique
          factor; a rejected claim has c_i = 0.
2. Plugin score (saturating):            score_p = 100 * (1 - exp(-S_p))
     Several weak signals add up, but no pile of minor issues can exceed 100.
3. Aggregation across plugins (noisy-OR): raw = 1 - prod_p (1 - W_p * score_p / 100)
     W_p caps how much risk one plugin can contribute alone, so e.g. an odd comment
     pattern never produces a red incident without a regulatory finding.
4. Mitigation by upheld counter-arguments: M = min(cap, sum_j m_j * c_j)
     risk_score = 100 * raw * (1 - M)
5. Optional LLM term (only when a model ran): + min(LLM_MAX_POINTS, LLM_CLAIM_POINTS * sum(c_k)) over
   grounded LLM-proposed claims, capped at 100. Absent a model this term is exactly 0.

Everything is monotone: a new finding never lowers the score, a new mitigating
circumstance never raises it. No value depends on which sample is analysed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..schemas import RuleResult
from . import weights as W


def finding_weight(code: str) -> float:
    if code.startswith("RULE_"):
        return W.RULE_WEIGHTS.get(code[5:], W.DEFAULT_FINDING_WEIGHT)
    return W.FINDING_WEIGHTS.get(code, W.DEFAULT_FINDING_WEIGHT)


def rule_residual(rules: list[RuleResult]) -> float:
    """Residual risk of criteria that passed with doubt or could not be assessed."""
    total = 0.0
    for r in rules:
        weight = W.RULE_WEIGHTS[r.id]
        if r.status == "unknown":
            total += weight * W.UNKNOWN_RULE_FACTOR
        elif r.status == "pass":
            total += weight * (1.0 - r.confidence) * W.PASS_DOUBT_FACTOR
    return total


def plugin_score(signals: list[tuple[str, float]], residual: float = 0.0) -> float:
    """signals: (finding code, confidence after critique). Returns 0-100."""
    strength = residual + sum(finding_weight(code) * max(0.0, min(1.0, conf)) for code, conf in signals)
    return 100.0 * (1.0 - math.exp(-strength))


def plugin_weight(plugin_id: str) -> float:
    return W.PLUGIN_WEIGHTS.get(plugin_id, W.DEFAULT_PLUGIN_WEIGHT)


@dataclass(frozen=True)
class ScoreBreakdown:
    raw: float  # 0-1 before mitigation
    mitigation: float  # 0-cap
    risk_score: float  # 0-100, including the LLM term
    llm_points: float = 0.0  # points added by grounded LLM claims (0 when no model ran)


def aggregate(plugin_scores: dict[str, float], mitigations: list[tuple[str, float]]) -> ScoreBreakdown:
    """plugin_scores: plugin id -> 0-100; mitigations: (mitigation key, confidence)."""
    survive = 1.0
    for plugin_id, score in plugin_scores.items():
        survive *= 1.0 - plugin_weight(plugin_id) * score / 100.0
    raw = 1.0 - survive
    mitigation = min(W.MITIGATION_CAP, sum(W.MITIGATION_WEIGHTS.get(k, 0.0) * c for k, c in mitigations))
    return ScoreBreakdown(raw=raw, mitigation=mitigation, risk_score=round(100.0 * raw * (1.0 - mitigation), 1))


def llm_adjustment(confidences: list[float]) -> float:
    """Points added to the risk score by grounded LLM-proposed claims (capped, never negative)."""
    total = sum(W.LLM_CLAIM_POINTS * max(0.0, min(1.0, c)) for c in confidences)
    return round(min(W.LLM_MAX_POINTS, total), 1)


def risk_level(risk_score: float, t_orange: float = W.T_ORANGE, t_red: float = W.T_RED) -> str:
    if risk_score >= t_red:
        return "red"
    return "orange" if risk_score >= t_orange else "green"


def recommendation_action(risk_score: float) -> str:
    if risk_score >= W.RECOMMEND_ESCALATE:
        return "escalate"
    if risk_score >= W.RECOMMEND_EXPLAIN:
        return "explain"
    return "monitor" if risk_score >= W.RECOMMEND_MONITOR else "none"
