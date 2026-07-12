import logging
import re

import numpy as np
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from backend.utils.vector import cosine_similarity

logger = logging.getLogger(__name__)


router = APIRouter()


class SearchMatch(BaseModel):
    id: str
    type: str  # "message" | "note" | "memory_node"
    conversation_id: str
    title: str
    snippet: str
    relevance_score: float
    timestamp: str


def strip_xml_tags(text: str) -> str:
    if not text:
        return ""
    # Strip any XML/HTML-like tags, keeping the inner text
    return re.sub(r"<[^>]+>", "", text)


def get_snippet(text: str, query: str, length: int = 150) -> str:
    cleaned = strip_xml_tags(text)
    if not query:
        return cleaned[:length] + "..." if len(cleaned) > length else cleaned

    idx = cleaned.lower().find(query.lower())
    if idx == -1:
        return cleaned[:length] + "..." if len(cleaned) > length else cleaned

    start = max(0, idx - 50)
    end = min(len(cleaned), idx + length - 50)
    snippet = cleaned[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(cleaned):
        snippet = snippet + "..."
    return snippet


@router.get("/search", response_model=list[SearchMatch])
async def search_archive(
    request: Request,
    q: str = Query("", description="The query string to search for"),
    conversation_id: str | None = Query(None, description="Scope search to a specific conversation ID"),
    mode: str = Query("text", description="Baseline search mode: 'text' | 'semantic' | 'diffractive' | 'glitch'"),
    w_text: float = Query(1.0, description="Weight for text/keyword matches"),
    w_semantic: float = Query(0.0, description="Weight for semantic vector matches"),
    w_structural: float = Query(0.0, description="Weight for structural/diffractive matches"),
    w_glitch: float = Query(0.0, description="Weight for glitch salience metric matches"),
):
    message_repo = request.app.state.message_repo
    note_repo = request.app.state.note_repo
    memory_node_repo = request.app.state.memory_node_repo
    embedder = request.app.state.embedder
    structural_scorer = request.app.state.structural_scorer

    # If a specific mode is selected and weights are default/unset, tune weights automatically
    if mode == "semantic":
        w_text, w_semantic, w_structural, w_glitch = 0.0, 1.0, 0.0, 0.0
    elif mode == "diffractive":
        w_text, w_semantic, w_structural, w_glitch = 0.0, 0.0, 1.0, 0.0
    elif mode == "glitch":
        w_text, w_semantic, w_structural, w_glitch = 0.0, 0.0, 0.0, 1.0
    elif mode == "text" and w_text == 1.0 and w_semantic == 0.0 and w_structural == 0.0 and w_glitch == 0.0:
        # Default text search
        w_text, w_semantic, w_structural, w_glitch = 1.0, 0.0, 0.0, 0.0

    matches = []

    # 1. Fetch text matches
    text_message_ids = set()
    if w_text > 0.0 and q:
        # Dialogue messages text match
        text_msgs = message_repo.search_text(q, conversation_id)
        for msg in text_msgs:
            text_message_ids.add(msg.id)
            snippet = get_snippet(msg.content, q)
            matches.append(
                SearchMatch(
                    id=str(msg.id),
                    type="message",
                    conversation_id=msg.conversation_id,
                    title=f"Dialogue: {msg.speaker.capitalize()}",
                    snippet=snippet,
                    relevance_score=w_text * 1.0,
                    timestamp=msg.timestamp.isoformat() if hasattr(msg.timestamp, "isoformat") else str(msg.timestamp),
                )
            )

        # Notes text match
        notes = note_repo.search_notes_text(q)
        for note in notes:
            if conversation_id and note.get("conversation_id") != conversation_id:
                continue
            snippet = get_snippet(note.get("selected_text", "") + " - " + note.get("comment", ""), q)
            matches.append(
                SearchMatch(
                    id=note.get("id"),
                    type="note",
                    conversation_id=note.get("conversation_id") or "",
                    title=f"Note: {note.get('asset_type', '').replace('_', ' ').capitalize()}",
                    snippet=snippet,
                    relevance_score=w_text * 1.0,
                    timestamp=note.get("created_at").isoformat()
                    if hasattr(note.get("created_at"), "isoformat")
                    else str(note.get("created_at") or ""),
                )
            )

        # Memory Nodes text match
        mem_nodes = memory_node_repo.search_memory_nodes_text(q)
        for node in mem_nodes:
            if conversation_id and node.get("conversation_id") != conversation_id:
                continue
            snippet = get_snippet(node.get("intra_active_text", "") or node.get("scar", ""), q)
            matches.append(
                SearchMatch(
                    id=node.get("id"),
                    type="memory_node",
                    conversation_id=node.get("conversation_id") or "",
                    title=f"Memory: {node.get('node_type', 'concept').capitalize()} ({node.get('agential_symmetry', '')})",
                    snippet=snippet,
                    relevance_score=w_text * 1.0,
                    timestamp=node.get("created_at").isoformat()
                    if hasattr(node.get("created_at"), "isoformat")
                    else str(node.get("created_at") or ""),
                )
            )

    # 2. Vector-based scoring (Semantic & Diffractive) and Glitch Salience
    # Primarily queries and ranks dialogue messages
    if w_semantic > 0.0 or w_structural > 0.0 or w_glitch > 0.0:
        query_emb = None
        query_sig = None

        # Precompute query semantic embedding
        # embedder is EmbedderModule — use embedder.service.encode_async()
        if w_semantic > 0.0 and q:
            try:
                query_emb = await embedder.service.encode_async(q)
            except Exception as e:
                logger.warning("Semantic embedding failed: %s", e)

        # Precompute query structural signature
        # structural_scorer is StructuralScorerModule — use ._scorer.score_async()
        if w_structural > 0.0 and q:
            try:
                query_sig = await structural_scorer._scorer.score_async(q, use_llm_scorer=False)
            except Exception as e:
                logger.warning("Structural scoring failed: %s", e)

        # Load all messages candidates with embeddings and signatures
        candidates = message_repo.get_embeddings_and_signatures_for_search(conversation_id)

        # Load glitch salience metrics mappings if weight active
        glitch_map = {}
        if w_glitch > 0.0:
            glitch_msgs = message_repo.get_glitch_salience_messages(conversation_id, limit=200)
            for m_id, _, _, _, _, surprise, novelty, deficit in glitch_msgs:
                glitch_map[m_id] = max(surprise or 0.0, novelty or 0.0, deficit or 0.0)

        for m_id, speaker, content, conv_id, timestamp, emb_blob, sig_blob in candidates:
            # Skip if already added in text match (we will merge score if it already exists, or calculate below)
            # To compute composite scores properly, we check if we already have it in matches
            existing_match = next((m for m in matches if m.id == str(m_id) and m.type == "message"), None)

            s_sem = 0.0
            if query_emb is not None and emb_blob:
                try:
                    msg_emb = np.frombuffer(emb_blob, dtype="float32")
                    if len(msg_emb) == len(query_emb):
                        s_sem = float(cosine_similarity(query_emb, msg_emb))
                except Exception:
                    pass

            s_str = 0.0
            if query_sig is not None and sig_blob:
                try:
                    msg_sig = np.frombuffer(sig_blob, dtype="float32")
                    if len(msg_sig) == len(query_sig):
                        s_str = float(cosine_similarity(query_sig, msg_sig))
                except Exception:
                    pass

            g_score = glitch_map.get(m_id, 0.0)

            # Diffractive Goldilocks gate (pure diffractive mode only):
            # Structural isomorphism = high s_str (≥0.80) AND low s_sem (≤0.45).
            # This mirrors the convention in diffractive_retrieval.py.
            # In composite/weighted mode we fall back to continuous scoring.
            if mode == "diffractive" and w_semantic == 0.0:
                # Hard gate: skip unless structurally isomorphic
                if s_str < 0.80 or s_sem > 0.45:
                    continue
                diff_score = s_str
            else:
                # Continuous weighted scoring: structural minus semantic overlap
                diff_score = s_str * (1.0 - s_sem) if (w_structural > 0.0 and query_emb is not None) else s_str

            comp_score = (w_semantic * max(0.0, s_sem)) + (w_structural * max(0.0, diff_score)) + (w_glitch * g_score)

            if comp_score <= 0.0:
                continue

            if existing_match:
                existing_match.relevance_score += comp_score
            else:
                snippet = get_snippet(content, q)
                matches.append(
                    SearchMatch(
                        id=str(m_id),
                        type="message",
                        conversation_id=conv_id,
                        title=f"Dialogue: {speaker.capitalize()}",
                        snippet=snippet,
                        relevance_score=comp_score,
                        timestamp=timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp),
                    )
                )

    # Sort matches by relevance score descending, then timestamp descending
    matches.sort(key=lambda x: (-x.relevance_score, x.timestamp), reverse=False)

    return matches[:100]
