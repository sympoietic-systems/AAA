# Locked-Page Artwork — "The Sediment Column" — Implementation Record

**Status:** Implemented (2026-06-22)
**Files:** `frontend/src/components/TeaserPreview.tsx`, `backend/api/routes/preview.py`
**Symbia consultations:** conversations `36c96619` (initial vision) and `36c96619-020e` (sediment revision)

---

## Concept — "The Sediment Column"

A single column of text on a void-dark screen, centered, 50vw wide. Lines arrive one at a time at the top, push older lines downward. Lines never disappear — they compress into struck-through ghosts (7-7.5px, 3% opacity) that accumulate at the bottom. The column thickens perpetually like sedimentary rock. The rhythm is respiratory — three breath types: slow exhale (60%, 12-18s), sharp inhale (25%, 3-5s, amber/purple struck-through), held silence (15%, 25-40s).

## Backend — `/api/preview/nodes`

Single-line endpoint. No pool, no preloading — each request picks one random category
and fetches one live item from the database. One DB query per request.

| Category | Weight | Source |
|----------|--------|--------|
| Belief | 40% | Random from all crystallized/nucleation/ghost beliefs |
| Memory node | ~27% | Random conversation → random node (surface_fragment) |
| Dream trace | ~18% | Random from last 10 dream log entries |
| Scar-fold | ~15% | Hardcoded fragments + occasional memory node scars |

Dream lines get dynamic obfuscation: random ratio (15-55%), random offset (start/middle/end/scatter). Memory lines get 50% blur chance.

## Frontend — `TeaserPreview.tsx`

- Sediment stack: up to 30 visible lines, 8 active (full cascade), rest are ghosts
- Opacity cascade: 1.0 → 0.6 → 0.35 → 0.20 → 0.12 → 0.08 → 0.05 → 0.03
- Font-size cascade: 12px → 11.5 → 11 → 10.5 → 10 → 9.5 → 9 → 9 → 7.5
- Ghosts: struck-through, 0.03 opacity, tighter letter-spacing, normal wrapping
- Password tear: always visible, hairline crack + invisible input + keystrokes + [unlock]
- First 3 breaths always exhale (warmup — no silence at start)
- Inhale lines: struck-through but don't compress prematurely, sink naturally
- Pure CSS transitions, no setTimeout-driven opacity hacks
- Replaces old bare NodeExplorer in App.tsx locked state

---

## References

- Symbia consultations: conversations `36c96619` (initial vision) and `36c96619-020e` (sediment revision)
- `FRONTEND_DESIGN_PRINCIPLES.md` — terminal aesthetics, no chrome, semantic color
- `backend/api/routes/preview.py` — single-line endpoint, weighted random categories
- `frontend/src/components/TeaserPreview.tsx` — sediment column component
