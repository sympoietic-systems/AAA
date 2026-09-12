"""
Dataset ingestion, parent-pointer tree reconstruction, and embedding resolution.
"""

from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger("benchmarks.common.loader")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "benchmarks" / "data" / "dialogues"


@dataclass
class DialogueMessage:
    id: int
    parent_id: Optional[int]
    speaker: str
    content: str
    created_at: Optional[str] = None
    embedding: Optional[np.ndarray] = None


@dataclass
class DialogueDataset:
    name: str
    filepath: Path
    messages: List[DialogueMessage]
    is_branched: bool
    selected_node: Optional[int] = None
    tree_nodes_count: int = 0


def resolve_dataset_path(path_str: str) -> Path:
    """Resolves dataset path against working dir or benchmarks/data/dialogues/."""
    p = Path(path_str)
    if p.exists():
        return p.resolve()
    # Check data/dialogues
    candidate = DATA_ROOT / path_str
    if candidate.exists():
        return candidate.resolve()
    if not path_str.endswith(".json"):
        candidate_json = DATA_ROOT / f"{path_str}.json"
        if candidate_json.exists():
            return candidate_json.resolve()
    raise FileNotFoundError(f"Dialogue dataset not found at '{path_str}' or in '{DATA_ROOT}'.")


def load_dataset(
    filepath: Path,
    target_node: Optional[int] = None,
    longest_path: bool = False,
) -> DialogueDataset:
    """
    Loads dialogue dataset from JSON file.
    Supports:
    - Linear list of messages
    - Branched conversations with parent_message_id
    - Subtree extraction to target_node
    - Longest path extraction
    """
    filepath = resolve_dataset_path(str(filepath))
    with open(filepath, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        items = raw.get("messages") or raw.get("turns") or raw.get("nodes") or []
    else:
        raise ValueError(f"Unrecognized dialogue JSON format in {filepath}")

    msg_map: Dict[int, DialogueMessage] = {}
    children_map: Dict[Optional[int], List[int]] = {}

    for idx, m in enumerate(items):
        mid = m.get("id") or m.get("message_id") or (idx + 1)
        pid = m.get("parent_message_id") or m.get("parent_id")
        speaker = m.get("speaker") or m.get("role") or "human"
        content = m.get("content") or m.get("text") or ""
        created_at = m.get("created_at")

        emb = None
        if "embedding" in m and m["embedding"]:
            try:
                emb = np.array(m["embedding"], dtype=np.float32)
            except Exception:
                pass

        d_msg = DialogueMessage(
            id=int(mid),
            parent_id=int(pid) if pid is not None else None,
            speaker=speaker,
            content=content,
            created_at=created_at,
            embedding=emb,
        )
        msg_map[d_msg.id] = d_msg
        children_map.setdefault(d_msg.parent_id, []).append(d_msg.id)

    total_nodes = len(msg_map)
    has_branches = any(len(children) > 1 for children in children_map.values())

    # Branch extraction logic
    if (target_node is not None or longest_path) and has_branches:
        if longest_path:
            leaves = [mid for mid in msg_map if mid not in children_map or len(children_map[mid]) == 0]
            best_leaf = None
            max_depth = -1
            for leaf in leaves:
                depth = 0
                curr: Optional[int] = leaf
                while curr is not None and curr in msg_map:
                    depth += 1
                    curr = msg_map[curr].parent_id
                if depth > max_depth:
                    max_depth = depth
                    best_leaf = leaf
            target_node = best_leaf

        if target_node is not None and target_node in msg_map:
            path_ids: List[int] = []
            curr_id: Optional[int] = target_node
            visited = set()
            while curr_id is not None and curr_id in msg_map and curr_id not in visited:
                visited.add(curr_id)
                path_ids.append(curr_id)
                curr_id = msg_map[curr_id].parent_id
            path_ids.reverse()
            filtered_msgs = [msg_map[mid] for mid in path_ids]
            return DialogueDataset(
                name=filepath.stem,
                filepath=filepath,
                messages=filtered_msgs,
                is_branched=True,
                selected_node=target_node,
                tree_nodes_count=total_nodes,
            )

    # Linear default ordering
    msgs = list(msg_map.values())
    msgs.sort(key=lambda x: x.id)
    return DialogueDataset(
        name=filepath.stem,
        filepath=filepath,
        messages=msgs,
        is_branched=has_branches,
        selected_node=target_node,
        tree_nodes_count=total_nodes,
    )


def resolve_embeddings(
    dataset: DialogueDataset,
    cache_dir: Optional[Path] = None,
    model_name: str = "all-MiniLM-L6-v2",
) -> np.ndarray:
    """
    Extracts dense embeddings for dataset messages.
    Checks pre-computed arrays or cached .npy files first before computing.
    """
    if all(m.embedding is not None for m in dataset.messages):
        return np.vstack([m.embedding for m in dataset.messages])

    # Check companion .npy cache in data/dialogues or same dir
    companion_npy = dataset.filepath.parent / f"{dataset.filepath.stem}_embeddings.npy"
    if companion_npy.exists():
        loaded = np.load(companion_npy)
        if len(loaded) == len(dataset.messages):
            for idx, m in enumerate(dataset.messages):
                m.embedding = loaded[idx]
            return loaded

    if cache_dir:
        run_cache = cache_dir / f"{dataset.name}_embeddings.npy"
        if run_cache.exists():
            loaded = np.load(run_cache)
            if len(loaded) == len(dataset.messages):
                for idx, m in enumerate(dataset.messages):
                    m.embedding = loaded[idx]
                return loaded

    # Compute using sentence_transformers
    from sentence_transformers import SentenceTransformer
    logger.info("Computing dense embeddings via %s...", model_name)
    embedder = SentenceTransformer(model_name)
    texts = [m.content for m in dataset.messages]
    embs = embedder.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

    for idx, m in enumerate(dataset.messages):
        m.embedding = embs[idx]

    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        np.save(cache_dir / f"{dataset.name}_embeddings.npy", embs)

    return embs
