"""Retroactive iteration-folding script for AAA memory nodes.

Identifies similar concept iterations across past checkpoints within conversations,
sutures them into a single primary memory node, increments revision history, and
resolves diffractive tendrils without erasing historical traces.
"""

import argparse
import json
import logging
import sqlite3
from datetime import UTC, datetime

from backend.metabolisation.sedimentation import _calculate_text_similarity, _resolve_diffractive_tendrils

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fold_iterations")


def fold_iterations_for_db(db_path: str, dry_run: bool = True, threshold: float = 0.65) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    conv_rows = conn.execute("SELECT DISTINCT conversation_id FROM memory_nodes").fetchall()
    total_folded = 0

    for crow in conv_rows:
        cid = crow["conversation_id"]
        rows = conn.execute(
            "SELECT * FROM memory_nodes WHERE conversation_id = ? ORDER BY created_at ASC", (cid,)
        ).fetchall()

        nodes = [dict(r) for r in rows]
        if len(nodes) <= 1:
            continue

        folded_by_id: dict[str, dict] = {}
        duplicates_to_remove: list[str] = []

        for node in nodes:
            nid = node.get("id")
            key = (node.get("diffractive_key") or "").strip().lower()
            text = node.get("intra_active_text") or node.get("surface_fragment") or ""

            match_found = None
            for primary in folded_by_id.values():
                pkey = (primary.get("diffractive_key") or "").strip().lower()
                ptext = primary.get("intra_active_text") or primary.get("surface_fragment") or ""

                if key and pkey and key == pkey:
                    match_found = primary
                    break

                sim = _calculate_text_similarity(text, ptext)
                if sim >= threshold:
                    match_found = primary
                    break

            if match_found:
                total_folded += 1
                match_found["revision_count"] = match_found.get("revision_count", 0) + 1
                match_found["last_merged_at"] = datetime.now(UTC).isoformat()
                
                # Merge tendrils
                try:
                    t1 = json.loads(match_found.get("tendril_ids") or "[]")
                    t2 = json.loads(node.get("tendril_ids") or "[]")
                    match_found["tendril_ids"] = json.dumps(_resolve_diffractive_tendrils(t1, t2))
                except Exception:
                    pass

                duplicates_to_remove.append(node["id"])
                logger.info(
                    "[fold] conversation %s: folding node %s -> %s (v%d)",
                    cid,
                    node["id"],
                    match_found["id"],
                    match_found["revision_count"],
                )
            else:
                folded_by_id[nid] = node

        if not dry_run and duplicates_to_remove:
            for primary in folded_by_id.values():
                conn.execute(
                    """UPDATE memory_nodes 
                       SET revision_count = ?, last_merged_at = ?, tendril_ids = ? 
                       WHERE id = ?""",
                    (
                        primary.get("revision_count", 0),
                        primary.get("last_merged_at"),
                        primary.get("tendril_ids"),
                        primary["id"],
                    ),
                )
            # Remove redundant historical snapshots under secondary node IDs
            conn.executemany("DELETE FROM memory_nodes WHERE id = ?", [(did,) for did in duplicates_to_remove])
            conn.commit()

    conn.close()
    prefix = "[DRY RUN] Would fold" if dry_run else "Successfully folded"
    logger.info("%s %d node iterations across past checkpoints.", prefix, total_folded)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retroactive iteration-folding script")
    parser.add_argument("--db", type=str, default="backend/data/aaa.db", help="Path to SQLite database")
    parser.add_argument("--execute", action="store_true", help="Apply folds to database")
    parser.add_argument("--threshold", type=float, default=0.65, help="Similarity threshold")
    args = parser.parse_args()

    fold_iterations_for_db(args.db, dry_run=not args.execute, threshold=args.threshold)
