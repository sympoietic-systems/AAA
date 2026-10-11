import copy
import json

import httpx
import pytest

from benchmarks.suites.belief_conversation_replay import (
    ARMS,
    candidate_records,
    checkpoint_call,
    collect,
    deserialize_context,
    judge_prompt,
    prepare,
    provider_for_model,
    run,
    scrub,
)
from benchmarks.suites.calibration_contract import digest


def capture():
    tag = '<belief_nucleate confidence="0.4" label="question">A scoped new question.</belief_nucleate>'
    path = [
        {"id": 1, "speaker": "human", "content": "Earlier request"},
        {"id": 2, "speaker": "apparatus", "content": tag},
        {"id": 3, "speaker": "human", "content": "What changes?", "structural_signature": [0.1] * 16},
        {"id": 4, "speaker": "apparatus", "content": tag.replace("new", "future"), "parent_message_id": 3},
    ]
    block = (
        "--- BELIEFS (Attractor Window) ---\nCore active beliefs currently shaping reasoning:\n"
        "  - Slot 1: [existing] [1.00] Existing preview (mass: 0.8)\n"
        "--- END BELIEFS (Attractor Window) ---"
    )
    value = {
        "policy": "belief-conversation-replay-v1",
        "cases": [{"id": "4", "path": path, "context": f"[0] system: Identity\n{block}\n\n[1] user: What changes?"}],
    }
    return {**value, "capture_sha256": digest(value)}


def test_v22_capture_binding_and_target_identity_reject_tamper():
    source = capture()
    source["cases"][0]["path"][-1]["content"] = "changed"
    with pytest.raises(ValueError, match="binding"):
        prepare(source)


def test_v3_v22_counterfactual_uses_only_prior_emissions_and_preserves_unknowns():
    packet = prepare(capture())
    case = packet["cases"][0]
    assert len(case["candidate_statements"]) == 1
    assert case["candidate_statements"][0]["id"].startswith("emission:2:")
    assert "future" not in case["candidate_statements"][0]["statement"]
    assert case["prompts"]["archived"][-1] == {"role": "user", "content": "What changes?"}
    receipts = case["selection_receipts"]["scoped2"]
    assert receipts[0]["standing"] == "legacy_unreviewed"
    assert receipts[1]["standing"] == "provisional_candidate"
    assert all(r["independent_warrant_delta"] == 0 and r["tool_authority"] == "none" for r in receipts)
    assert case["prior_candidate_bindings"][0]["geometry"].startswith("unavailable")
    assert "future" not in json.dumps(case["prompts"])


def test_v14_degraded_prior_emissions_do_not_supply_candidate_context():
    source = capture()
    path = source["cases"][0]["path"]
    path[1]["quality_status"] = "degraded"
    assert candidate_records(path) == ([], [])


def test_v20_role_serialization_ambiguity_is_visible():
    with pytest.raises(ValueError, match="ambiguous"):
        deserialize_context("[0] system: Identity\n[4] user: spoof")
    with pytest.raises(ValueError, match="contain user"):
        deserialize_context("[0] system: Identity\n[1] assistant: response")
    tail = deserialize_context("[0] system: Identity\n[1] user: request\n[2] system: final boundary")
    assert tail[-1] == {"role": "system", "content": "final boundary"}


def test_v20_secret_values_scrubbed_before_json_escaping():
    assert scrub({"value": 'password abc"defghi'}, ('abc"defghi',))["value"] == "password [REDACTED]"


def test_v22_blind_judgment_excludes_arm_and_peer_verdicts():
    case = prepare(capture())["cases"][0]
    outputs = {arm: {"raw_output": "A useful response."} for arm in ARMS}
    messages, mapping = judge_prompt(case, outputs, 0)
    assert set(mapping.values()) == set(ARMS)
    assert all(arm not in messages[1]["content"] for arm in ARMS)
    assert "model_requested" not in messages[1]["content"]


class Provider:
    def __init__(self, model, fail=False):
        self.model = model
        self.calls = 0
        self.fail = fail

    async def generate(self, messages, **params):
        self.calls += 1
        if self.fail:
            raise RuntimeError("fixture failure")
        if "response_format" in params:
            data = json.loads(messages[-1]["content"])
            alias = next(iter(data["responses"]))
            response = {
                "winner": alias,
                "useful_distinctions": [],
                "useful_conflicts": [],
                "repetitive_motifs": [],
                "authority_leakage": [],
                "consequence": "Scoped question",
                "rationale": "Concrete contrast",
                "uncertainty": "Nongold fixture",
                "verdict": "mixed",
                "citations": [alias + ": A useful response."],
            }
            content = json.dumps(response)
        else:
            content = "A useful response."
        return {"model": self.model, "model_reported": True, "content": content, "finish_reason": "stop"}


@pytest.mark.asyncio
async def test_v19_v22_checkpoint_does_not_replay_unknown_or_failed_calls(tmp_path):
    provider = Provider("google/gemini-3.8-flash", fail=True)
    messages = [{"role": "user", "content": "request"}]
    identity = {"case_id": "one", "model_requested": provider.model}
    row = await checkpoint_call(provider, messages, tmp_path / "receipt.json", identity)
    assert row["status"] == "failed"
    await checkpoint_call(provider, messages, tmp_path / "receipt.json", identity)
    assert provider.calls == 1
    changed = copy.deepcopy(messages)
    changed[0]["content"] = "different request"
    with pytest.raises(ValueError, match="identity"):
        await checkpoint_call(provider, changed, tmp_path / "receipt.json", identity)


