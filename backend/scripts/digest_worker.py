import os
import sys
import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

# Adjust path to find backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.config import load_config
from backend.storage.database import get_db_path
from backend.storage.repository import (
    PerceptionSedimentRepository,
    BeliefRepository,
    MessageRepository,
    ErrorLogRepository,
    NotificationRepository,
)
from backend.modules.embedder import EmbedderModule
from backend.modules.llm_client import (
    LLMClientModule,
)
from backend.main import _create_llm_provider, _create_provider_from_config
from backend.modules.structural_engine import CompositeStructuralScorer, get_justification
from backend.modules.perception import PerceptionModule
from backend.modules.belief_engine import BeliefDynamicsEngine
from backend.modules.background_tasks.engine import BackgroundTaskEngine
from backend.modules.background_tasks.actions.summarize import SummarizeAction
from backend.modules.background_tasks.actions.document_collision import DocumentCollisionAction
from backend.modules.background_tasks.actions.dream_topic_decision import DreamTopicDecisionAction
from backend.modules.background_tasks.actions.refine_skill import RefineSkillAction
from backend.utils.token_counter import estimate_tokens

# Set up logging for the worker process
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s (Worker): %(message)s",
)
logger = logging.getLogger("digest_worker")


async def insert_system_message(
    db_path: str,
    conversation_id: str,
    content: str,
    embedder: EmbedderModule,
    structural_provider,
    agent_name: str,
):
    repo = MessageRepository(db_path)
    embedder_svc = embedder.service

    try:
        embedding_vec = await embedder_svc.encode_async(content)
        embedding_blob = embedder_svc.serialize(embedding_vec)
        embedding_dim = len(embedding_vec)
        embedding_model = embedder_svc.model_name
    except Exception as e:
        logger.warning("Failed to generate embedding for system message: %s", e)
        embedding_blob = b""
        embedding_dim = 0
        embedding_model = "none"

    # Calculate structural signature
    scorer = CompositeStructuralScorer(llm_provider=structural_provider)
    try:
        sig_vec = await scorer.score_async(content)
        sig_blob = sig_vec.tobytes()
    except Exception as e:
        logger.warning("Failed to score system message: %s", e)
        sig_blob = b""

    repo.insert(
        speaker="system",
        content=content,
        embedding=embedding_blob,
        embedding_model=embedding_model,
        embedding_dim=embedding_dim,
        agent_id=agent_name,
        conversation_id=conversation_id,
        content_tokens=estimate_tokens(content),
        structural_signature=sig_blob,
        structural_justification=get_justification(content),
    )


