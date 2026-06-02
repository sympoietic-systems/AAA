import logging
import re
import json
from pathlib import Path
import yaml
import numpy as np
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

# Stemmed target keywords for the 16 cybernetic dimensions
LEXICON_MAPPINGS: List[List[str]] = [
    # 01. Homeostatic
    ['homeostas', 'regulat', 'stabili', 'dampen', 'equilib', 'negative feedback', 'ashby', 'restor'],
    # 02. Amplifying
    ['amplif', 'positive feedback', 'runaway', 'growth', 'cascade', 'multiplier', 'snowball', 'maruyama', 'vicious circle'],
    # 03. Cyclic
    ['cycl', 'loop', 'recurs', 'autopoie', 'self-produc', 're-ent', 'circular', 'maturana', 'varela', 'oscilla'],
    # 04. Bifurcated
    ['bifurc', 'tipping', 'threshold', 'phase shift', 'catastroph', 'prigogine', 'transition', 'trigger'],
    # 05. Decentralized
    ['decentral', 'peer-to-peer', 'p2p', 'distributed', 'mesh', 'non-hierarch', 'mcculloch', 'p2p'],
    # 06. Rhizomatic / Networked
    ['rhizom', 'network', 'meshwork', 'redundant', 'deleuze', 'guattari', 'hyperlink', 'lateral'],
    # 07. Boundary Permeability
    ['permeab', 'boundary', 'semi-permeab', 'closure', 'open system', 'closed system', 'filtering'],
    # 08. Recursion Depth
    ['recurs', 'nest', 'fractal', 'scaling', 'subsystem', 'hierarchy', 'beer', 'vsm', 'nested'],
    # 09. Variety Filtering
    ['variety', 'filter', 'attenuat', 'requisite variety', 'ashby', 'selection', 'attenuation'],
    # 10. Negentropic Complexity
    ['negentrop', 'entropy', 'order', 'complexity', 'schrodinger', 'information density', 'syntropy'],
    # 11. Temporal Latency
    ['latenc', 'delay', 'lag', 'buffer', 'time-lag', 'forrester', 'sluggish', 'retardation'],
    # 12. Attractor Depth
    ['attractor', 'rigidity', 'basin', 'resilien', 'plastic', 'adaptation', 'thom', 'well'],
    # 13. Symbiotic
    ['symbio', 'co-evolution', 'coupling', 'mutual', 'parasit', 'bateson', 'mutualism'],
    # 14. Nomadic
    ['nomad', 'deterritor', 'line of flight', 'drift', 'escape', 'smooth space', 'migration'],
    # 15. Conversational Co-Orientation
    ['convers', 'consensus', 'agreement', 'co-orient', 'pask', 'l-user', 'dialogue'],
    # 16. Substrate Materiality
    ['substrat', 'material', 'embod', 'physical', 'foerster', 'hardware', 'silicon', 'meatware']
]


# In-memory cache for LLM justifications
JUSTIFICATION_CACHE: dict[str, str] = {}


def get_justification(content: str) -> Optional[str]:
    if not content:
        return None
    import hashlib
    h = hashlib.sha256(content.encode('utf-8')).hexdigest()
    return JUSTIFICATION_CACHE.get(h)


def set_justification(content: str, justification: str) -> None:
    if not content or not justification:
        return
    import hashlib
    h = hashlib.sha256(content.encode('utf-8')).hexdigest()
    JUSTIFICATION_CACHE[h] = justification
    # Prevent memory leaks
    if len(JUSTIFICATION_CACHE) > 1000:
        first_key = next(iter(JUSTIFICATION_CACHE))
        JUSTIFICATION_CACHE.pop(first_key)


class StructuralScorer:
    """Interface for structural signature calculators."""
    def score(self, text: str, context: Optional[dict] = None) -> np.ndarray:
        raise NotImplementedError()


