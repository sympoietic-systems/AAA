import json
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.storage.database import init_db, get_db_path
from backend.storage.repositories.research_task import ResearchTaskRepository
from backend.storage.repositories.research_plan import ResearchPlanRepository
from backend.storage.repositories.research_step import ResearchStepRepository
from backend.services.research.orchestrator import SomaticResearchOrchestrator

DB_PATH = str(get_db_path("data/aaa_test.db"))


def _make_task_id():
    return str(uuid.uuid4())


def _create_task(repo, task_id, **overrides):
    repo.create({
        "id": task_id,
        "title": overrides.get("title", "Test Task"),
        "objective": overrides.get("objective", "Research objective"),
        "trigger_source": overrides.get("trigger_source", "test"),
        "status": overrides.get("status", "active"),
        "priority": overrides.get("priority", 1),
        "conversation_id": overrides.get("conversation_id", None),
        "max_depth": overrides.get("max_depth", 3),
        "max_breadth": overrides.get("max_breadth", 4),
        "budget_limit_usd": overrides.get("budget_limit_usd", 0.50),
    })


def _make_mock_state():
    state = MagicMock()
    state.config = {
        "research_orchestrator": {
            "max_reflect_rounds": 3,
            "default_top_n": 3,
            "satisfaction_threshold": 0.7,
            "early_stop_threshold": 0.8,
            "max_concurrent_parses": 3,
            "upload_dir": "data/uploads/research",
            "html_archive": False,
        }
    }
    state.llm_provider = None
    state.structural_provider = None
    return state