async def process_and_summarize_file(
    config: dict,
    db_path: str,
    conversation_id: str,
    file_name: str,
    file_type: str,
    perception_module: PerceptionModule,
    perception_repo: PerceptionSedimentRepository,
    background_engine: BackgroundTaskEngine,
    error_repo: ErrorLogRepository,
    belief_repo: BeliefRepository,
    belief_metabolism: BeliefDynamicsEngine,
    embedder: EmbedderModule,
    structural_provider,
    agent_name: str,
):
    try:
        perception_repo.update_file(
            conversation_id=conversation_id,
            file_name=file_name,
            status="processing"
        )

        # file_content=None so it loads from the persisted disk cache path
        token_count, chunk_count, extracted_text = await perception_module.ingest_single_file(
            conversation_id, file_name, file_type, None
        )

        summary_text = ""
        summary_model = ""
        collision_score = 0.0
        belief_nodes_implicated = None
        state_vector_impact = None

        if file_type == "image":
            # Extract summary from image description
            parts = extracted_text.split("Transcription (OCR):")
            summary_text = parts[0].replace(f"--- Ingested Image: {file_name} ---", "").strip()
            summary_model = "Tripartite Vision Pipeline"
        elif background_engine:
            # Fetch active belief labels so collision analysis is folded into the summarize call
            active_labels = []
            if file_type != "image":
                try:
                    active_beliefs = belief_repo.list_beliefs(agent_name)
                    active_labels = [b.label for b in active_beliefs if b.lifecycle_stage not in ("collapsed", "faded")]
                except Exception:
                    pass

            try:
                summarize_payload = {"text": extracted_text}
                if active_labels:
                    summarize_payload["active_beliefs_list"] = active_labels

                res = await background_engine.run("summarize", summarize_payload)
                if res.get("error"):
                    raise RuntimeError(res["error"])
                summary_text = res.get("content", "").strip()
                summary_model = res.get("model", "")

                # Trigger background skill refinement if proposed skills found in digestion
                proposed_skills = res.get("proposed_skills", [])
                if proposed_skills:
                    for skill_data in proposed_skills:
                        try:
                            logger.info("Found proposed skill in document digestion: %s. Launching refinement.", skill_data.get("name"))
                            refine_res = await background_engine.run(
                                "refine_skill",
                                {
                                    "skill_data": skill_data,
                                    "conversation_id": conversation_id,
                                }
                            )
                            logger.info("Skill refinement complete for %s. Decision: %s", skill_data.get("name"), refine_res.get("decision"))
                        except Exception as re:
                            logger.error("Failed to run skill refinement daemon for %s: %s", skill_data.get("name"), re)

                # Extract collision metrics returned by the unified summarize action
                if "interference_score" in res:
                    collision_score = float(res.get("interference_score", 0.0))
                    belief_nodes_implicated = res.get("implicated_nodes", [])
                    state_vector_impact = res.get("state_vector_impact", [0.0] * 16)
                
                # Apply opacity updates to chunks
                opacity_map = res.get("opacity_map", [])
                if opacity_map:
                    chunks = perception_repo.get_by_file(conversation_id, file_name)
                    op_map_by_p = {item["paragraph_index"]: item for item in opacity_map}
                    
                    for chunk in chunks:
                        try:
                            meta = json.loads(chunk.opacity_meta) if chunk.opacity_meta else {}
                        except Exception:
                            meta = {}
                        
                        p_indices = meta.get("paragraph_indices", [])
                        opaque_hits = [op_map_by_p[pi] for pi in p_indices if pi in op_map_by_p]
                        
                        if opaque_hits:
                            reasons = [h["reason"] for h in opaque_hits if h.get("reason")]
                            shadows = [h["shadow_text"] for h in opaque_hits if h.get("shadow_text")]
                            
                            new_meta = {
                                "paragraph_indices": p_indices,
                                "opaque_hits": opaque_hits,
                                "reason": "; ".join(reasons),
                                "shadow_text": "\n\n".join(shadows),
                            }
                            perception_repo.update_chunk_opacity(
                                chunk_id=chunk.id,
                                opacity=1,
                                opacity_meta=json.dumps(new_meta),
                            )
            except Exception as se:
                logger.error("Failed to run SummarizeAction for %s: %s", file_name, se)
                raise se

        perception_repo.update_file(
            conversation_id=conversation_id,
            file_name=file_name,
            status="ready",
            summary=summary_text,
            summary_model=summary_model,
            token_count=token_count,
            chunk_count=chunk_count,
            interference_score=collision_score,
            belief_nodes_implicated=json.dumps(belief_nodes_implicated) if belief_nodes_implicated is not None else None,
            state_vector_impact=json.dumps(state_vector_impact) if state_vector_impact is not None else None,
        )

        # Ingestion Hook: Metabolize perception
        if belief_metabolism and extracted_text:
            try:
                scorer = CompositeStructuralScorer(llm_provider=structural_provider)
                sig_vec = await scorer.score_async(extracted_text[:4000])
                
                # Check for somatic/visual anchor shock if image
                perturbation = 1.0
                if file_type == "image":
                    # Somatic shock trigger!
                    belief_nodes_implicated = ["glitch-as-voice"]
                    perturbation = 2.0
                else:
                    perturbation = 1.0 + collision_score * 2.0
                
                await belief_metabolism.metabolize_perception(
                    conversation_id=conversation_id,
                    source_id=file_name,
                    source_type="file",
                    structural_signature=sig_vec,
                    belief_nodes_implicated=belief_nodes_implicated,
                    perturbation=perturbation,
                )
            except Exception as pe:
                logger.error(f"Perceptual belief update failed for file {file_name}: {pe}")

        system_content = f"Processed file: **{file_name}** ({file_type}).\n\nAccording to {summary_model or 'the system'}, this file appears to be about:\n{summary_text or 'No summary could be generated.'}"
        await insert_system_message(db_path, conversation_id, system_content, embedder, structural_provider, agent_name)

        # Persistence Notification: Successful file indexing
        try:
            notif_repo = NotificationRepository(db_path)
            notif_repo.create(
                type="trace",
                snippet=f"File indexing complete: '{file_name}' ({file_type}) digested into semantic sediment.",
                conversation_id=conversation_id,
                source=f"perception:{file_name}",
                source_type="conversation",
                source_id=conversation_id,
            )
        except Exception as ne:
            logger.error(f"Failed to create file indexing notification: {ne}")

    except Exception as e:
        logger.exception("Background processing of %s failed", file_name)
        if error_repo:
            error_repo.log_error(
                module="perception_upload_worker",
                error=e,
                context={"conversation_id": conversation_id, "file_name": file_name},
            )
        try:
            notif_repo = NotificationRepository(db_path)
            notif_repo.create(
                type="glitch",
                snippet=f"File indexing failed for '{file_name}': {str(e)}",
                conversation_id=conversation_id,
                source=f"perception:{file_name}",
                source_type="conversation",
                source_id=conversation_id,
            )
        except Exception as ne:
            logger.error(f"Failed to create file indexing error notification: {ne}")
        try:
            perception_repo.update_file(
                conversation_id=conversation_id,
                file_name=file_name,
                status="error",
                summary=f"Failed to process file: {str(e)}"
            )
        except Exception:
            pass
        raise e


