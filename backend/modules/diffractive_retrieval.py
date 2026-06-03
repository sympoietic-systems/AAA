import logging
from datetime import datetime
from typing import Optional
import numpy as np

from backend.skills.metadata import SkillMeta
from backend.storage.repository import MessageRepository, PerceptionSedimentRepository, SemanticKnotRepository
from backend.utils.token_counter import estimate_tokens
from .base import ProcessingModule

logger = logging.getLogger(__name__)


def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(v1, v2) / (norm1 * norm2))


class DiffractiveRetrievalModule(ProcessingModule):
    def __init__(
        self,
        message_repo: MessageRepository,
        perception_repo: PerceptionSedimentRepository,
        semantic_knot_repo: Optional[SemanticKnotRepository] = None,
        enabled: bool = True,
        similarity_range_min: float = 0.35,
        similarity_range_max: float = 0.55,
        file_range_min: float = 0.25,
        file_range_max: float = 0.45,
        max_diffractive_count: int = 3,
        token_budget: int = 1500,
        cohesion_length: int = 3,
    ):
        self._message_repo = message_repo
        self._perception_repo = perception_repo
        self._semantic_knot_repo = semantic_knot_repo
        self._enabled = enabled
        self._similarity_range_min = similarity_range_min
        self._similarity_range_max = similarity_range_max
        self._file_range_min = file_range_min
        self._file_range_max = file_range_max
        self._max_diffractive_count = max_diffractive_count
        self._token_budget = token_budget
        self._cohesion_length = cohesion_length

        self._states: dict[str, str] = {}  # conversation_id -> "FLOWING" | "STAGNANT"
        self._timers: dict[str, int] = {}  # conversation_id -> countdown

    @property
    def name(self) -> str:
        return "diffractive_retrieval"

    @property
    def skill_meta(self) -> SkillMeta:
        return SkillMeta(
            name="diffractive_retrieval",
            description="Perturbs conversation loops by retrieving semantically orthogonal Nomadic and Dormant context fragments",
            category="memory",
            always_run=True,
            children=[
                SkillMeta(
                    name="StagnationEvaluator",
                    description="Calculates loop severity via pairwise similarity, novelty, and entropy to trigger intervention",
                    category="memory",
                ),
                SkillMeta(
                    name="NomadicRetriever",
                    description="Retrieves semantically distant but structurally isomorphic memories from other threads",
                    category="memory",
                ),
                SkillMeta(
                    name="SemanticKnotRetriever",
                    description="Retrieves distilled concepts from semantic knots to perturb stagnant conversation loops",
                    category="memory",
                ),
                SkillMeta(
                    name="DormantFileRetriever",
                    description="Retrieves inactive file context segments falling in the dynamic similarity Goldilocks zone",
                    category="memory",
                ),
                SkillMeta(
                    name="BudgetInterleaver",
                    description="Interleaves retrieved items and enforces token context limits based on loop intensity",
                    category="memory",
                ),
            ]
        )

    def validate(self) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        payload["diffractive_messages"] = []
        payload["diffractive_state"] = "FLOWING"
        payload["diffractive_p"] = 0.0
        payload["diffractive_ratio"] = 0.0

        if not self._enabled:
            return payload

        conversation_id = payload.get("conversation_id", "")
        current_blob = payload.get("embedding")
        metrics = payload.get("metrics")

        if not conversation_id or not current_blob:
            return payload

        # Extract Metrics
        vitality = payload.get("conversation_vitality")
        if vitality is None and metrics:
            vitality = metrics.get("conversation_vitality")
        if vitality is None:
            vitality = 0.5

        boringness = 0.0
        rolling_entropy = 0.5
        if metrics:
            val_b = metrics.get("boringness")
            if val_b is not None:
                boringness = val_b
            val_e = metrics.get("rolling_entropy")
            if val_e is not None:
                rolling_entropy = val_e


        # Compute P_diffract with stochastic jitter R ~ U(-0.05, 0.05)
        jitter = np.random.uniform(-0.05, 0.05)
        p_diffract = 0.5 * boringness + 0.3 * (1.0 - rolling_entropy) - 0.4 * vitality + jitter
        p_diffract = float(np.clip(p_diffract, 0.0, 1.0))
        payload["diffractive_p"] = p_diffract

        # Hysteresis State Machine
        current_state = self._states.get(conversation_id, "FLOWING")
        timer = self._timers.get(conversation_id, 0)

        start_time = datetime.now()

        if timer > 0:
            timer -= 1
            self._timers[conversation_id] = timer
            target_state = current_state
        else:
            if current_state == "FLOWING":
                if p_diffract >= 0.75:
                    target_state = "STAGNANT"
                    timer = self._cohesion_length
                    self._timers[conversation_id] = timer
                else:
                    target_state = "FLOWING"
            else:  # STAGNANT
                if p_diffract <= 0.35:
                    target_state = "FLOWING"
                else:
                    target_state = "STAGNANT"

        self._states[conversation_id] = target_state
        payload["diffractive_state"] = target_state

        # Calculate Stagnation Index and Context Ratio (always compute for telemetry)
        stagnation = float(np.clip(boringness / (vitality + 0.01), 0.0, 1.0))
        r_context = 0.20 + 0.35 * stagnation
        payload["diffractive_ratio"] = r_context

        # Dynamic max count based on stagnation + randomness
        base_rand = np.random.randint(0, 3)  # 0, 1, or 2
        stagnation_bonus = int(np.round(stagnation * (self._max_diffractive_count - 1)))
        dynamic_max = int(np.clip(base_rand + stagnation_bonus, 0, self._max_diffractive_count))

        # Dynamic Sliding Goldilocks Range Bounds
        mem_min = 0.45 - 0.15 * stagnation
        mem_max = 0.85 - 0.15 * stagnation
        file_min = 0.35 - 0.15 * stagnation
        file_max = 0.75 - 0.15 * stagnation

        if target_state != "STAGNANT":
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            payload["diffractive_meta"] = {
                "state": target_state,
                "previous_state": current_state,
                "p_diffract": round(p_diffract, 4),
                "stagnation_index": round(stagnation, 4),
                "r_context": round(r_context, 4),
                "dynamic_max": 0,
                "cohesion_timer": timer,
                "similarity_range_memory": [round(mem_min, 3), round(mem_max, 3)],
                "similarity_range_files": [round(file_min, 3), round(file_max, 3)],
                "candidates_searched": 0,
                "items_injected": 0,
                "tokens_used": 0,
                "token_budget": 0,
                "duration_ms": round(duration_ms, 1),
                "sources": [],
            }
            return payload

        if dynamic_max == 0:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            payload["diffractive_meta"] = {
                "state": target_state,
                "previous_state": current_state,
                "p_diffract": round(p_diffract, 4),
                "stagnation_index": round(stagnation, 4),
                "r_context": round(r_context, 4),
                "dynamic_max": 0,
                "cohesion_timer": timer,
                "similarity_range_memory": [round(mem_min, 3), round(mem_max, 3)],
                "similarity_range_files": [round(file_min, 3), round(file_max, 3)],
                "candidates_searched": 0,
                "items_injected": 0,
                "tokens_used": 0,
                "token_budget": 0,
                "duration_ms": round(duration_ms, 1),
                "sources": [],
            }
            return payload

        # Dynamic Sliding Goldilocks Range Bounds
        # memory range base similarity [0.45, 0.85], slides down by up to 0.15 under stagnation
        mem_min = 0.45 - 0.15 * stagnation
        mem_max = 0.85 - 0.15 * stagnation

        # file range base similarity [0.35, 0.75], slides down by up to 0.15
        file_min = 0.35 - 0.15 * stagnation
        file_max = 0.75 - 0.15 * stagnation

        current_vec = np.frombuffer(current_blob, dtype="float32")

        # 1. Nomadic Cross-Conversation Retrieval (Capped at 30 candidates)
        # 1. Nomadic Cross-Conversation Retrieval & Semantic Knots (Capped at 30 candidates)
        if stagnation >= 0.70:
            # Dual-Vector Isomorphic Retrieval
            from backend.modules.structural_engine import CompositeStructuralScorer
            scorer = CompositeStructuralScorer(llm_provider=None)  # Use fast empirical scorers for latency
            query_text = payload.get("content", "")
            query_sig = await scorer.score_async(query_text)

            raw_candidates = self._message_repo.get_embeddings_and_signatures_except(
                exclude_conversation_id=conversation_id, limit=500
            )

            raw_knots = []
            if self._semantic_knot_repo:
                raw_knots = self._semantic_knot_repo.get_embeddings_and_signatures_except(
                    exclude_conversation_id=conversation_id, limit=500
                )

            scored_candidates = []
            for msg_id, emb_vec, sig_vec in raw_candidates:
                if len(emb_vec) != len(current_vec):
                    continue
                s_sem = cosine_similarity(current_vec, emb_vec)
                s_str = 0.0
                if sig_vec is not None and len(sig_vec) == 16:
                    s_str = cosine_similarity(query_sig, sig_vec)

                # Isomorphic filter: s_sem <= 0.45 AND s_str >= 0.80
                if s_sem <= 0.45 and s_str >= 0.80:
                    scored_candidates.append((s_sem, msg_id, s_str, "nomadic"))

            for knot_id, emb_vec, sig_vec, payload_text in raw_knots:
                if len(emb_vec) != len(current_vec):
                    continue
                s_sem = cosine_similarity(current_vec, emb_vec)
                s_str = 0.0
                if sig_vec is not None and len(sig_vec) == 16:
                    s_str = cosine_similarity(query_sig, sig_vec)

                if s_sem <= 0.45 and s_str >= 0.80:
                    scored_candidates.append((s_sem, knot_id, s_str, "semantic_knot"))

            # Sort by structural similarity descending, semantic similarity ascending
            scored_candidates.sort(key=lambda x: (-x[2], x[0]))
            nomadic_candidates = [(item[0], item[1], item[3]) for item in scored_candidates[:30]]
        else:
            # Standard Goldilocks Retrieval
            raw_nomadic = self._message_repo.get_embeddings_in_similarity_range(
                query_vec=current_vec,
                exclude_conversation_id=conversation_id,
                min_sim=mem_min,
                max_sim=mem_max,
                limit=30,
            )
            nomadic_candidates = [(sim, msg_id, "nomadic") for sim, msg_id in raw_nomadic]

            if self._semantic_knot_repo:
                raw_knots = self._semantic_knot_repo.get_knots_in_similarity_range(
                    query_vec=current_vec,
                    exclude_conversation_id=conversation_id,
                    min_sim=mem_min,
                    max_sim=mem_max,
                    limit=30,
                )
                nomadic_candidates += [(sim, knot_id, "semantic_knot") for sim, knot_id in raw_knots]

        selected_nomadic_messages = []
        if nomadic_candidates:
            nomadic_ids = [cid for _, cid, ctype in nomadic_candidates if ctype == "nomadic"]
            knot_ids = [cid for _, cid, ctype in nomadic_candidates if ctype == "semantic_knot"]

            msgs_by_id = {}
            if nomadic_ids:
                msgs = self._message_repo.get_sediment_messages_with_metadata(nomadic_ids)
                msgs_by_id = {m["id"]: m for m in msgs}

            knots_by_id = {}
            if knot_ids and self._semantic_knot_repo:
                knots = self._semantic_knot_repo.get_by_ids(knot_ids)
                knots_by_id = {k.id: k for k in knots}

            candidates_with_details = []
            for sim, cid, ctype in nomadic_candidates:
                if ctype == "nomadic":
                    m = msgs_by_id.get(cid)
                    if m:
                        candidates_with_details.append({
                            "type": "nomadic",
                            "content": m["content"],
                            "similarity": sim,
                            "source_title": m["conversation_title"],
                            "timestamp": m["timestamp"],
                        })
                elif ctype == "semantic_knot":
                    k = knots_by_id.get(cid)
                    if k:
                        candidates_with_details.append({
                            "type": "semantic_knot",
                            "content": k.concept_payload,
                            "similarity": sim,
                            "source_title": f"Sedimented Knot (Conv {k.conversation_id[:8]})",
                            "timestamp": k.created_at,
                        })

            def parse_date(d):
                if isinstance(d, str):
                    try:
                        return datetime.fromisoformat(d)
                    except ValueError:
                        return datetime.min
                return d or datetime.min

            candidates_with_details.sort(key=lambda x: parse_date(x["timestamp"]), reverse=True)

            # Roulette selection with exponential decay
            selected_indices = []
            indices = list(range(len(candidates_with_details)))
            weights = [np.exp(-0.05 * i) for i in range(len(candidates_with_details))]

            while len(selected_indices) < dynamic_max and indices:
                total_w = sum(weights[idx] for idx in indices)
                if total_w <= 0:
                    break
                r = np.random.uniform(0, total_w)
                running_w = 0.0
                chosen_idx = None
                for idx in indices:
                    running_w += weights[idx]
                    if r <= running_w:
                        chosen_idx = idx
                        break
                if chosen_idx is None:
                    chosen_idx = indices[-1]
                selected_indices.append(chosen_idx)
                indices.remove(chosen_idx)

            for idx in selected_indices:
                selected_nomadic_messages.append(candidates_with_details[idx])

        # 2. Dormant File Chunks Retrieval (Capped at 30 candidates)
        file_candidates = self._perception_repo.get_chunks_in_similarity_range(
            query_vec=current_vec,
            conversation_id=conversation_id,
            min_sim=file_min,
            max_sim=file_max,
        )

        selected_file_chunks = []
        if file_candidates:
            # Sort by similarity DESC
            file_candidates.sort(key=lambda x: x[0], reverse=True)
            target_chunk_ids = [chunk_id for _, chunk_id in file_candidates[:30]]
            sim_dict = {chunk_id: sim for sim, chunk_id in file_candidates}

            # select top N from candidate pool
            target_chunk_ids = target_chunk_ids[:dynamic_max]

            if target_chunk_ids:
                chunks = self._perception_repo.get_by_ids(target_chunk_ids)
                for chunk in chunks:
                    selected_file_chunks.append({
                        "type": "dormant_file",
                        "content": chunk.chunk_text,
                        "similarity": sim_dict.get(chunk.id, 0.0),
                        "source_title": chunk.file_name,
                        "timestamp": None,
                    })

        # Interleave & Budget Context
        all_candidates = []
        for i in range(max(len(selected_nomadic_messages), len(selected_file_chunks))):
            if i < len(selected_nomadic_messages):
                all_candidates.append(selected_nomadic_messages[i])
            if i < len(selected_file_chunks):
                all_candidates.append(selected_file_chunks[i])

        budget_limit = int(self._token_budget * r_context)
        accumulated_tokens = 0
        diffractive_payload = []

        for item in all_candidates:
            item_tokens = estimate_tokens(item["content"])
            if accumulated_tokens + item_tokens <= budget_limit:
                diffractive_payload.append(item)
                accumulated_tokens += item_tokens
            else:
                break

        payload["diffractive_messages"] = diffractive_payload

        # Telemetry Block Logging
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Build structured meta for API/frontend
        sources = []
        for item in diffractive_payload:
            sources.append({
                "type": item.get("type", "nomadic"),
                "source_title": item.get("source_title", ""),
                "similarity": round(item.get("similarity", 0.0), 4),
            })

        nomadic_count = len(nomadic_candidates) if nomadic_candidates else 0
        file_count = len(file_candidates) if file_candidates else 0

        payload["diffractive_meta"] = {
            "state": target_state,
            "previous_state": current_state,
            "p_diffract": round(p_diffract, 4),
            "stagnation_index": round(stagnation, 4),
            "r_context": round(r_context, 4),
            "dynamic_max": dynamic_max,
            "cohesion_timer": timer,
            "similarity_range_memory": [round(mem_min, 3), round(mem_max, 3)],
            "similarity_range_files": [round(file_min, 3), round(file_max, 3)],
            "candidates_searched": nomadic_count + file_count,
            "items_injected": len(diffractive_payload),
            "tokens_used": accumulated_tokens,
            "token_budget": budget_limit,
            "duration_ms": round(duration_ms, 1),
            "sources": sources,
        }

        _log_telemetry(
            boringness=boringness,
            vitality=vitality,
            rolling_entropy=rolling_entropy,
            p_diffract=p_diffract,
            state=current_state,
            target_state=target_state,
            timer=timer,
            r_context=r_context,
            budget=budget_limit,
            retrieved_count=len(diffractive_payload),
            duration_ms=duration_ms,
            diffractive_payload=diffractive_payload,
        )


        return payload