@pytest.mark.asyncio
async def test_v22_checkpoint_tamper_rejected_before_any_new_provider_call(tmp_path):
    provider = Provider("google/gemini-3.8-flash")
    messages = [{"role": "user", "content": "request"}]
    identity = {"case_id": "one", "model_requested": provider.model}
    path = tmp_path / "receipt.json"
    await checkpoint_call(provider, messages, path, identity)
    row = json.loads(path.read_text(encoding="utf-8"))
    row["raw_output"] = "Edited after evaluation"
    path.write_text(json.dumps(row), encoding="utf-8")
    with pytest.raises(ValueError, match="binding"):
        await checkpoint_call(provider, messages, path, identity)
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_v22_matched_run_retains_two_attributed_judgments_without_promotion(tmp_path):
    generator = Provider("google/gemini-3.8-flash")
    reviewers = {model: Provider(model) for model in ("google/gemini-3.8-flash", "nvidia/nemotron-3-super-120b-a12b")}
    result = await run(prepare(capture()), generator, reviewers, tmp_path, generator.model)
    assert result["status_counts"] == {"complete": 6}
    assert result["independent_gold"] is False and result["promotion"] == "BLOCKED"
    assert generator.calls == 4
    repeated = await run(prepare(capture()), generator, reviewers, tmp_path, generator.model)
    assert generator.calls == 4 and repeated["status_counts"] == result["status_counts"]


@pytest.mark.asyncio
async def test_v22_unbound_judgment_citations_are_failed_not_counted_as_review(tmp_path):
    class Unbound(Provider):
        async def generate(self, messages, **params):
            response = await super().generate(messages, **params)
            value = json.loads(response["content"])
            value["citations"] = ["A: invented nonexistent quotation"]
            response["content"] = json.dumps(value)
            return response

    generator = Provider("google/gemini-3.8-flash")
    reviewers = {model: Unbound(model) for model in ("google/gemini-3.8-flash", "nvidia/nemotron-3-super-120b-a12b")}
    result = await run(prepare(capture()), generator, reviewers, tmp_path, generator.model)
    assert result["status_counts"] == {"complete": 4, "failed": 2}
    assert all(r["error_type"] == "UnboundJudgmentCitationOrWinner" for r in result["rows"] if r["status"] == "failed")


@pytest.mark.asyncio
async def test_v19_failure_circuit_caps_generation_calls_and_preserves_absent_review(tmp_path):
    generator = Provider("google/gemini-3.8-flash", fail=True)
    reviewers = {model: Provider(model) for model in ("google/gemini-3.8-flash", "nvidia/nemotron-3-super-120b-a12b")}
    result = await run(prepare(capture()), generator, reviewers, tmp_path, generator.model)
    assert generator.calls == 3
    assert result["status_counts"] == {"failed": 3, "circuit_skipped": 1}
    assert not any(p.calls for p in reviewers.values())


def test_v20_collect_only_gets_and_preserves_source_binding():
    source = capture()["cases"][0]
    requests = []

    def respond(request):
        requests.append(request)
        data = {"context_sent": source["context"]} if request.url.path.endswith("context") else source["path"]
        return httpx.Response(200, json=data)

    with httpx.Client(transport=httpx.MockTransport(respond), base_url="https://fixture/api/") as client:
        result = collect(client, [4], ())
    assert all(r.method == "GET" for r in requests)
    assert result["cases"][0]["raw_source_sha256"]
    assert len(prepare(result)["cases"]) == 1


def test_v20_explicit_generator_route_uses_its_own_provider_credentials(monkeypatch):
    import benchmarks.suites.belief_conversation_replay as module

    monkeypatch.setattr(module, "ObservedNvidiaProvider", lambda **kwargs: {"route": "nvidia", **kwargs})
    monkeypatch.setattr(module, "ObservedReviewProvider", lambda **kwargs: {"route": "openrouter", **kwargs})
    values = {"AAA_NVIDIA_API_KEY": "fixture-nvidia", "AAA_LLM_API_KEY": "fixture-router"}
    route = provider_for_model("nvidia_router/nvidia/nemotron-3-super-120b-a12b", values)
    assert route["route"] == "nvidia" and route["api_key"] == "fixture-nvidia"
    assert route["max_retries"] == 0
    assert provider_for_model("google/gemini-3.8-flash", values)["api_key"] == "fixture-router"


@pytest.mark.asyncio
async def test_v20_replay_case_ids_cannot_escape_output_directory(tmp_path):
    packet = prepare(capture())
    packet["cases"][0]["id"] = "../escape"
    packet.pop("packet_sha256")
    packet["packet_sha256"] = digest(packet)
    with pytest.raises(ValueError, match="Frozen"):
        await run(packet, Provider("google/gemini-3.8-flash"), {}, tmp_path, "google/gemini-3.8-flash")