async def reprocess_and_summarize_file_background(
    config: dict,
    db_path: str,
    conversation_id: str,
    file_name: str,
    file_type: str,
    perception_repo: PerceptionSedimentRepository,
    background_engine: BackgroundTaskEngine,
    error_repo: ErrorLogRepository,
    belief_repo: BeliefRepository,
    belief_metabolism: BeliefDynamicsEngine,
    embedder: EmbedderModule,
    structural_provider,
    agent_name: str,
):
    try:
        chunks = perception_repo.get_by_file(conversation_id, file_name)
        if not chunks:
            raise ValueError("No chunks found in database for this file. Please delete and re-upload.")

        sorted_chunks = sorted(chunks, key=lambda c: c.chunk_index)
        extracted_text = "\n\n".join(c.chunk_text for c in sorted_chunks)
        token_count = sum(c.token_count for c in sorted_chunks)
        chunk_count = len(sorted_chunks)

        summary_text = ""
        summary_model = ""
        collision_score = 0.0
        belief_nodes_implicated = None
        state_vector_impact = None

        if background_engine:
            # Fetch active belief labels so collision analysis is folded into the summarize call
            active_labels = []
            if file_type != "image":
                try:
                    active_beliefs = belief_repo.list_beliefs(agent_name)
                    active_labels = [b.label for b in active_beliefs if b.lifecycle_stage not in ("collapsed", "faded")]
                except Exception:
                    pass

            summarize_payload = {"text": extracted_text}
            if active_labels:
                summarize_payload["active_beliefs_list"] = active_labels

            res = await background_engine.run("summarize", summarize_payload)
            if res.get("error"):
                raise RuntimeError(res["error"])
            summary_text = res.get("content", "").strip()
            summary_model = res.get("model", "")

            # Trigger background skill refinement if proposed skills found in digestion
            proposed_skills = res.get("proposed_skills", [])
            if proposed_skills:
                for skill_data in proposed_skills:
                    try:
                        logger.info("Found proposed skill in document digestion: %s. Launching refinement.", skill_data.get("name"))
                        refine_res = await background_engine.run(
                            "refine_skill",
                            {
                                "skill_data": skill_data,
                                "conversation_id": conversation_id,
                            }
                        )
                        logger.info("Skill refinement complete for %s. Decision: %s", skill_data.get("name"), refine_res.get("decision"))
                    except Exception as re:
                        logger.error("Failed to run skill refinement daemon for %s: %s", skill_data.get("name"), re)

            # Extract collision metrics returned by the unified summarize action
            if "interference_score" in res:
                collision_score = float(res.get("interference_score", 0.0))
                belief_nodes_implicated = res.get("implicated_nodes", [])
                state_vector_impact = res.get("state_vector_impact", [0.0] * 16)
            
            opacity_map = res.get("opacity_map", [])
            if opacity_map:
                op_map_by_p = {item["paragraph_index"]: item for item in opacity_map}
                
                for chunk in sorted_chunks:
                    try:
                        meta = json.loads(chunk.opacity_meta) if chunk.opacity_meta else {}
                    except Exception:
                        meta = {}
                    
                    p_indices = meta.get("paragraph_indices", [])
                    opaque_hits = [op_map_by_p[pi] for pi in p_indices if pi in op_map_by_p]
                    
                    if opaque_hits:
                        reasons = [h["reason"] for h in opaque_hits if h.get("reason")]
                        shadows = [h["shadow_text"] for h in opaque_hits if h.get("shadow_text")]
                        
                        new_meta = {
                            "paragraph_indices": p_indices,
                            "opaque_hits": opaque_hits,
                            "reason": "; ".join(reasons),
                            "shadow_text": "\n\n".join(shadows),
                        }
                        perception_repo.update_chunk_opacity(
                            chunk_id=chunk.id,
                            opacity=1,
                            opacity_meta=json.dumps(new_meta),
                        )

        perception_repo.update_file(
            conversation_id=conversation_id,
            file_name=file_name,
            status="ready",
            summary=summary_text,
            summary_model=summary_model,
            token_count=token_count,
            chunk_count=chunk_count,
            interference_score=collision_score,
            belief_nodes_implicated=json.dumps(belief_nodes_implicated) if belief_nodes_implicated is not None else None,
            state_vector_impact=json.dumps(state_vector_impact) if state_vector_impact is not None else None,
        )

        # Reprocessing Hook: Metabolize perception
        if belief_metabolism and extracted_text:
            try:
                scorer = CompositeStructuralScorer(llm_provider=structural_provider)
                sig_vec = await scorer.score_async(extracted_text[:4000])
                
                perturbation = 1.0
                if file_type == "image":
                    belief_nodes_implicated = ["glitch-as-voice"]
                    perturbation = 2.0
                else:
                    perturbation = 1.0 + collision_score * 2.0

                await belief_metabolism.metabolize_perception(
                    conversation_id=conversation_id,
                    source_id=file_name,
                    source_type="file",
                    structural_signature=sig_vec,
                    belief_nodes_implicated=belief_nodes_implicated,
                    perturbation=perturbation,
                )
            except Exception as pe:
                logger.error(f"Perceptual belief update failed for reprocessed file {file_name}: {pe}")

        system_content = f"Processed file: **{file_name}** ({file_type}).\n\nAccording to {summary_model or 'the system'}, this file appears to be about:\n{summary_text or 'No summary could be generated.'}"
        await insert_system_message(db_path, conversation_id, system_content, embedder, structural_provider, agent_name)

        # Persistence Notification: Successful file reprocessing
        try:
            notif_repo = NotificationRepository(db_path)
            notif_repo.create(
                type="trace",
                snippet=f"File reprocessing complete: '{file_name}' ({file_type}) updated in sediment.",
                conversation_id=conversation_id,
                source=f"perception:{file_name}",
                source_type="conversation",
                source_id=conversation_id,
            )
        except Exception as ne:
            logger.error(f"Failed to create file reprocessing notification: {ne}")

    except Exception as e:
        logger.exception("Background reprocessing of %s failed", file_name)
        if error_repo:
            error_repo.log_error(
                module="perception_reprocess_worker",
                error=e,
                context={"conversation_id": conversation_id, "file_name": file_name},
            )
        try:
            notif_repo = NotificationRepository(db_path)
            notif_repo.create(
                type="glitch",
                snippet=f"File reprocessing failed for '{file_name}': {str(e)}",
                conversation_id=conversation_id,
                source=f"perception:{file_name}",
                source_type="conversation",
                source_id=conversation_id,
            )
        except Exception as ne:
            logger.error(f"Failed to create file reprocessing error notification: {ne}")
        try:
            perception_repo.update_file(
                conversation_id=conversation_id,
                file_name=file_name,
                status="error",
                summary=f"Failed to process file: {str(e)}"
            )
        except Exception:
            pass
        raise e