class LexiconScorer(StructuralScorer):
    """Calculates keyword frequency density using cybernetic lexicons with saturation scaling."""
    def __init__(self, kappa: float = 100.0, mappings: Optional[List[List[str]]] = None):
        self.kappa = kappa
        self.mappings = mappings or LEXICON_MAPPINGS

    def score(self, text: str, context: Optional[dict] = None) -> np.ndarray:
        text_lower = text.lower()
        # Simple word tokenization for density calculation
        words = re.findall(r'[a-z0-9\-]+', text_lower)
        word_count = len(words)
        if word_count == 0:
            return np.zeros(16, dtype=np.float32)

        scores = np.zeros(16, dtype=np.float32)
        for i, stems in enumerate(self.mappings):
            count = 0
            for stem in stems:
                # Count raw occurrences of the stem in lowercase text
                count += text_lower.count(stem)
            
            density = count / word_count
            # Apply non-linear exponential saturation: 1 - e^(-kappa * density)
            scores[i] = 1.0 - np.exp(-self.kappa * density)

        return scores


class TopologyScorer(StructuralScorer):
    """Calculates empirical markdown formatting, hierarchy, and connection density properties."""
    def score(self, text: str, context: Optional[dict] = None) -> np.ndarray:
        scores = np.zeros(16, dtype=np.float32)
        char_count = max(1, len(text))

        # 1. Recursion Depth (Dimension 8) - Markdown Header Hierarchy Entropy
        headers = re.findall(r'^(#{1,6})\s+', text, re.MULTILINE)
        if headers:
            counts = [0] * 6
            for h in headers:
                counts[len(h) - 1] += 1
            max_depth = max(len(h) for h in headers)
            
            total_headers = len(headers)
            p = [c / total_headers for c in counts if c > 0]
            entropy = -sum(pi * np.log2(pi) for pi in p)
            
            # S_topo_8 = (max_depth / 6) * (1 - e^(-entropy))
            scores[7] = (max_depth / 6.0) * (1.0 - np.exp(-entropy))
        else:
            scores[7] = 0.0

        # 2. Rhizomatic / Networked (Dimension 6) - Wiki link and URL density
        wiki_links = len(re.findall(r'\[\[([^\]]+)\]\]', text))
        urls = len(re.findall(r'https?://\S+', text))
        total_links = wiki_links + urls
        link_density = (total_links / char_count) * 1000.0
        
        # Check context for degree centrality
        degree = 0
        if context and 'degree_centrality' in context:
            degree = context['degree_centrality']
            
        scores[5] = float(np.tanh(0.2 * link_density + 0.1 * degree))

        # 3. Cyclic / Recursive (Dimension 3) - Graph cycle presence check
        if context and context.get('is_in_cycle', False):
            scores[2] = 1.0
        else:
            # Check for self-referencing markdown loops/backlinks in text
            if re.search(r'\[\[self\]\]|\[\[same\]\]|loop|recursion', text, re.IGNORECASE):
                scores[2] = 0.5

        # 4. Decentralized (Dimension 5) - Bullet points, checklist, list density
        list_items = len(re.findall(r'^(\s*[\*\-\+])\s+', text, re.MULTILINE))
        checklist_items = len(re.findall(r'^(\s*[\*\-\+]\s+\[[ xX]\])\s+', text, re.MULTILINE))
        total_lists = list_items + checklist_items
        list_density = (total_lists / char_count) * 1000.0
        scores[4] = float(np.tanh(0.15 * list_density))

        # 5. Boundary Permeability (Dimension 7) - Blockquotes and codeblocks
        codeblocks = len(re.findall(r'```', text)) // 2
        blockquotes = len(re.findall(r'^>\s+', text, re.MULTILINE))
        permeability = (codeblocks * 2 + blockquotes) / max(1, char_count // 500)
        scores[6] = float(np.tanh(0.4 * permeability))

        return scores


class LLMScorer(StructuralScorer):
    """Interrogates the LLM to score the text across the 16 dimensions using a structured schema."""
    def __init__(self, provider = None, system_prompt: Optional[str] = None):
        self.provider = provider
        if system_prompt is None:
            try:
                prompts_file = Path(__file__).resolve().parents[1] / "prompts" / "structural_engine" / "classification.yaml"
                if prompts_file.exists():
                    with open(prompts_file, "r", encoding="utf-8") as f:
                        c_data = yaml.safe_load(f) or {}
                    self.system_prompt = c_data.get("system_prompt", "You are a cybernetic taxonomy classifier. Respond ONLY with the requested JSON object.")
                else:
                    self.system_prompt = "You are a cybernetic taxonomy classifier. Respond ONLY with the requested JSON object."
            except Exception as e:
                logger.warning("Failed to load taxonomy system prompt from YAML: %s", e)
                self.system_prompt = "You are a cybernetic taxonomy classifier. Respond ONLY with the requested JSON object."
        else:
            self.system_prompt = system_prompt

    async def score_async(self, text: str, context: Optional[dict] = None) -> np.ndarray:
        if not self.provider:
            return np.full(16, 0.25, dtype=np.float32)

        prompt = (
            f"Analyze the structural/systemic profile of the following text chunk across 16 cybernetic dimensions.\n"
            f"Text to analyze:\n---\n{text}\n---\n"
            f"You must output a JSON object containing:\n"
            f'1. "justification": A concise string explaining your reasoning for the structural properties of the text.\n'
            f'2. "scores": An array of exactly 16 float values, each strictly between 0.0 and 1.0, representing the intensity of the following dimensions in order:\n'
            f"   01: Homeostatic (negative feedback, stability, dampening)\n"
            f"   02: Amplifying (positive feedback, runaway growth, cascade)\n"
            f"   03: Cyclic (autopoietic loops, self-reference, circular)\n"
            f"   04: Bifurcated (tipping points, thresholds, phase shifts)\n"
            f"   05: Decentralized (distributed control, peer-to-peer, mesh)\n"
            f"   06: Rhizomatic/Networked (redundant links, flat lateral paths)\n"
            f"   07: Boundary Permeability (selectivity of system borders)\n"
            f"   08: Recursion Depth (nested systems, fractals, scaling)\n"
            f"   09: Variety Filtering (variety attenuation or control)\n"
            f"   10: Negentropic Complexity (dense information, ordered structure)\n"
            f"   11: Temporal Latency (time lags, feedback delay)\n"
            f"   12: Attractor Depth (resilience, rigidity vs. plasticity)\n"
            f"   13: Symbiotic (co-evolution, coupling, environmental match)\n"
            f"   14: Nomadic (boundary crossing, lines of flight, drift)\n"
            f"   15: Conversational Co-Orientation (dialogue, agreement dynamics)\n"
            f"   16: Substrate Materiality (physical embodiment vs. symbolic virtuality)\n\n"
            f"Response must be valid JSON matching this schema:\n"
            f'{{\n  "justification": "reasoning...",\n  "scores": [0.1, 0.2, ...]\n}}'
        )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]

        try:
            res = await self.provider.generate(
                messages,
                temperature=0.1,
                max_tokens=600
            )
            content = res.get("content", "").strip()
            
            # Simple extract JSON regex block
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                justification = data.get("justification", "")
                if justification:
                    set_justification(text, justification)
                scores_list = data.get("scores", [])
                if isinstance(scores_list, list) and len(scores_list) > 0:
                    # Pad or truncate to 16
                    while len(scores_list) < 16:
                        scores_list.append(0.25)
                    scores_list = scores_list[:16]
                    # Clamp values strictly to [0.0, 1.0]
                    clamped = [max(0.0, min(1.0, float(v))) for v in scores_list]
                    return np.array(clamped, dtype=np.float32)
            logger.warning("Failed to parse scores from LLMScorer response content: %s", content)
        except Exception as e:
            logger.exception("Error in LLMScorer generation: %s", e)

        return np.full(16, 0.25, dtype=np.float32)

    def score(self, text: str, context: Optional[dict] = None) -> np.ndarray:
        # Synchronous fallback runs asyncio loop
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running (e.g. inside FastAPI), we run it via task
                import nest_asyncio
                nest_asyncio.apply()
            return loop.run_until_complete(self.score_async(text, context))
        except Exception as e:
            logger.error("Failed to run LLMScorer synchronously: %s", e)
            return np.full(16, 0.25, dtype=np.float32)


