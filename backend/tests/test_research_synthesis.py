import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

# Ensure parent directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.research_orchestrator import SomaticResearchOrchestrator


class MockAppState:
    def __init__(self):
        self.config = {
            "research_orchestrator": {
                "max_reflect_rounds": 3,
                "default_top_n": 3,
                "satisfaction_threshold": 0.7,
                "early_stop_threshold": 0.8,
                "max_concurrent_parses": 3,
            }
        }
        self.llm_provider = MagicMock()
        self.llm_provider.model_id = "test-model"
        
        self.research_task_repo = MagicMock()
        self.research_plan_repo = MagicMock()
        self.research_step_repo = MagicMock()
        self.research_step_result_repo = MagicMock()
        self.scraped_asset_repo = MagicMock()
        self.research_branch_repo = MagicMock()
        self.research_meta_log_repo = MagicMock()


@pytest.mark.asyncio
async def test_synthesize_phase_uses_synthesis_persona():
    state = MockAppState()
    orchestrator = SomaticResearchOrchestrator(state)

    # Set up mock repos to return dummy objects
    task_id = "test_task_synthesis"
    state.research_task_repo.get.return_value = {
        "id": task_id,
        "objective": "Understand Barad's diffractive methodology",
        "max_depth": 2,
        "budget_limit_usd": 5.0,
        "cached_inputs": None,
    }
    
    # Empty cache initially
    orchestrator._state_mgr.states[task_id] = {
        "phase": "synthesizing",
        "objective": "Understand Barad's diffractive methodology",
        "max_depth": 2,
        "budget": 5.0,
        "all_findings": ["[Barad 2007]: Diffraction is an intra-active phenomenon.", "[Haraway 1997]: Diffraction maps interference patterns."],
        "sources_analyzed": 2,
        "step_number": 5,
        "current_depth": 1,
        "last_reflection": {
            "reflection": "Reflection about intra-action",
            "key_insights": ["Insight A", "Insight B"],
            "remaining_gaps": ["Gap C"]
        }
    }

    # Mock DB returns for step results
    state.research_step_result_repo.get_by_task.return_value = [
        {
            "source_url": "https://example.com/barad",
            "source_title": "Meeting the Universe Halfway",
            "raw_content": "Content about Barad",
        },
        {
            "source_url": "https://example.com/haraway",
            "source_title": "Modest_Witness",
            "raw_content": "Content about Haraway",
        }
    ]

    mock_markdown = (
        "# Diffractive Study of Intra-action\n\n"
        "## Agential Cut Declaration\n"
        "This synthesis cuts through Barad and Haraway.\n\n"
        "## Diffractive Interference Landscape\n"
        "We read Barad [S1] through Haraway [S2] to map interference.\n\n"
        "## Sources Consulted\n"
        "| Identifier | Title | URL |\n"
        "|---|---|---|\n"
        "| [S1] | Meeting the Universe Halfway | https://example.com/barad |\n"
        "| [S2] | Modest_Witness | https://example.com/haraway |"
    )

    # We mock generate_unified to capture system_prompt and return mock markdown
    mock_resp = {
        "json_data": {
            "report_markdown": mock_markdown,
            "confidence": 0.95,
            "key_takeaway": "Diffraction maps interference rather than reflection."
        },
        "content": None,
        "thinking": "Thinking about diffractive apparatus.",
        "model": "test-model",
        "provider_used": "test-provider",
    }

    with patch("backend.modules.llm_client.generate_unified", AsyncMock(return_value=mock_resp)) as mock_gen:
        # Patch the persona builder helper to verify context_key
        with patch.object(orchestrator, "_build_orchestrator_persona", wraps=orchestrator._build_orchestrator_persona) as mock_persona:
            report = await orchestrator._phase_synthesize(
                task_id=task_id,
                objective="Understand Barad's diffractive methodology",
                goal="Autonomous research",
                all_findings=["[Meeting the Universe Halfway]: Diffraction is an intra-active phenomenon.", "[Modest_Witness]: Diffraction maps interference patterns."],
                sources_count=2,
                step_id="mock_step_id",
            )
            
            # Assertions
            assert report == mock_markdown
            
            # Verify the persona builder was called with research_synthesis context key!
            mock_persona.assert_called_once_with("Understand Barad's diffractive methodology", "research_synthesis")
            
            # Verify generate_unified was called
            mock_gen.assert_called_once()
            args, kwargs = mock_gen.call_args
            
            # The system prompt should include the research_synthesis operational protocols
            system_prompt = kwargs.get("system_prompt", "")
            assert "Research Synthesis Protocols" in system_prompt
            assert "Agential Cut Declaration" in system_prompt
            assert "Diffractive Interference" in system_prompt
            assert "Citation Integrity" in system_prompt
            
            # Verify citation compression correctly replaced source names with [S1] and [S2]
            user_prompt = kwargs.get("user_prompt", "")
            assert "[S1]:" in user_prompt or "[S2]:" in user_prompt
            assert "Sources Legend:" in user_prompt
            
            # Verify reflection context was passed
            assert "Reflection about intra-action" in user_prompt
            assert "Insight A" in user_prompt
            assert "Gap C" in user_prompt