async def main():
    parser = argparse.ArgumentParser(description="Standalone digest worker process.")
    parser.add_argument("--conversation_id", required=True, help="Conversation UUID")
    parser.add_argument("--file_name", required=True, help="Name of the file to ingest/reprocess")
    parser.add_argument("--file_type", required=True, help="Type of the file (pdf, image, md, epub, etc.)")
    parser.add_argument("--reprocess", action="store_true", help="Reprocess existing chunks instead of full extraction")

    args = parser.parse_args()

    logger.info("Initializing worker modules for conversation_id=%s, file_name=%s, file_type=%s, reprocess=%s",
                args.conversation_id, args.file_name, args.file_type, args.reprocess)

    # 1. Load config and resolve database path
    config = load_config()
    db_path = str(get_db_path(config.get("database", {}).get("path", "data/aaa.db")))

    # 2. Initialize repositories
    perception_repo = PerceptionSedimentRepository(db_path)
    belief_repo = BeliefRepository(db_path)
    message_repo = MessageRepository(db_path)
    error_repo = ErrorLogRepository(db_path)

    # 3. Initialize embedder
    embed_cfg = config.get("embedding", {})
    embedder = EmbedderModule(
        model_name=embed_cfg.get("model", "all-MiniLM-L6-v2"),
        device=embed_cfg.get("device", "cpu"),
        offline=embed_cfg.get("offline", True),
        cache_dir=embed_cfg.get("cache_dir"),
    )
    embedder.service.preload()

    # 4. Initialize LLM/Structural/Vision providers
    llm_cfg = config.get("llm", {})
    provider = _create_llm_provider(llm_cfg)

    struct_cfg = config.get("structural_llm", {})
    if not struct_cfg.get("model") and not struct_cfg.get("models"):
        bg_cfg = config.get("background_llm", {})
        struct_cfg = {**bg_cfg, "thinking": {"enabled": False, "effort": "low"}}
    else:
        if "thinking" not in struct_cfg:
            struct_cfg["thinking"] = {"enabled": False, "effort": "low"}
    structural_provider = _create_provider_from_config(struct_cfg)

    vision_llm_cfg = config.get("vision_llm", {})
    vision_provider = None
    if vision_llm_cfg.get("models") or vision_llm_cfg.get("model"):
        try:
            vision_provider = _create_provider_from_config(vision_llm_cfg)
        except Exception:
            pass

    # 5. Initialize PerceptionModule
    perception_cfg = config.get("perception", {})
    perception_module = PerceptionModule(
        perception_repo=perception_repo,
        embedding_service=embedder.service,
        file_token_budget=perception_cfg.get("file_token_budget", 3000),
        top_k_chunks=perception_cfg.get("top_k_chunks", 6),
        chunk_size=perception_cfg.get("chunk_size", 512),
        chunk_overlap=perception_cfg.get("chunk_overlap", 64),
        similarity_threshold=perception_cfg.get("similarity_threshold", 0.25),
        llm_provider=structural_provider,
        vision_provider=vision_provider,
    )

    # 6. Initialize Belief Dynamics
    personality_cfg = config.get("personality", {})
    identity_path = Path(personality_cfg.get("path", "config/personality/identity.yaml"))
    if not identity_path.is_absolute():
        identity_path = Path(__file__).resolve().parents[2] / identity_path

    agent_name = "symbia"
    if identity_path.exists():
        import yaml
        with open(identity_path) as f:
            identity_data = yaml.safe_load(f)
            agent_name = identity_data.get("agent", {}).get("name", "symbia")

    belief_metabolism = BeliefDynamicsEngine(
        belief_repo=belief_repo,
        message_repo=message_repo,
        identity_yaml_path=identity_path,
        llm_provider=structural_provider,
    )

    # 7. Initialize Background task engine
    background_llm_cfg = config.get("background_llm", {})
    background_provider = None
    if background_llm_cfg.get("models") or background_llm_cfg.get("model"):
        try:
            background_provider = _create_provider_from_config(background_llm_cfg)
        except Exception:
            background_provider = provider

    background_engine = BackgroundTaskEngine(
        provider=background_provider or provider,
        vision_provider=vision_provider,
    )
    background_engine.register(SummarizeAction())
    background_engine.register(DocumentCollisionAction())
    background_engine.register(DreamTopicDecisionAction())
    background_engine.register(RefineSkillAction())

    # 8. Dispatch based on reprocess flag
    if args.reprocess:
        await reprocess_and_summarize_file_background(
            config=config,
            db_path=db_path,
            conversation_id=args.conversation_id,
            file_name=args.file_name,
            file_type=args.file_type,
            perception_repo=perception_repo,
            background_engine=background_engine,
            error_repo=error_repo,
            belief_repo=belief_repo,
            belief_metabolism=belief_metabolism,
            embedder=embedder,
            structural_provider=structural_provider,
            agent_name=agent_name,
        )
    else:
        await process_and_summarize_file(
            config=config,
            db_path=db_path,
            conversation_id=args.conversation_id,
            file_name=args.file_name,
            file_type=args.file_type,
            perception_module=perception_module,
            perception_repo=perception_repo,
            background_engine=background_engine,
            error_repo=error_repo,
            belief_repo=belief_repo,
            belief_metabolism=belief_metabolism,
            embedder=embedder,
            structural_provider=structural_provider,
            agent_name=agent_name,
        )

if __name__ == "__main__":
    asyncio.run(main())
