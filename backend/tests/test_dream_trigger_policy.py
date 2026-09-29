import logging
from types import SimpleNamespace

from backend.metabolisation.dream_trigger_policy import DreamTriggerPolicyMixin


def test_budget_exhaustion_logs_once_per_transition(caplog):
    daemon = SimpleNamespace(
        short_counter=2,
        short_window_max=2,
        short_window_hours=8,
        dream_counter=3,
        max_daily_dreams=30,
    )

    with caplog.at_level(logging.WARNING):
        DreamTriggerPolicyMixin._log_budget_exhausted(daemon, "short_window", 1)
        DreamTriggerPolicyMixin._log_budget_exhausted(daemon, "short_window", 1)
        daemon.dream_counter = 4
        DreamTriggerPolicyMixin._log_budget_exhausted(daemon, "short_window", 1)

    budget_records = [record for record in caplog.records if "Dream budget exhausted" in record.message]
    assert len(budget_records) == 2
    assert "pending_self_triggers=1" in budget_records[0].message
