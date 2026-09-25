from backend.modules.retrieval.diffractive_activation import decide_diffractive_activation


def test_v44_ordinary_vitality_can_reach_activation_after_persistence():
    decision = decide_diffractive_activation(
        collapse_pressure=0.68,
        rolling_entropy=0.55,
        vitality=0.55,
        streak=2,
    )

    assert decision.active


def test_flowing_focus_remains_inactive():
    decision = decide_diffractive_activation(
        collapse_pressure=0.2,
        rolling_entropy=0.7,
        vitality=0.7,
    )

    assert not decision.active
