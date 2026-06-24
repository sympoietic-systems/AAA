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

## Visual Design

```
┌─────────────────────────────────┐
│  (void — no header, no labels)  │
│                                  │
│                                  │
│          the glitch is the       │  ← appears fully formed, #555555, 12px
│          apparatus's authentic   │
│          voice                   │  ← lingers 6-10 seconds
│                                  │
│              — seams mask the    │  ← appears below, indented, slightly
│                entanglement      │     higher opacity, as response
│                                  │
│  (long silence — 5-15 seconds)  │  ← reader wonders if it's over
│                                  │
│     the drone-body is the...     │  ← blurred text, Gaussian falloff,
│                                  │     unresolvable — the keyhole
│                                  │
│  (silence)                      │
│                                  │
│          ▇▇▇▇ says I lean       │  ← obfuscated, amber, struck-through
│          against no edge         │     appears and vanishes in blink
│                                  │
│  ──────────────────  ← tear     │  ← glowing hairline crack, center
│                                  │     click to type password
│  (keystrokes appear same font,  │  ← no cursor, no placeholder, no box
│   no feedback, no cursor)       │
│                                  │
│         [unlock]                 │  ← bracket text, dim → green on hover
└─────────────────────────────────┘
```

### Typographic rules

| Element | Font | Size | Color | Opacity |
|---------|------|------|--------|---------|
| Primary line | font-mono | 12px | `#555555` | 1.0 → fade to 0 |
| Response line | font-mono | 11px | `#666666` | 0.8 |
| Blurred memory | font-mono | 11px-12px | `#555555` | 0.4-0.6 + blur filter |
| Scar-fold | font-mono | 9px | `#f59e0b` | 0.3, fluttering |
| Glitch strike-through | font-mono | 12px | `#ef4444` | flash → 0 |
| Obfuscated | font-mono | 11px | `#f59e0b` | 0.6, ▇▇▇ chars |
| Password keystrokes | font-mono | 12px | `#555555` | 0.8 |
| Unlock button | font-mono | 10px | `#666666` | hover `#4ade80` |

---

## Rhythm & Sequencing

### Core breathing cycle

1. **Appear** — a line materializes fully-formed (fade-in 1-1.5s, no typewriter)
2. **Linger** — stays visible 6-10 seconds (long enough for unease)
3. **Response** — a second line appears below, indented, slightly higher opacity (optional, ~40% chance)
4. **Fade** — the first line begins evaporating from bottom-up (1-2s)
5. **Silence** — 5-15 seconds of darkness
6. **Next breath** — a new line appears

### Special events (random, ~20% chance per cycle)

| Event | Behavior | Duration |
|-------|----------|----------|
| Blurred memory | Line appears with CSS `filter: blur(3px)`, opacity 0.5. Never resolves — the reader knows there are words but cannot read them | 4-8s |
| Glitch strike-through | A line strikes through mid-word, variant appears beside at lower opacity. Amber/red flash. | <1s |
| Scar-fold flutter | A parenthetical appears at 30% brightness, sidles in from right, retreats | 2-3s |
| Obfuscated whisper | ▇▇▇▇ replaces first half of line, readable word at end. Amber color. | 3-5s |

### Respiration rules

- **No predictable timing** — intervals vary randomly within ranges
- **No loops** — lines are drawn from a shuffled pool, never repeat in sequence
- **Silence is structural** — the empty void between breaths is the artwork too
- **After a glitch, longer silence** — the mind needs to recover

---

## Password Input — The Tear

```html
<div class="relative w-full max-w-[320px] mx-auto mt-4">
  <!-- Hairline crack -->
  <div class="h-px bg-[#333] shadow-[0_0_8px_rgba(120,120,120,0.3)]" />
  <!-- Click target extends above/below the crack -->
  <input
    type="password"
    class="absolute inset-0 opacity-0 cursor-text"
    autofocus
  />
  <!-- Rendered keystrokes (visible only when typing) -->
  <div class="text-[#555] text-[12px] font-mono text-center mt-3 min-h-[1rem]">
    {/* masked keystrokes rendered here */}
  </div>
</div>
```

Key behaviors:
- Click the hairline crack to focus
- Typed characters appear BELOW the crack, same font/color as fragments — no cursor, no placeholder, no box
- No feedback on each keystroke — they just appear
- Press Enter to submit
- Error: the crack glows slightly red, then fades back to dim

---

## Backend — Preview Endpoint

**File:** `backend/api/routes/preview.py`

Same structure as current, but rename the output to reflect "the slip":

```json
{
  "lines": [
    { "text": "...", "type": "belief", "intensity": 0.8, "stage": "crystallized" },
    { "text": "...", "type": "memory", "intensity": 0.9, "blur": true },
    { "text": "...", "type": "dream", "obfuscated": true },
    { "text": "...", "type": "scar_fold" }
  ]
}
```

`lines` is a shuffled pool of ~20-25 entries: beliefs, memory nodes, dream traces, scar-folds. The frontend draws from this pool in random order.

No separate telemetry section — minimal approach, only text lines.

---

## References

- Symbia consultations: conversations `36c96619` (initial vision) and `36c96619-020e` (sediment revision)
- `FRONTEND_DESIGN_PRINCIPLES.md` — terminal aesthetics, no chrome, semantic color
- `backend/api/routes/preview.py` — single-line endpoint, weighted random categories
- `frontend/src/components/TeaserPreview.tsx` — sediment column component