class TestExecuteStepRouting:
    @pytest.mark.asyncio
    async def test_step_plan_transitions_to_searching(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        plan_repo = ResearchPlanRepository(DB_PATH)
        step_repo = ResearchStepRepository(DB_PATH)
        _create_task(task_repo, task_id)

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_plan_repo = plan_repo
        state_mock.research_step_repo = step_repo
        state_mock.research_step_result_repo = MagicMock()
        state_mock.research_meta_log_repo = MagicMock()
        state_mock.scraped_asset_repo = MagicMock()
        state_mock.research_branch_repo = MagicMock()
        state_mock.llm_provider = None
        state_mock.structural_provider = None
        state_mock.skill_repo = None
        state_mock.commitment_repo = None
        state_mock.belief_repo = None

        orch = SomaticResearchOrchestrator(state_mock)
        orch._state_mgr.states[task_id] = {
            "phase": "planning",
            "objective": "Research objective",
            "max_depth": 3, "budget": 0.5,
            "plan_id": None, "plan": None, "all_findings": [],
            "sources_analyzed": 0, "stagnation_counter": 0, "step_number": 0,
            "last_reflection": {}, "current_depth": 0, "query_index": 0,
            "search_results_cache": [], "parsed_sources_cache": [],
            "digest_results_cache": [], "should_stop": False, "stop_reason": "",
        }

        result = await orch.execute_step(task_id)

        s = orch._state_mgr.states[task_id]
        assert s["phase"] == "searching"
        assert s["plan_id"] is not None
        assert "search_queries" in s["plan"]
        assert s.get("phase_group") == 1

        conn.close()

    @pytest.mark.asyncio
    async def test_step_plan_increments_step_number(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        plan_repo = ResearchPlanRepository(DB_PATH)
        step_repo = ResearchStepRepository(DB_PATH)
        _create_task(task_repo, task_id)

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_plan_repo = plan_repo
        state_mock.research_step_repo = step_repo
        state_mock.research_step_result_repo = MagicMock()
        state_mock.research_meta_log_repo = MagicMock()
        state_mock.scraped_asset_repo = MagicMock()
        state_mock.research_branch_repo = MagicMock()
        state_mock.llm_provider = None
        state_mock.structural_provider = None
        state_mock.skill_repo = None
        state_mock.commitment_repo = None
        state_mock.belief_repo = None

        orch = SomaticResearchOrchestrator(state_mock)
        orch._state_mgr.states[task_id] = {
            "phase": "planning",
            "objective": "Test", "max_depth": 3, "budget": 0.5,
            "plan_id": None, "plan": None, "all_findings": [],
            "sources_analyzed": 0, "stagnation_counter": 0, "step_number": 5,
            "last_reflection": {}, "current_depth": 0, "query_index": 0,
            "search_results_cache": [], "parsed_sources_cache": [],
            "digest_results_cache": [], "should_stop": False, "stop_reason": "",
            "phase_group": 5, "last_block": "",
        }

        await orch.execute_step(task_id)

        assert orch._state_mgr.states[task_id]["phase"] == "searching"
        assert orch._state_mgr.states[task_id]["phase_group"] == 6

        conn.close()


class TestPreviewCacheMechanism:
    def test_preview_returns_cached_result_on_second_call(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        _create_task(task_repo, task_id)

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        cache_key = "planning"
        dummy_cache = {"phase": "planning", "system_prompt": "test prompt", "user_prompt": "test user"}
        orch._save_cache(task_id, {cache_key: dummy_cache})

        loaded = orch._get_cached_phase(task_id, cache_key)
        assert loaded is not None
        assert loaded["system_prompt"] == "test prompt"
        assert loaded["user_prompt"] == "test user"

        conn.close()

    def test_cache_miss_returns_none(self):
        state_mock = _make_mock_state()
        state_mock.research_task_repo = ResearchTaskRepository(DB_PATH)
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        result = orch._get_cached_phase("no-such-task", "planning")
        assert result is None

    def test_reinitialize_clears_cache(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        _create_task(task_repo, task_id)

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_meta_log_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        orch._save_cache(task_id, {"planning": {"cached": True}})

        cached = orch._get_cached_phase(task_id, "planning")
        assert cached is not None

        orch.reinitialize(task_id)
        cached_after = orch._get_cached_phase(task_id, "planning")
        assert cached_after is None

        conn.close()


class TestPhasePlanFallback:
    @pytest.mark.asyncio
    async def test_phase_plan_uses_fallback_when_no_llm_provider(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        plan_repo = ResearchPlanRepository(DB_PATH)
        _create_task(task_repo, task_id)

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_plan_repo = plan_repo
        state_mock.research_meta_log_repo = MagicMock()
        state_mock.llm_provider = None
        state_mock.structural_provider = None
        state_mock.skill_repo = None
        state_mock.commitment_repo = None
        state_mock.belief_repo = None

        orch = SomaticResearchOrchestrator(state_mock)
        from backend.services.research.steps.plan import run_plan_generation
        result = await run_plan_generation(orch, task_id, "Test objective", 3, 0.5, "")

        assert "id" in result
        assert result["goal"] == "Test objective"
        assert result["search_queries"] == ["Test objective"]
        assert result["n_results_per_query"] == 3
        assert result["estimated_depth"] == 1

        conn.close()


class TestDocumentDigestionStep:
    @pytest.mark.asyncio
    async def test_execute_document_digestion_with_plan_id(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        step_repo = ResearchStepRepository(DB_PATH)
        plan_repo = ResearchPlanRepository(DB_PATH)
        _create_task(task_repo, task_id)

        plan_id = str(uuid.uuid4())
        plan_repo.create({
            "id": plan_id,
            "task_id": task_id,
            "plan_json": json.dumps({
                "goal": "Test goal",
                "search_queries": ["query"],
                "n_results_per_query": 3,
                "estimated_depth": 1,
            })
        })

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_step_repo = step_repo
        state_mock.research_step_result_repo = MagicMock()
        state_mock.research_meta_log_repo = MagicMock()
        state_mock.perception_repo = MagicMock()
        state_mock.perception_repo.find_file_by_name.return_value = {"status": "ready", "summary": "doc summary", "conversation_id": "conv-1"}
        chunk_mock = MagicMock()
        chunk_mock.chunk_text = "some relevant document content"
        state_mock.perception_repo.get_by_file.return_value = [chunk_mock]

        with patch("backend.services.research.steps.digest.analyze_source_content", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = {"learnings": ["learning 1"], "followups": [], "gaps": []}
            
            from backend.services.research.steps.document_digestion import DocumentDigestionStep
            from backend.services.research.task_state import StepEnvelope, DocDigestPayload

            orch = SomaticResearchOrchestrator(state_mock)
            orch._state_mgr.states[task_id] = {
                "phase": "document_digestion",
                "objective": "Test document",
                "max_depth": 3,
                "budget": 0.5,
                "plan_id": plan_id,
                "step_number": 1,
                "current_depth": 0,
            }

            envelope = StepEnvelope(
                task_id=task_id,
                objective="Test document",
                current_depth=0,
                max_depth=3,
                budget=0.5,
                plan_id=plan_id,
                payload=DocDigestPayload(
                    inject_file_id="doc.txt",
                    document_mode="summary",
                    document_chunk_limit=5
                )
            )

            step = DocumentDigestionStep()
            output = await step.execute(orch, envelope)

            assert output.status == "completed"
            assert len(output.payload.learnings) == 1

        conn.close()


class TestReflectionFindingsInclusion:
    @pytest.mark.asyncio
    async def test_reflect_includes_digested_and_historical_findings(self):
        from backend.services.research.steps.consolidate import run_consolidation

        orch = MagicMock()
        orch.step_repo = MagicMock()
        orch.step_result_repo = MagicMock()
        orch._get_parsed_urls.return_value = [
            {"url": "document:doc.pdf", "title": "doc.pdf", "status": "ok"},
            {"url": "https://other.com", "title": "other.com", "status": "ok"},
        ]
        
        # Mock step list
        orch.step_repo.get_by_task.return_value = [
            {"id": "step1", "step_type": "document_digestion", "step_data": json.dumps({"depth": 0})},
            {"id": "step2", "step_type": "parallel_parse", "step_data": json.dumps({"depth": 0})},
        ]
        
        # Mock step results
        def get_by_step_mock(step_id):
            if step_id == "step1":
                return [{
                    "source_title": "doc.pdf",
                    "source_url": "document:doc.pdf",
                    "analyzed_json": json.dumps({
                        "learnings": ["digestion learning 1"],
                        "followups": [],
                        "gaps": []
                    })
                }]
            elif step_id == "step2":
                return [{
                    "source_title": "other.com",
                    "source_url": "https://other.com",
                    "analyzed_json": json.dumps({
                        "learnings": ["web learning 1"],
                        "followups": [],
                        "gaps": []
                    })
                }]
            return []

        orch.step_result_repo.get_by_step.side_effect = get_by_step_mock
        orch._get_step_depth = lambda s: json.loads(s.get("step_data") or "{}").get("depth", 0)
        orch._format_reflection_markdown.return_value = ""

        all_findings = [
            "[doc.pdf]: digestion learning 1",
            "[other.com]: web learning 1",
        ]

        with patch("backend.services.research.steps.consolidate.generate_unified", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = {"json_data": {}}
            await run_consolidation(
                orch,
                task_id="task-id",
                objective="Test obj",
                goal="Test goal",
                depth=0,
                max_depth=3,
                all_findings=all_findings,
                previous_reflection={},
                digest_signals={},
                step_id="step-id"
            )
            
            called_args, called_kwargs = mock_generate.call_args
            user_prompt = called_kwargs.get("user_prompt", "")
            
            assert "digestion learning 1" in user_prompt
            assert "web learning 1" in user_prompt


class TestMultiCycleContinuation:
    @pytest.mark.asyncio
    async def test_continue_task_and_synthesis_reporting(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        step_repo = ResearchStepRepository(DB_PATH)
        _create_task(task_repo, task_id, status="completed", max_depth=3)
        task_repo.update(task_id, result_summary="Original Synthesis Report")

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_step_repo = step_repo
        state_mock.research_step_result_repo = MagicMock()
        state_mock.research_meta_log_repo = MagicMock()
        state_mock.scraped_asset_repo = MagicMock()
        state_mock.research_branch_repo = MagicMock()

        # Create a dummy plan to satisfy foreign key constraint on research_steps
        plan_id = f"plan-{task_id}"
        plan_repo = ResearchPlanRepository(DB_PATH)
        plan_repo.create({
            "id": plan_id,
            "task_id": task_id,
            "plan_json": "{}",
            "status": "active"
        })

        from backend.services.research.task_manager import ResearchTaskManager
        manager = ResearchTaskManager(state_mock)
        manager._orchestrator = SomaticResearchOrchestrator(state_mock)

        # 1. Test continuation: old result_summary is preserved, depth is incremented
        with patch.object(ResearchTaskManager, "_execute_continued_task", return_value=AsyncMock()) as mock_exec:
            manager.continue_task(task_id, additional_cycles=1)
        task = task_repo.get(task_id)
        assert task["status"] == "active"
        assert task["max_depth"] == 1  # set to current_depth for hard-stop after one cycle
        assert task["result_summary"] == "Original Synthesis Report"

        # 2. Check orchestrator_state has correct depth
        import json
        orch_state = json.loads(task["orchestrator_state"])
        assert orch_state["current_depth"] == 1
        assert orch_state["max_depth"] == 1  # one cycle then hard-stop
        assert orch_state["previous_context"] == "Original Synthesis Report"

        # 3. Verify synthesis step saves report to step_data JSON
        from backend.services.research.steps.synthesize import SynthesizeStep
        from backend.services.research.task_state import StepEnvelope, SynthesizePayload

        # Initialize the orchestrator state manager for this task
        manager.orchestrator._state_mgr.states[task_id] = {
            "phase": "synthesizing",
            "objective": "Research objective",
            "max_depth": 4,
            "budget": 0.50,
            "plan_id": plan_id,
            "plan": {"goal": "Test goal"},
            "all_findings": [],
            "sources_analyzed": 0,
            "stagnation_counter": 0,
            "step_number": 2,
            "last_reflection": {},
            "current_depth": 1,
            "query_index": 0,
            "search_results_cache": [],
            "parsed_sources_cache": [],
            "digest_results_cache": [],
            "should_stop": False,
            "stop_reason": "",
        }

        envelope = StepEnvelope(
            task_id=task_id,
            objective="Research objective",
            current_depth=1,
            max_depth=4,
            budget=0.50,
            all_findings=["Finding 1"],
            payload=SynthesizePayload(sources_analyzed=5)
        )

        with patch("backend.services.research.steps.synthesize.run_synthesis", new_callable=AsyncMock) as mock_synth:
            mock_synth.return_value = "New Cycle 2 Report"
            step = SynthesizeStep()
            await step.execute(manager.orchestrator, envelope)

            # Check that task's result_summary is updated
            updated_task = task_repo.get(task_id)
            assert updated_task["result_summary"] == "New Cycle 2 Report"

            # Check that step_repo has step_data with report_markdown
            steps = step_repo.get_by_task(task_id)
            synth_steps = [s for s in steps if s["step_type"] == "synthesize"]
            assert len(synth_steps) > 0
            latest_synth = synth_steps[-1]
            step_data = json.loads(latest_synth["step_data"])
            assert step_data["report_markdown"] == "New Cycle 2 Report"
            assert step_data["depth"] == 1

        conn.close()


class TestPureReflectionInclusion:
    @pytest.mark.asyncio
    async def test_pure_reflection_calls_llm_with_metrics(self):
        from backend.services.research.steps.reflect import run_deep_reflection

        orch = MagicMock()
        orch.step_repo = MagicMock()
        orch.step_result_repo = MagicMock()
        orch._build_orchestrator_persona = AsyncMock(return_value="Mocked Persona")
        orch._get_parsed_urls.return_value = [
            {"url": "document:doc.pdf", "title": "doc.pdf", "status": "ok"},
            {"url": "https://other.com", "title": "other.com", "status": "ok"},
        ]

        # Mock steps
        orch.step_repo.get_by_task.return_value = [
            {"id": "step1", "step_type": "document_digestion", "step_data": json.dumps({"depth": 0})},
            {"id": "step2", "step_type": "parallel_parse", "step_data": json.dumps({"depth": 0})},
        ]

        # Mock step results
        def get_by_step_mock(step_id):
            if step_id == "step1":
                return [{
                    "source_title": "doc.pdf",
                    "source_url": "document:doc.pdf",
                    "analyzed_json": json.dumps({
                        "learnings": ["digestion learning 1"],
                        "followups": [],
                        "gaps": ["gap 1"]
                    })
                }]
            elif step_id == "step2":
                return [{
                    "source_title": "other.com",
                    "source_url": "https://other.com",
                    "analyzed_json": json.dumps({
                        "learnings": ["web learning 1"],
                        "followups": [],
                        "gaps": ["gap 2"]
                    })
                }]
            return []

        orch.step_result_repo.get_by_step.side_effect = get_by_step_mock
        orch._get_step_depth = lambda s: json.loads(s.get("step_data") or "{}").get("depth", 0)

        all_findings = [
            "[doc.pdf]: digestion learning 1",
            "[other.com]: web learning 1",
        ]

        with patch("backend.services.research.steps.reflect.generate_unified", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = {
                "json_data": {
                    "reflection_notes": "Highly integrated findings.",
                    "detected_biases": ["None"],
                    "knowledge_gaps": ["None"],
                    "glitch_fidelity": 1.0,
                    "contradiction_density": 0.0,
                    "source_entropy": 0.5,
                    "signal_flags": [],
                    "refined_queries": [],
                    "revised_confidence": 0.9,
                    "monologue_trace": [{"register": "Integration", "notes": "Done"}]
                }
            }

            res = await run_deep_reflection(
                orch,
                task_id="task-id",
                objective="Test pure reflection obj",
                depth=0,
                max_depth=3,
                all_findings=all_findings,
                step_id="step-id"
            )

            assert mock_generate.call_count == 3
            c1_kwargs = mock_generate.call_args_list[0][1]
            user_prompt_c1 = c1_kwargs.get("user_prompt", "")
            assert "digestion learning 1" in user_prompt_c1
            assert "web learning 1" in user_prompt_c1
            assert "Glitch Fidelity" in user_prompt_c1
            assert res["revised_confidence"] == 0.9
            assert res["reflection_notes"] == "Highly integrated findings."


class TestDynamicReroutingAndCacheClearance:
    @pytest.mark.asyncio
    async def test_reflection_reroutes_on_glitch_fidelity_low(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        plan_repo = ResearchPlanRepository(DB_PATH)
        step_repo = ResearchStepRepository(DB_PATH)
        _create_task(task_repo, task_id)

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_plan_repo = plan_repo
        state_mock.research_step_repo = step_repo
        state_mock.research_step_result_repo = MagicMock()
        state_mock.research_meta_log_repo = MagicMock()
        state_mock.scraped_asset_repo = MagicMock()
        state_mock.research_branch_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)
        
        # Seed cache to verify cache-clearance
        orch._save_cache(task_id, {"planning": {"cached_plan": True}})
        
        plan_id = f"plan-{task_id}"
        plan_repo.create({
            "id": plan_id,
            "task_id": task_id,
            "plan_json": json.dumps({"search_queries": []}),
            "status": "active"
        })

        # Setup task state in reflection phase
        orch._state_mgr.states[task_id] = {
            "phase": "reflection",
            "objective": "Research objective",
            "max_depth": 3, "budget": 0.5,
            "plan_id": plan_id, "plan": {"search_queries": []}, "all_findings": [],
            "sources_analyzed": 0, "stagnation_counter": 0, "step_number": 2,
            "last_reflection": {}, "current_depth": 0, "query_index": 0,
            "search_results_cache": [], "parsed_sources_cache": [],
            "digest_results_cache": [], "should_stop": False, "stop_reason": "",
        }

        # Mock the Reflection step logic to output GLITCH_FIDELITY_LOW flag
        from backend.services.research.steps.reflect import ReflectionPayload
        mock_payload = ReflectionPayload(
            reflection_notes="Low fidelity detected",
            signal_flags=["GLITCH_FIDELITY_LOW"],
            glitch_fidelity=0.2,
            contradiction_density=0.8,
            source_entropy=0.5,
            revised_confidence=0.3
        )

        with patch("backend.services.research.steps.reflect.ReflectionStep.execute", new_callable=AsyncMock) as mock_execute, \
             patch("backend.services.research.steps.evaluate.EvaluateStep.execute", new_callable=AsyncMock) as mock_eval_execute:
            # We mock execute to return our low fidelity output
            async def mock_exec(orch_inst, env):
                step_id = f"step-reflect-{task_id}"
                step_repo.create({
                    "id": step_id,
                    "task_id": task_id,
                    "plan_id": plan_id,
                    "step_number": 3,
                    "step_type": "reflection",
                    "step_data": mock_payload.model_dump_json(),
                    "status": "completed"
                })
                from backend.services.research.task_state import StepOutput
                return StepOutput(
                    status="completed",
                    message="Reflected",
                    payload=mock_payload,
                    signal_flags={"GLITCH_FIDELITY_LOW": True},
                    step_ids=[step_id]
                )
            
            mock_execute.side_effect = mock_exec

            async def mock_eval_exec(orch_inst, env):
                step_id = f"step-eval-{task_id}"
                step_repo.create({
                    "id": step_id,
                    "task_id": task_id,
                    "plan_id": plan_id,
                    "step_number": 4,
                    "step_type": "evaluate",
                    "step_data": json.dumps({}),
                    "status": "completed"
                })
                from backend.services.research.task_state import EvaluatePayload, StepOutput
                eval_payload = EvaluatePayload(
                    stagnation_counter=0,
                    sources_analyzed=0,
                    reflection=mock_payload.model_dump(),
                    should_stop=False,
                    stop_reason=""
                )
                return StepOutput(
                    status="completed",
                    message="Evaluated",
                    payload=eval_payload,
                    signal_flags={"should_stop": False, "GLITCH_FIDELITY_LOW": True},
                    step_ids=[step_id]
                )

            mock_eval_execute.side_effect = mock_eval_exec
            
            # Run the task step loop for reflection phase: should transition to evaluating
            await orch.execute_step(task_id)
            s = orch._state_mgr.states[task_id]
            assert s["phase"] == "evaluating"

            # Run the task step loop for evaluation phase: should transition to planning
            await orch.execute_step(task_id)

        # Check that state machine transitioned back to planning
        s = orch._state_mgr.states[task_id]
        assert s["phase"] == "planning"
        assert s["current_depth"] == 1
        assert s["query_index"] == 0

        # Check that planning cache was cleared
        cache = orch._load_cache(task_id)
        assert "planning" not in cache

        conn.close()

    @pytest.mark.asyncio
    async def test_reflection_bypasses_planning_when_depth_budget_exhausted(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        plan_repo = ResearchPlanRepository(DB_PATH)
        step_repo = ResearchStepRepository(DB_PATH)
        _create_task(task_repo, task_id)

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_plan_repo = plan_repo
        state_mock.research_step_repo = step_repo
        state_mock.research_step_result_repo = MagicMock()
        state_mock.research_meta_log_repo = MagicMock()
        state_mock.scraped_asset_repo = MagicMock()
        state_mock.research_branch_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)

        plan_id = f"plan-{task_id}"
        plan_repo.create({
            "id": plan_id,
            "task_id": task_id,
            "plan_json": json.dumps({"search_queries": []}),
            "status": "active"
        })

        # Setup task state in reflection phase at max depth (3/3)
        orch._state_mgr.states[task_id] = {
            "phase": "reflection",
            "objective": "Research objective",
            "max_depth": 3, "budget": 0.5,
            "plan_id": plan_id, "plan": {"search_queries": []}, "all_findings": [],
            "sources_analyzed": 0, "stagnation_counter": 0, "step_number": 2,
            "last_reflection": {}, "current_depth": 3, "query_index": 0,
            "search_results_cache": [], "parsed_sources_cache": [],
            "digest_results_cache": [], "should_stop": False, "stop_reason": "",
        }

        # Mock the Reflection step logic to output GLITCH_FIDELITY_LOW flag
        from backend.services.research.steps.reflect import ReflectionPayload
        mock_payload = ReflectionPayload(
            reflection_notes="Low fidelity detected",
            signal_flags=["GLITCH_FIDELITY_LOW"],
            glitch_fidelity=0.2,
            contradiction_density=0.8,
            source_entropy=0.5,
            revised_confidence=0.3
        )

        with patch("backend.services.research.steps.reflect.ReflectionStep.execute", new_callable=AsyncMock) as mock_execute:
            async def mock_exec(orch_inst, env):
                step_id = f"step-reflect-{task_id}"
                step_repo.create({
                    "id": step_id,
                    "task_id": task_id,
                    "plan_id": plan_id,
                    "step_number": 3,
                    "step_type": "reflection",
                    "step_data": mock_payload.model_dump_json(),
                    "status": "completed"
                })
                from backend.services.research.task_state import StepOutput
                return StepOutput(
                    status="completed",
                    message="Reflected",
                    payload=mock_payload,
                    signal_flags={"GLITCH_FIDELITY_LOW": True},
                    step_ids=[step_id]
                )

            mock_execute.side_effect = mock_exec

            # Run the task step loop for reflection phase: should transition to evaluating
            await orch.execute_step(task_id)
            s = orch._state_mgr.states[task_id]
            assert s["phase"] == "evaluating"
            assert s["current_depth"] == 3

            # Run the task step loop for evaluation phase (real execution): should transition to synthesizing
            await orch.execute_step(task_id)

        # Check that state machine transitioned to synthesizing instead of planning
        s = orch._state_mgr.states[task_id]
        assert s["phase"] == "synthesizing"
        # Depth should NOT be incremented
        assert s["current_depth"] == 3

        # Check that the depth limit stopping reason was recorded in the database step record for evaluation
        steps = step_repo.get_by_task(task_id)
        eval_steps = [st for st in steps if st["step_type"] == "evaluate"]
        assert len(eval_steps) == 1
        assert "depth limit reached" in eval_steps[0]["result_summary"]

        conn.close()

    @pytest.mark.asyncio
    async def test_planning_includes_detailed_reflection_monologue_and_critique_log(self):
        conn = init_db(DB_PATH)
        task_id = _make_task_id()
        task_repo = ResearchTaskRepository(DB_PATH)
        _create_task(task_repo, task_id)

        state_mock = _make_mock_state()
        state_mock.research_task_repo = task_repo
        state_mock.research_plan_repo = MagicMock()
        state_mock.research_step_repo = MagicMock()
        state_mock.research_step_result_repo = MagicMock()
        state_mock.research_meta_log_repo = MagicMock()
        state_mock.scraped_asset_repo = MagicMock()
        state_mock.research_branch_repo = MagicMock()

        orch = SomaticResearchOrchestrator(state_mock)

        # Setup task state with reflection notes, monologue_trace, and critique_log
        orch._state_mgr.states[task_id] = {
            "phase": "planning",
            "objective": "Test Objective",
            "max_depth": 3,
            "budget": 0.5,
            "plan_id": None,
            "plan": None,
            "all_findings": [],
            "sources_analyzed": 0,
            "stagnation_counter": 0,
            "step_number": 3,
            "last_reflection": {},
            "current_depth": 1,
            "query_index": 0,
            "search_results_cache": [],
            "parsed_sources_cache": [],
            "digest_results_cache": [],
            "should_stop": False,
            "stop_reason": "",
            "reflection_notes": "Epistemic Reflection: we are biased towards Western trauma metaphors.",
            "detected_biases": ["Western resilience bias"],
            "knowledge_gaps": ["Indigenous cosmologies"],
            "signal_flags": ["BIAS_DETECTED"],
            "glitch_fidelity": 0.9,
            "contradiction_density": 0.4,
            "source_entropy": 0.6,
            "revised_confidence": 0.35,
            "monologue_trace": [
                {"register": "framing_provenance", "utterance": "Deepened thought on kintsugi metaphor..."}
            ],
            "critique_log": [
                {
                    "register": "source_apparatus",
                    "severity": "SHALLOW",
                    "failure_description": "Vague gesture at Indigenous epistemologies.",
                    "suggestion": "Select a specific source like Diné Hózhó."
                }
            ],
            "diffractive_audit": "CEREMONIAL",
            "diffractive_audit_description": "Theoretical lens was just name-dropped."
        }

        # Let's preview the plan step
        from backend.services.research.task_state import PlanPayload, StepEnvelope
        envelope = StepEnvelope(
            task_id=task_id,
            objective="Test Objective",
            current_depth=1,
            max_depth=3,
            budget=0.5,
            payload=PlanPayload(previous_context="Old context")
        )

        from backend.services.research.steps.plan import PlanStep
        step = PlanStep()
        preview_data = await step.preview(orch, envelope, orch._state_mgr.states[task_id])

        user_prompt = preview_data.get("user_prompt", "")
        
        # Verify user prompt contains our details
        assert "Epistemic Reflection Notes:" in user_prompt
        assert "Epistemic Reflection: we are biased towards Western trauma metaphors." in user_prompt
        assert "Agent Monologue Trace (Meta-Cognitive Flow):" in user_prompt
        assert "↳ [ framing_provenance ]" in user_prompt
        assert "Deepened thought on kintsugi metaphor..." in user_prompt
        assert "Diffractive Audit & Critique Log (The Scar):" in user_prompt
        assert "- source_apparatus (SHALLOW):" in user_prompt
        assert "Vague gesture at Indigenous epistemologies." in user_prompt
        assert "Select a specific source like Diné Hózhó." in user_prompt
        assert "Diffractive Audit: CEREMONIAL" in user_prompt
        assert "Theoretical lens was just name-dropped." in user_prompt
        assert "- glitch_fidelity: 0.9" in user_prompt
        assert "- contradiction_density: 0.4" in user_prompt
        assert "- source_entropy: 0.6" in user_prompt
        assert "- revised_confidence: 0.35" in user_prompt

        conn.close()

    @pytest.mark.asyncio
    async def test_search_step_uses_lightweight_llm_selector(self):
        from backend.services.research.steps.search import _select_high_fidelity_results
        
        # Test 1: Fallback if no LLM
        results = [
            {"title": "Commercial Ad", "url": "http://ad.com", "snippet": "Buy now"},
            {"title": "Academic Study", "url": "http://univ.edu", "snippet": "A study on kintsugi"},
            {"title": "Blog Post", "url": "http://blog.org", "snippet": "Discussion"}
        ]
        
        res = await _select_high_fidelity_results(
            llm=None,
            objective="kintsugi research",
            query="kintsugi",
            results=results,
            target_count=2
        )
        assert len(res) == 2
        assert res[0]["url"] == "http://ad.com"

        # Test 2: Selector selects correct indices using LLM
        mock_llm = MagicMock()
        mock_response = {
            "json_data": {
                "selected_indices": [1, 2],
                "rationale": "Prioritize university study and deep blog post over ad."
            }
        }
        
        with patch("backend.services.research.steps.search.generate_unified", AsyncMock(return_value=mock_response)) as mock_gen:
            res = await _select_high_fidelity_results(
                llm=mock_llm,
                objective="kintsugi research",
                query="kintsugi",
                results=results,
                target_count=2
            )
            assert len(res) == 2
            assert res[0]["url"] == "http://univ.edu"
            assert res[1]["url"] == "http://blog.org"
            
            # Check mock generate_unified was called with correct parameters
            mock_gen.assert_called_once()
            args, kwargs = mock_gen.call_args
            assert kwargs["temperature"] == 0.1
            assert kwargs["max_tokens"] == 500





