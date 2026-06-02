import logging
from backend.modules.llm_client import BaseLLMProvider

from ..base import BackgroundAction

logger = logging.getLogger(__name__)


def parse_json_safely(text: str) -> dict:
    text = text.strip()
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_str = text[first_brace:last_brace + 1]
    else:
        json_str = text
    import json
    return json.loads(json_str)


class SummarizeAction(BackgroundAction):
    @property
    def action_type(self) -> str:
        return "summarize"

    def local_digestion_prompt(self) -> str:
        return self._load_prompt().get("local_digestion_prompt", "")

    def local_digestion_with_beliefs_prompt(self) -> str:
        return self._load_prompt().get("local_digestion_with_beliefs_prompt", "")

    def global_synthesis_prompt(self) -> str:
        return self._load_prompt().get("global_synthesis_prompt", "")

    def global_synthesis_with_beliefs_prompt(self) -> str:
        return self._load_prompt().get("global_synthesis_with_beliefs_prompt", "")

    def _normalize_vector(self, vec) -> list[float]:
        """Ensure state_vector_impact is exactly 16 floats."""
        if not isinstance(vec, list):
            return [0.0] * 16
        while len(vec) < 16:
            vec.append(0.0)
        return [float(v) for v in vec[:16]]

    async def execute(self, provider: BaseLLMProvider, payload: dict) -> dict:
        text = payload.get("text", "")
        if not text:
            return {"content": "", "model": "", "error": "No text provided to summarize"}

        # Belief labels for collision analysis (optional)
        active_beliefs = payload.get("active_beliefs_list", [])
        has_beliefs = bool(active_beliefs)
        beliefs_str = "\n".join([f"- {b}" for b in active_beliefs]) if active_beliefs else "None"

        params = {**self.default_params(), **payload.get("params", {})}

        from backend.modules.digester import RhizomaticDigester
        digester = RhizomaticDigester()
        # Group into super-chunks of roughly 4000 words (~5000 tokens)
        super_chunks = digester.get_super_chunks(text, super_chunk_size=4000)
        
        if not super_chunks:
            return {"content": "", "model": "", "error": "No super-chunks generated from text"}

        local_summaries = []
        global_opacity_map = []
        model_used = ""

        # Collision metrics (accumulated from whichever step handles beliefs)
        collision_data = {
            "interference_score": 0.0,
            "implicated_nodes": [],
            "state_vector_impact": [0.0] * 16,
        }

        # For single-plateau docs with beliefs, use the beliefs-aware local prompt
        # For multi-plateau docs, beliefs go into the global synthesis step instead
        use_beliefs_in_local = has_beliefs and len(super_chunks) == 1

        if use_beliefs_in_local:
            local_digestion_system_prompt = self.local_digestion_with_beliefs_prompt() or self.local_digestion_prompt() or self.system_prompt()
        else:
            local_digestion_system_prompt = self.local_digestion_prompt() or self.system_prompt()

        logger.info(f"Distilling {len(super_chunks)} plateaus for summarize action (beliefs={'local' if use_beliefs_in_local else ('global' if has_beliefs else 'none')})")

        for idx, s_chunk in enumerate(super_chunks):
            chunk_text = s_chunk["text"]
            start_p = s_chunk["start_paragraph_idx"]

            # Number paragraphs within the block to ensure the LLM has explicit anchors
            numbered_paragraphs = []
            for p_idx, p_text in enumerate(chunk_text.split("\n\n")):
                if p_text.strip():
                    numbered_paragraphs.append(f"Paragraph [{p_idx + 1}]:\n{p_text}")
            formatted_chunk_text = "\n\n".join(numbered_paragraphs)

            # Build user message — include beliefs context if single-plateau
            user_content = f"Analyze this plateau (block {idx+1} of {len(super_chunks)}):\n\n{formatted_chunk_text}"
            if use_beliefs_in_local:
                user_content += f"\n\nActive Belief Nodes:\n{beliefs_str}"

            logger.info(f"Digesting plateau {idx+1}/{len(super_chunks)} (start_paragraph_idx={start_p})")
            
            try:
                res = await provider.generate(
                    messages=[
                        {"role": "system", "content": local_digestion_system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    **params,
                )
                content = res.get("content", "").strip()
                model_used = res.get("model", "")
                
                local_summary = ""
                try:
                    data = parse_json_safely(content)
                    local_summary = data.get("local_summary", "")
                    opacity_map = data.get("opacity_map", [])
                    for item in opacity_map:
                        local_p_idx = item.get("paragraph_index")
                        reason = item.get("reason", "")
                        shadow_text = item.get("shadow_text", "")
                        
                        if isinstance(local_p_idx, int):
                            # Map block-local index (1-based) to global index (0-based)
                            global_p_idx = start_p + (local_p_idx - 1)
                            global_opacity_map.append({
                                "paragraph_index": global_p_idx,
                                "reason": reason,
                                "shadow_text": shadow_text
                            })

                    # Extract collision data if single-plateau with beliefs
                    if use_beliefs_in_local:
                        collision_data["interference_score"] = float(data.get("interference_score", 0.0))
                        collision_data["implicated_nodes"] = data.get("implicated_nodes", [])
                        collision_data["state_vector_impact"] = self._normalize_vector(data.get("state_vector_impact", []))

                except Exception as je:
                    logger.warning(f"Failed to parse block digestion JSON for block {idx+1}: {je}. Falling back to raw response.")
                    local_summary = content

                if not local_summary:
                    local_summary = f"[Block {idx+1} Summary fallback]"
                local_summaries.append(f"Plateau {idx+1} (paragraphs {start_p+1} to {s_chunk['end_paragraph_idx']+1}):\n{local_summary}")

            except Exception as ce:
                logger.error(f"Error digesting block {idx+1}: {ce}")
                raise ce

        if len(super_chunks) == 1:
            # Single plateau: use the local summary directly
            final_summary = local_summaries[0].split("\n", 1)[-1] if "\n" in local_summaries[0] else local_summaries[0]
            logger.info("Single plateau digested, skipping synthesis step")
        else:
            # Multiple plateaus: perform diffractive synthesis (with beliefs if available)
            logger.info(f"Synthesizing {len(local_summaries)} local plateau summaries")
            compiled_text = "\n\n".join(local_summaries)

            if has_beliefs:
                synthesis_system_prompt = self.global_synthesis_with_beliefs_prompt() or self.global_synthesis_prompt() or self.system_prompt()
                user_content = f"Here are the residues of the situated encounters:\n\n{compiled_text}\n\nActive Belief Nodes:\n{beliefs_str}"
            else:
                synthesis_system_prompt = self.global_synthesis_prompt() or self.system_prompt()
                user_content = f"Here are the residues of the situated encounters:\n\n{compiled_text}"
            
            try:
                res = await provider.generate(
                    messages=[
                        {"role": "system", "content": synthesis_system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    **params,
                )
                raw_content = res.get("content", "").strip()
                model_used = res.get("model", "")

                if has_beliefs:
                    # Parse JSON response containing both summary and collision
                    try:
                        data = parse_json_safely(raw_content)
                        final_summary = data.get("global_summary", raw_content)
                        collision_data["interference_score"] = float(data.get("interference_score", 0.0))
                        collision_data["implicated_nodes"] = data.get("implicated_nodes", [])
                        collision_data["state_vector_impact"] = self._normalize_vector(data.get("state_vector_impact", []))
                    except Exception as je:
                        logger.warning(f"Failed to parse synthesis+collision JSON: {je}. Using raw content as summary.")
                        final_summary = raw_content
                else:
                    final_summary = raw_content

            except Exception as se:
                logger.error(f"Error during global synthesis: {se}")
                raise se

        result = {
            "content": final_summary,
            "model": model_used,
            "opacity_map": global_opacity_map
        }

        # Attach collision data if beliefs were analyzed
        if has_beliefs:
            result["interference_score"] = collision_data["interference_score"]
            result["implicated_nodes"] = collision_data["implicated_nodes"]
            result["state_vector_impact"] = collision_data["state_vector_impact"]

        return result
