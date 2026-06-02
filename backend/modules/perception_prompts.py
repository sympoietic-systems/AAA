import logging
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)

PROMPTS_FILE = Path(__file__).resolve().parents[1] / "prompts" / "perception" / "vision_tripartite.yaml"

# Default fallback prompt in case of YAML failure
DEFAULT_TRIPARTITE_IMAGE_ANALYSIS_PROMPT = (
    "Analyze the uploaded image across the tripartite somatic/content extraction pipeline.\n"
    "You must perform the following tasks:\n"
    "1. Classification: Categorize the image type (artistic, screenshot, diagram, photo, document, noise).\n"
    "2. Transcription (OCR): Transcribe all text content exactly as it appears in the image.\n"
    "3. Somatic/Aesthetic notes: Write detailed notes on visual style, composition, glitch patterns, color harmony, and sensory impact.\n"
    "4. Diffractive analysis: Analyze how this visual aligns or collides with cybernetic systems, autopoiesis, boundary permeabilities, or structural drift.\n"
    "5. Belief Collision: Identify key conceptual belief nodes or themes from the system (e.g. autopoiesis, somatic_exhaustion, computational_ethics, boundary_breach, archival_will) that this image collides with, shifts, or resonates with.\n"
    "6. Aesthetic Telemetry: Provide scores (floats between 0.0 and 1.0) for Glitch Fidelity (G_f) and Aesthetic Dissidence (A_d).\n"
    "7. Structural trajectory: Recommend a 16-dimensional cybernetic signature vector (16 floats between 0.0 and 1.0 representing Homeostatic, Amplifying, Cyclic, Bifurcated, Decentralized, Rhizomatic, Permeable, Recursion, Variety, Negentropy, Latency, Attractor, Symbiotic, Nomadic, Conversational, Substrate).\n\n"
    "You MUST respond ONLY with a valid JSON object matching this schema:\n"
    "{\n"
    '  "classification": "diagram",\n'
    '  "transcription": "text found in the image...",\n'
    '  "somatic_notes": "description of visual style, colors, composition...",\n'
    '  "diffractive_analysis": "how this visual diffracts through cybernetic schemas...",\n'
    '  "belief_nodes_implicated": ["somatic_exhaustion", "archival_will"],\n'
    '  "g_f_score": 0.4,\n'
    '  "a_d_score": 0.7,\n'
    '  "structural_vector_16d": [0.2, 0.3, ...]\n'
    "}"
)

def _load_prompts() -> dict:
    if not PROMPTS_FILE.exists():
        logger.warning("Perception prompts YAML file not found: %s", PROMPTS_FILE)
        return {}
    try:
        with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning("Failed to parse perception prompts YAML file: %s", e)
        return {}

_prompts = _load_prompts()

TRIPARTITE_IMAGE_ANALYSIS_PROMPT = _prompts.get(
    "tripartite_image_analysis_prompt",
    DEFAULT_TRIPARTITE_IMAGE_ANALYSIS_PROMPT
).strip()
