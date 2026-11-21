"""Scoring: weights config + the documented scoring function."""

from .score import (
    ScoreBreakdown,
    aggregate,
    finding_weight,
    llm_adjustment,
    plugin_score,
    plugin_weight,
    recommendation_action,
    risk_level,
    rule_residual,
)

__all__ = [
    "ScoreBreakdown",
    "aggregate",
    "finding_weight",
    "llm_adjustment",
    "plugin_score",
    "plugin_weight",
    "recommendation_action",
    "risk_level",
    "rule_residual",
]
