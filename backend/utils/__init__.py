from backend.utils.token_counter import estimate_tokens
from backend.utils.similarity import cosine_similarity  # delegates to vector.py
from backend.utils.vector import (
    parse_vector_16d,
    cosine_similarity as _cosine_similarity,  # re-exported via similarity.py
    deserialize_structural_signature,
    build_history_message,
)
from backend.utils.filesystem import UPLOAD_DIR, ensure_upload_dir, get_upload_path, to_utc
from backend.utils.skill_parser import parse_skill_nucleation_tags

