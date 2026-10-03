"""Assembly-owned activation evidence. Provenance is not a claim of response influence."""

import hashlib
import json
from typing import Any

from backend.core.logging_config import mask_secrets
from backend.storage.activation import ActivationEntry, ActivationTrace
from backend.utils.prompt_builder import format_skills_always_active


def build_activation_trace(payload: dict[str, Any], assembled: list[dict[str, Any]]) -> dict[str, Any]:
    """Called at prompt assembly, replacing any input-supplied provenance."""
    entries: list[ActivationEntry] = []
    truncated = any(
        payload.get(field) is None for field in ("attractor_window", "loaded_skills", "always_active_skills")
    )
    for field, kind, origin in (
        ("attractor_window", "belief", "attractor"),
        ("spectral_margin", "belief", "spectral"),
        ("always_active_skills", "skill", "always_active"),
        ("loaded_skills", "skill", "on_demand"),
        ("file_context", "external", "file"),
        ("web_context", "external", "web"),
        ("sediment_messages", "external", "resonance"),
        ("diffractive_messages", "external", "diffractive"),
    ):
        items = payload.get(field) or []
        for item in items:
            if len(entries) == 128:
                truncated = True
                break
            identifier = item.get("id") or item.get("source_id") or item.get("file_id") or item.get("url")
            if isinstance(identifier, str) and "://" in identifier:
                identifier = "uri-sha256:" + hashlib.sha256(identifier.encode()).hexdigest()
            label = item.get("label") or item.get("name") or item.get("source_title") or ""
            if kind == "skill":
                injected = bool(item.get("content_truncated", item.get("content")))
                if origin == "on_demand":
                    injected = True  # Loaded skill brief is always formatted.
                else:
                    brief = format_skills_always_active(items)
                    injected = injected or f"[{item.get('name')}]:" in brief
            elif kind == "belief":
                injected = True  # Every selected attractor/spectral entry is formatted.
            else:
                injected = origin != "diffractive" or payload.get("diffractive_state", "FLOWING") == "STAGNANT"
            entries.append(
                ActivationEntry.model_validate(
                    {
                        "kind": kind,
                        "id": mask_secrets(str(identifier))[:200] if identifier else None,
                        "label": mask_secrets(str(label))[:200],
                        "origin": origin,
                        "injected": injected,
                    }
                )
            )
    digest = hashlib.sha256(json.dumps(assembled, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    trace = ActivationTrace(
        coverage="partial" if truncated or any(e.id is None for e in entries) else "complete",
        prompt_sha256=digest,
        entries=entries,
    )
    return trace.model_dump()
