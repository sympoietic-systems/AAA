"""Perception Metabolism Handlers — Metabolizing perceptions, notes, web probes, and themes."""

import logging
from typing import Any

import numpy as np

from backend.modules.belief_math import calculate_concept_density, parse_vector_16d
from backend.utils.similarity import cosine_similarity

logger = logging.getLogger(__name__)


class PerceptionMetabolismHandler:
    """Metabolizes non-chat structural inputs into belief accretions or proto-beliefs."""

    @staticmethod
    async def metabolize_perception(
        engine: Any,
        conversation_id: str,
        source_id: str,
        source_type: str,
        structural_signature: np.ndarray,
        belief_nodes_implicated: list[str] | None = None,
        perturbation: float = 1.0,
    ) -> None:
        try:
            if len(structural_signature) != 16:
                logger.warning(
                    f"Incorrect structural vector dimension for perception metabolism: {len(structural_signature)}"
                )
                return

            agent_id = "symbia"
            all_beliefs = engine._belief_repo.list_beliefs(agent_id)

            best_sim = -1.0
            # 1. Update all non-collapsed beliefs by similarity against perception signature
            for b in all_beliefs:
                if b.lifecycle_stage in ("collapsed", "faded"):
                    continue
                if belief_nodes_implicated and (
                    b.label not in belief_nodes_implicated and b.id not in belief_nodes_implicated
                ):
                    continue

                b_vec = parse_vector_16d(b.vector_16d)
                if b_vec is None:
                    logger.warning(
                        f"Skipping belief '{b.label}' with invalid or malformed vector_16d: {b.vector_16d[:80]}"
                    )
                    continue
                alignment = cosine_similarity(structural_signature, b_vec)
                if alignment > best_sim:
                    best_sim = alignment

                dc = 0.80
                _impact_multiplier = 1.0
                if belief_nodes_implicated and (b.label in belief_nodes_implicated or b.id in belief_nodes_implicated):
                    _impact_multiplier = 2.5

                source_weight = engine._get_source_weight("ingested_document")
                effective_perturbation = perturbation * _impact_multiplier
                engine._accrete_belief(
                    b,
                    structural_signature,
                    source_weight,
                    alignment,
                    effective_perturbation,
                    source_type=source_type,
                    source_id=source_id,
                    dc=dc,
                )

            # 2. Draft proposal if this is a completely new concept (similarity < threshold)
            if best_sim < engine._NUCLEATION_THRESHOLD:
                statement = f"Emergent concept from ingested perception '{source_id}'."
                engine._nucleate_proto_belief(
                    agent_id=agent_id,
                    statement=statement,
                    vector=structural_signature,
                    source_type=source_type,
                    source_id=source_id,
                    source_weight=engine._get_source_weight("ingested_document"),
                )

            logger.info(f"Successfully metabolized perception '{source_id}' of type '{source_type}'.")

        except Exception as e:
            logger.error(f"Error metabolizing perception: {e}", exc_info=True)

    @staticmethod
    async def metabolize_note(
        engine: Any,
        conversation_id: str,
        message_id: int,
        selected_text: str,
        comment: str,
        note_id: str,
    ) -> None:
        try:
            agent_id = "symbia"
            note_full_text = (
                f'Selected: "{selected_text}" | Comment: "{comment}"' if comment else f'Selected: "{selected_text}"'
            )
            note_vec = engine._scorer.score(note_full_text)

            # Find the closest active belief node (excluding ghosts)
            best_match = engine._find_closest_active_belief(agent_id, note_vec, min_similarity=0.0)
            best_sim = 0.0
            if best_match:
                try:
                    b_vec = parse_vector_16d(best_match.vector_16d)
                    if b_vec is not None:
                        best_sim = cosine_similarity(note_vec, b_vec)
                    else:
                        logger.warning(f"Shared note match belief '{best_match.label}' has invalid vector_16d")
                        best_sim = 0.0
                except Exception:
                    best_sim = 0.0

            source_weight = engine._get_source_weight("shared_note")
            if best_match and best_sim > 0.85:
                # Accrete the existing belief
                engine._accrete_belief(best_match, note_vec, source_weight, alignment=best_sim, perturbation=1.5)
                logger.info(
                    f"Metabolized shared note {note_id}: accreted belief '{best_match.label}' (sim={best_sim:.2f})"
                )
            else:
                # Nucleate a proto-belief instead of instant creation
                engine._nucleate_proto_belief(
                    agent_id=agent_id,
                    statement=note_full_text,
                    vector=note_vec,
                    source_type="chat_turn",
                    source_id=str(message_id),
                    source_weight=source_weight,
                )
                logger.info(f"Metabolized shared note {note_id}: nucleated proto-belief")
        except Exception as e:
            logger.error(f"Error metabolizing note {note_id}: {e}", exc_info=True)

    @staticmethod
    async def metabolize_web(
        engine: Any,
        conversation_id: str,
        source_id: str,
        extracted_text: str,
    ) -> None:
        try:
            agent_id = "symbia"
            source_weight = engine._get_source_weight("web_retrieval")
            web_vec = engine._scorer.score(extracted_text)

            closest = engine._find_closest_active_belief(agent_id, web_vec, min_similarity=engine._NUCLEATION_THRESHOLD)
            b_vec = parse_vector_16d(closest.vector_16d) if closest else None
            if closest is not None and b_vec is not None:
                alignment = cosine_similarity(web_vec, b_vec)
                engine._accrete_belief(
                    closest,
                    web_vec,
                    source_weight,
                    alignment,
                    perturbation=1.0,
                    source_type="web_probe",
                    source_id=source_id,
                )
            elif calculate_concept_density(extracted_text) > engine._NUCLEATION_THRESHOLD:
                engine._nucleate_proto_belief(
                    agent_id=agent_id,
                    statement=extracted_text[:200],
                    vector=web_vec,
                    source_type="web_probe",
                    source_id=source_id,
                    source_weight=source_weight,
                )
            logger.info(f"Web retrieval {source_id} metabolized into belief system")
        except Exception as e:
            logger.error(f"Error metabolizing web retrieval: {e}", exc_info=True)

    @staticmethod
    async def metabolize_conversational_pattern(
        engine: Any,
        agent_id: str,
        theme_text: str,
    ) -> None:
        try:
            source_weight = engine._get_source_weight("conversational_pattern")
            theme_vec = engine._scorer.score(theme_text)
            dc = calculate_concept_density(theme_text)

            if dc < engine._NUCLEATION_THRESHOLD:
                return

            closest = engine._find_closest_active_belief(
                agent_id, theme_vec, min_similarity=engine._NUCLEATION_THRESHOLD
            )
            b_vec = parse_vector_16d(closest.vector_16d) if closest else None
            if closest is not None and b_vec is not None:
                alignment = cosine_similarity(theme_vec, b_vec)
                engine._accrete_belief(
                    closest,
                    theme_vec,
                    source_weight,
                    alignment,
                    perturbation=1.0,
                    source_type="chat_turn",
                    source_id=None,
                )
            else:
                engine._nucleate_proto_belief(
                    agent_id=agent_id,
                    statement=theme_text[:200],
                    vector=theme_vec,
                    source_type="chat_turn",
                    source_id="cross_conversation",
                    source_weight=source_weight,
                )
            logger.info(f"Conversational pattern metabolized: '{theme_text[:80]}...'")
        except Exception as e:
            logger.error(f"Error metabolizing conversational pattern: {e}", exc_info=True)
