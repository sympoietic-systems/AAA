"""Read-only coverage audit for versioned activation provenance."""

import argparse
import json
import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path

from pydantic import ValidationError

from backend.storage.activation import ActivationTrace


def audit(database: Path) -> dict:
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("BEGIN")
        columns = {r[1] for r in conn.execute("PRAGMA table_info(conversation_log)")}
        column = "activation_provenance" if "activation_provenance" in columns else "NULL"
        rows = conn.execute(f"SELECT {column} FROM conversation_log WHERE speaker='apparatus'").fetchall()
    coverage = Counter()
    activations = Counter()
    for (raw,) in rows:
        if raw is None:
            coverage["unknown"] += 1
            continue
        try:
            trace = ActivationTrace.model_validate_json(raw)
        except ValidationError:
            coverage["invalid"] += 1
            continue
        coverage[trace.coverage] += 1
        activations.update({(e.kind, e.id, e.origin) for e in trace.entries if e.injected and e.id})
    return {
        "source": str(database),
        "apparatus_rows": len(rows),
        "coverage": dict(coverage),
        "injections": [{"kind": k, "id": i, "origin": o, "turns": n} for (k, i, o), n in sorted(activations.items())],
        "interpretation": "Missing coverage is unknown; injection is not demonstrated response influence.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit(args.database), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