@pytest.mark.asyncio
async def test_research_task_completion_triggers_sedimentation():
    state = MockAppState()
    state.perception_repo = MagicMock()
    
    from backend.services.research_task_manager import ResearchTaskManager
    manager = ResearchTaskManager(state)
    
    # Mock transition
    manager.transition = MagicMock()
    
    # Mock task repository
    task_id = "test-task-123"
    state.research_task_repo.get.return_value = {
        "id": task_id,
        "conversation_id": "test-conv-abc",
        "objective": "Test task completion",
    }
    
    # Mock FileService functions
    from backend.services.file import FileService
    with patch.object(FileService, "cache_file") as mock_cache, \
         patch.object(FileService, "process_and_summarize", new_callable=AsyncMock) as mock_process:
        
        manager.complete(task_id, "This is the final result markdown")
        
        # Verify transition was called
        manager.transition.assert_called_once_with(task_id, "completed")
        
        # Verify task update was called
        state.research_task_repo.update.assert_called_once_with(task_id, result_summary="This is the final result markdown")
        
        # Verify file caching occurred
        mock_cache.assert_called_once_with("test-conv-abc", f"research-synthesis-{task_id}.md", b"This is the final result markdown")
        
        # Verify file creation in perception repo
        state.perception_repo.create_file.assert_called_once_with(
            conversation_id="test-conv-abc",
            file_name=f"research-synthesis-{task_id}.md",
            file_type="research-synthesis",
            status="uploading",
        )


@pytest.mark.asyncio
async def test_inject_global_research_task_lazy_provisions():
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from backend.api.routes.sediment import router as sediment_router
    
    app = FastAPI()
    app.include_router(sediment_router)
    
    class MockApp:
        def __init__(self):
            self.state = MagicMock()
            self.state.perception_repo = MagicMock()
            self.state.research_task_repo = MagicMock()
            
    mock_app = MockApp()
    app.state = mock_app.state
    
    # Mock data
    task_id = "global-task-456"
    mock_app.state.research_task_repo.list_all.return_value = [
        {
            "id": task_id,
            "objective": "Global test task",
            "result_summary": "Report synthesis text content",
            "completed_at": "2026-06-23 10:00:00",
        }
    ]
    mock_app.state.perception_repo.get_all_files_across_conversations.return_value = []
    
    # Mock SQLite repository methods
    mock_app.state.perception_repo.check_file_exists.return_value = False
    
    mock_app.state.research_task_repo.get.return_value = {
        "id": task_id,
        "objective": "Global test task",
        "result_summary": "Report synthesis text content",
    }
    
    # Client request testing
    client = TestClient(app)
    
    # 1. Test listing
    resp = client.get("/sediment/files")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["files"]) == 1
    assert data["files"][0]["file_name"] == f"research-synthesis-{task_id}.md"
    assert data["files"][0]["conversation_id"] == "global-research"
    assert data["files"][0]["display_name"] == "Global test task"
    
    # 2. Test injecting
    from backend.services.file import FileService
    with patch.object(FileService, "cache_file") as mock_cache, \
         patch.object(FileService, "process_and_summarize", new_callable=AsyncMock) as mock_process:
        
        inject_payload = {
            "files": [
                {
                    "source_conversation_id": "global-research",
                    "source_file_name": f"research-synthesis-{task_id}.md"
                }
            ]
        }
        
        # Mock service inject call
        from backend.services.sediment import SedimentService
        with patch.object(SedimentService, "inject", return_value=[{"id": "inj-999", "source_conversation_id": "global-research", "source_file_name": f"research-synthesis-{task_id}.md"}]) as mock_inj_service:
            
            resp_inject = client.post(
                "/conversations/conv-xyz/sediment/inject",
                json=inject_payload
            )
            assert resp_inject.status_code == 200
            
            # Verify conversations was checked/inserted
            mock_app.state.perception_repo.ensure_conversation_exists.assert_called_once_with(
                "global-research", "Global Research Reports", "system"
            )
            
            # Verify file was cached and created in repo
            mock_cache.assert_called_once_with("global-research", f"research-synthesis-{task_id}.md", b"Report synthesis text content")
            mock_app.state.perception_repo.create_file.assert_called_once_with(
                conversation_id="global-research",
                file_name=f"research-synthesis-{task_id}.md",
                file_type="research-synthesis",
                status="uploading",
            )