class CompositeStructuralScorer(StructuralScorer):
    """Coordinates calculation from different strategies and applies weighted linear combination."""
    def __init__(
        self,
        llm_provider = None,
        config: Optional[dict] = None,
        w_ling: float = 0.25,
        w_topo: float = 0.25,
        w_llm: float = 0.50
    ):
        if config is None:
            try:
                from backend.config import load_config
                config = load_config()
            except Exception:
                config = {}

        ss_cfg = config.get("structural_signature", {})
        lexicon_config = ss_cfg.get("lexicon")
        llm_prompt_config = ss_cfg.get("llm_system_prompt")
        self.llm_scorer_enabled = ss_cfg.get("llm_scorer_enabled", True)

        self.lexicon_scorer = LexiconScorer(mappings=lexicon_config)
        self.topology_scorer = TopologyScorer()
        self.llm_scorer = LLMScorer(llm_provider, system_prompt=llm_prompt_config)
        
        # Normalize weights
        total_w = w_ling + w_topo + w_llm
        self.w_ling = w_ling / total_w
        self.w_topo = w_topo / total_w
        self.w_llm = w_llm / total_w

    async def score_async(self, text: str, context: Optional[dict] = None, use_llm_scorer: Optional[bool] = None) -> np.ndarray:
        s_ling = self.lexicon_scorer.score(text, context)
        s_topo = self.topology_scorer.score(text, context)
        
        run_llm = use_llm_scorer if use_llm_scorer is not None else self.llm_scorer_enabled
        # Only run LLMScorer if enabled and provider is present
        if run_llm and self.llm_scorer.provider:
            s_llm = await self.llm_scorer.score_async(text, context)
        else:
            s_llm = np.full(16, 0.25, dtype=np.float32)
            
        final_score = self.w_ling * s_ling + self.w_topo * s_topo + self.w_llm * s_llm
        return np.clip(final_score, 0.0, 1.0)

    def score(self, text: str, context: Optional[dict] = None, use_llm_scorer: Optional[bool] = None) -> np.ndarray:
        s_ling = self.lexicon_scorer.score(text, context)
        s_topo = self.topology_scorer.score(text, context)
        
        run_llm = use_llm_scorer if use_llm_scorer is not None else self.llm_scorer_enabled
        if run_llm and self.llm_scorer.provider:
            s_llm = self.llm_scorer.score(text, context)
        else:
            s_llm = np.full(16, 0.25, dtype=np.float32)
        
        final_score = self.w_ling * s_ling + self.w_topo * s_topo + self.w_llm * s_llm
        return np.clip(final_score, 0.0, 1.0)


# Import elements for the pipeline module
from backend.modules.base import ProcessingModule
from backend.skills.metadata import SkillMeta


class StructuralScorerModule(ProcessingModule):
    """Pipeline module wrapping CompositeStructuralScorer."""
    def __init__(self, composite_scorer: CompositeStructuralScorer):
        self._scorer = composite_scorer

    @property
    def name(self) -> str:
        return "structural_scorer"

    def validate(self) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        content = payload.get("content", "")
        use_llm = payload.get("include_structural_scoring")
        if content:
            sig = await self._scorer.score_async(content, use_llm_scorer=use_llm)
            payload["structural_signature"] = sig.tobytes()
        return payload

    @property
    def skill_meta(self) -> SkillMeta:
        return SkillMeta(
            name="structural_scorer",
            description="Calculates 16-dimensional cybernetic structural signatures of the message text",
            category="perception",
            always_run=True,
        )
