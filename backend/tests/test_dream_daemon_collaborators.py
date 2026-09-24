"""Compatibility checks for the split dream-daemon collaborators."""

from backend.metabolisation.daemon import AutopoieticDreamDaemon
from backend.metabolisation.dream_execution import DreamExecutionMixin
from backend.metabolisation.dream_maintenance import DreamMaintenanceMixin
from backend.metabolisation.dream_trigger_policy import DreamTriggerPolicyMixin


def test_daemon_composes_extracted_policy_execution_and_maintenance() -> None:
    assert issubclass(AutopoieticDreamDaemon, DreamTriggerPolicyMixin)
    assert issubclass(AutopoieticDreamDaemon, DreamExecutionMixin)
    assert issubclass(AutopoieticDreamDaemon, DreamMaintenanceMixin)

    assert AutopoieticDreamDaemon.check_and_trigger_dream is DreamTriggerPolicyMixin.check_and_trigger_dream
    assert AutopoieticDreamDaemon._execute_self_triggered_dream is DreamExecutionMixin._execute_self_triggered_dream
    assert AutopoieticDreamDaemon.backfill_structure_on_idle is DreamMaintenanceMixin.backfill_structure_on_idle
    assert AutopoieticDreamDaemon.compact_memory is DreamMaintenanceMixin.compact_memory


def test_daemon_remains_the_lifecycle_owner() -> None:
    lifecycle_methods = {"__init__", "start", "stop", "aclose", "_run_loop"}
    assert lifecycle_methods <= AutopoieticDreamDaemon.__dict__.keys()
