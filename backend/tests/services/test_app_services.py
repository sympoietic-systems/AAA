import subprocess
import sys
from dataclasses import MISSING, fields

import pytest
from fastapi import HTTPException
from starlette.datastructures import State

from backend.api.deps import get_app_services, get_message_repo, get_skill_service
from backend.bootstrap.services import AppServices, bind_legacy_state_aliases


def _services() -> AppServices:
    values = {
        field.name: object()
        for field in fields(AppServices)
        if field.default is MISSING and field.default_factory is MISSING
    }
    values.update(
        config={},
        agent_name="symbia",
        pipeline_order=[],
        system_prompt_tokens=0,
        background_provider=None,
        vision_provider=None,
    )
    return AppServices(**values)  # type: ignore[arg-type]


def test_v32_legacy_state_aliases_are_object_identical() -> None:
    state = State()
    services = _services()

    bind_legacy_state_aliases(state, services)

    assert state.services is services
    for field in fields(services):
        assert getattr(state, field.name) is getattr(services, field.name)


def test_v35_dependency_getter_honors_diverged_legacy_override() -> None:
    state = State()
    services = _services()
    bind_legacy_state_aliases(state, services)
    override = object()
    state.message_repo = override

    assert get_message_repo(state) is override

    bind_legacy_state_aliases(state, services)
    assert get_message_repo(state) is services.message_repo


def test_v35_service_factory_honors_diverged_legacy_override() -> None:
    state = State()
    services = _services()
    bind_legacy_state_aliases(state, services)
    state.skill_repo = object()

    assert get_skill_service(state)._state is state


def test_v24_missing_dependency_is_structured_503() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_message_repo(State())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Message repo is not initialized"


def test_v24_missing_app_services_is_structured_503() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_app_services(State())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Application services are not initialized"


def test_v22_bootstrap_leaf_import_does_not_eagerly_load_lifecycle() -> None:
    code = """
import sys
import backend.bootstrap.services

assert "backend.bootstrap.background" not in sys.modules
assert "backend.bootstrap.lifecycle" not in sys.modules
"""
    subprocess.run([sys.executable, "-c", code], check=True)
