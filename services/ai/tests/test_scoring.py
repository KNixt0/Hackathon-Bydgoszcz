from __future__ import annotations

import math

import pytest

from app.rules import RULE_ORDER
from app.scoring import aggregate, finding_weight, plugin_score, recommendation_action, risk_level
from app.scoring import weights as W


def test_weights_cover_every_rule_and_plugin():
    assert set(W.RULE_WEIGHTS) == set(RULE_ORDER)
    assert all(0 < w <= 1 for w in W.PLUGIN_WEIGHTS.values())
    assert finding_weight("RULE_3") == W.RULE_WEIGHTS["3"]
    assert finding_weight("SOMETHING_NEW") == W.DEFAULT_FINDING_WEIGHT


def test_plugin_score_is_saturating_and_monotone():
    assert plugin_score([]) == 0
    one = plugin_score([("RULE_3", 0.9)])
    two = plugin_score([("RULE_3", 0.9), ("RULE_2", 0.9)])
    assert one == pytest.approx(100 * (1 - math.exp(-0.9 * W.RULE_WEIGHTS["3"])))
    assert one < two < 100
    assert plugin_score([("RULE_3", 0.9)] * 50) <= 100
    assert plugin_score([("RULE_3", 0.0)]) == 0  # a rejected claim contributes nothing


def test_aggregate_is_continuous_bounded_and_monotone():
    base = aggregate({"m2_risk_disclosure": 60.0}, [])
    more = aggregate({"m2_risk_disclosure": 60.0, "m3_shadow_advisory": 50.0}, [])
    mitigated = aggregate({"m2_risk_disclosure": 60.0, "m3_shadow_advisory": 50.0}, [("FIRM_REGISTERED", 0.95)])
    assert base.risk_score == pytest.approx(60 * W.PLUGIN_WEIGHTS["m2_risk_disclosure"], abs=0.05)
    assert base.risk_score < more.risk_score <= 100
    assert mitigated.risk_score < more.risk_score
    assert aggregate({}, []).risk_score == 0
    everything = aggregate(dict.fromkeys(W.PLUGIN_WEIGHTS, 100.0), [])
    assert 95 < everything.risk_score <= 100


def test_mitigation_is_capped():
    many = [(k, 1.0) for k in W.MITIGATION_WEIGHTS]
    assert aggregate({"m3_shadow_advisory": 100.0}, many).mitigation == W.MITIGATION_CAP


def test_levels_and_recommendations_follow_thresholds():
    assert [risk_level(s) for s in (0, 34.9, 35, 69.9, 70, 100)] == ["green", "green", "orange", "orange", "red", "red"]
    assert risk_level(40, t_orange=50) == "green"
    assert [recommendation_action(s) for s in (5, 20, 50, 80)] == ["none", "monitor", "explain", "escalate"]