def _log_telemetry(
    boringness: float,
    vitality: float,
    rolling_entropy: float,
    p_diffract: float,
    state: str,
    target_state: str,
    timer: int,
    r_context: float,
    budget: int,
    retrieved_count: int,
    duration_ms: float,
    diffractive_payload: list[dict],
) -> None:
    timer_str = " ".join(["#" if i < timer else "-" for i in range(3)])
    source_info = "None"
    sim_val = 0.0

    if diffractive_payload:
        first = diffractive_payload[0]
        source_info = f"{first['type'].capitalize()}: {first['source_title']}"
        sim_val = first["similarity"]

    # Goldilocks bar visualization
    bar_width = 30
    marker_pos = int(sim_val * bar_width)
    bar_chars = list("-" * bar_width)
    for pos in range(bar_width):
        val = pos / bar_width
        if 0.25 <= val <= 0.85:
            bar_chars[pos] = ":"
    if 0 <= marker_pos < bar_width:
        bar_chars[marker_pos] = "*"
    bar_str = "".join(bar_chars)

    print("\n === [HOME] STAGNATION TELEMETRY ========================================================")
    print(f"  METRICS    |  Boringness: {boringness:.2f}   |  Vitality: {vitality:.2f}   |  Rolling Entropy: {rolling_entropy:.2f}")
    print(f"  STATE      |  Current: {state}   |  P_diffract: {p_diffract:.2f} |  Target State: {target_state} ({'Active' if target_state == 'STAGNANT' else 'Idle'})")
    print(f"  COHESION   |  Timer Cohesion Lock: [{timer_str}] ({timer} turns remaining)")
    print(f" === [CUT] DIFFRACTIVE INTERFERENCE PATTERN =============================================")
    print(f"  SOURCE     |  {source_info}")
    print(f"  INDEX      |  delta = {sim_val:.3f}  [ {bar_str} ] (Goldilocks Zone)")
    print(f"  STOCHASTIC |  Vectorized Cosine Matcher retrieved {retrieved_count} items (Budget: {budget} tokens) in {duration_ms:.1f}ms")
    print(" ========================================================================================\n")

