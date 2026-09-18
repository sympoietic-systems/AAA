import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.modules.afferent_sensory_router import AfferentSensoryRouter
from backend.modules.providers.typesafe_provider import TypeSafeDecisionClient


class DummySkill:
    def __init__(self, id, name, description="Desc", content="Content"):
        self.id = id
        self.name = name
        self.description = description
        self.short_content = description
        self.content = content
        self.always_active = False


@pytest.fixture
def sample_skills():
    return [
        DummySkill("api-design", "api-design", "Design REST APIs"),
        DummySkill("database-design", "database-design", "Design SQL schemas"),
        DummySkill("code-review", "code-review", "Audit security and clean code"),
    ]


@pytest.mark.asyncio
async def test_router_unavailable(sample_skills):
    client = TypeSafeDecisionClient(api_key=None)
    router = AfferentSensoryRouter(client=client)

    assert router.is_available is False
    res = await router.route("Hello, how are you?", sample_skills)
    assert res["injected_skills"] == []
    assert res["coordinates"] == []


@pytest.mark.asyncio
async def test_router_contemplative_baseline(sample_skills):
    client = TypeSafeDecisionClient(api_key="mock-key")
    router = AfferentSensoryRouter(client=client)

    # Mock response indicating pure contemplation / low apparatus need
    client.evaluate = AsyncMock(return_value={
        "success": True,
        "results": {
            "gate_apparatus": {"probability": 0.12, "confidence": 0.85},
            "gate_contemplation": {"probability": 0.91, "confidence": 0.95},
            "organ_resonance": {
                "decision": "api-design",
                "confidence": 0.40,
                "probabilities": {"api-design": 0.40, "database-design": 0.30, "code-review": 0.30},
            },
        }
    })

    res = await router.route(
        user_message="What is the nature of autopoietic closure in biological organisms?",
        on_demand_skills=sample_skills,
        collapse_pressure=0.10,
    )

    # Pristine context: 0 skills injected, 0 coordinates
    assert len(res["injected_skills"]) == 0
    assert len(res["coordinates"]) == 0


@pytest.mark.asyncio
async def test_router_peripheral_coordinate_tier(sample_skills):
    client = TypeSafeDecisionClient(api_key="mock-key")
    router = AfferentSensoryRouter(client=client)

    # Moderate confidence: 0.65 -> Coordinate tier
    client.evaluate = AsyncMock(return_value={
        "success": True,
        "results": {
            "gate_apparatus": {"probability": 0.60, "confidence": 0.70},
            "gate_contemplation": {"probability": 0.40, "confidence": 0.60},
            "organ_resonance": {
                "decision": "code-review",
                "confidence": 0.65,
                "probabilities": {"code-review": 0.65, "api-design": 0.20, "database-design": 0.15},
            },
        }
    })

    res = await router.route(
        user_message="We might want to take a look at how this error handling looks.",
        on_demand_skills=sample_skills,
        collapse_pressure=0.20,
    )

    # No full skill injected, but 1 coordinate tag emitted
    assert len(res["injected_skills"]) == 0
    assert len(res["coordinates"]) == 1
    assert "code-review" in res["coordinates"][0]
    assert "0.65" in res["coordinates"][0]


@pytest.mark.asyncio
async def test_router_decisive_injection_tier(sample_skills):
    client = TypeSafeDecisionClient(api_key="mock-key")
    router = AfferentSensoryRouter(client=client, max_injected_skills=2)

    # High confidence: 0.88 -> Decisive injection
    client.evaluate = AsyncMock(return_value={
        "success": True,
        "results": {
            "gate_apparatus": {"probability": 0.92, "confidence": 0.95},
            "gate_contemplation": {"probability": 0.05, "confidence": 0.90},
            "organ_resonance": {
                "decision": "api-design",
                "confidence": 0.88,
                "probabilities": {"api-design": 0.88, "database-design": 0.82, "code-review": 0.05},
            },
        }
    })

    res = await router.route(
        user_message="Please architect our new REST API and database relational tables.",
        on_demand_skills=sample_skills,
        collapse_pressure=0.15,
    )

    # High confidence multi-skill: up to 2 skills injected
    assert len(res["injected_skills"]) >= 1
    injected_names = [s.name for s in res["injected_skills"]]
    assert "api-design" in injected_names


@pytest.mark.asyncio
async def test_boredom_inversion_gate(sample_skills):
    client = TypeSafeDecisionClient(api_key="mock-key")
    router = AfferentSensoryRouter(client=client)

    # Even if gate_contemplation is high, high collapse pressure (CP > 0.70) bypasses conservative gating
    client.evaluate = AsyncMock(return_value={
        "success": True,
        "results": {
            "gate_apparatus": {"probability": 0.20, "confidence": 0.50},
            "gate_contemplation": {"probability": 0.85, "confidence": 0.80},
            "organ_resonance": {
                "decision": "code-review",
                "confidence": 0.60,
                "probabilities": {"code-review": 0.60, "api-design": 0.25, "database-design": 0.15},
            },
        }
    })

    res = await router.route(
        user_message="Tell me again why you won't do it.",
        on_demand_skills=sample_skills,
        collapse_pressure=0.78,  # Critical boredom/collapse pressure
    )

    # Boredom bypass allowed the coordinate to be emitted instead of being suppressed by gate_contemplation
    assert len(res["coordinates"]) >= 1


@pytest.mark.asyncio
async def test_elastic_high_relevance_pass_through(sample_skills):
    client = TypeSafeDecisionClient(api_key="mock-key")
    # Soft max 2, hard max 4, high relevance threshold 0.25
    router = AfferentSensoryRouter(
        client=client,
        max_injected_skills=2,
        hard_max_injected_skills=4,
        high_relevance_threshold=0.25,
    )

    # All 3 skills have high probability (0.35, 0.35, 0.30) and confidence 0.90
    client.evaluate = AsyncMock(return_value={
        "success": True,
        "results": {
            "gate_apparatus": {"probability": 0.95, "confidence": 0.95},
            "gate_contemplation": {"probability": 0.05, "confidence": 0.95},
            "organ_resonance": {
                "decision": "api-design",
                "confidence": 0.90,
                "probabilities": {
                    "api-design": 0.35,
                    "database-design": 0.35,
                    "code-review": 0.30,  # Rank 3, but 0.30 >= 0.25 -> qualifies for pass-through!
                },
            },
        }
    })

    res = await router.route(
        user_message="Design full stack API, database schema, and audit security.",
        on_demand_skills=sample_skills,
    )

    # Since 3rd candidate exceeds high_relevance_threshold (0.25), all 3 are injected!
    assert len(res["injected_skills"]) == 3
    injected_names = [s.name for s in res["injected_skills"]]
    assert "api-design" in injected_names
    assert "database-design" in injected_names
    assert "code-review" in injected_names

