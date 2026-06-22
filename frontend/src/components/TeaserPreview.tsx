// The Sediment Column — a locked-page artwork.
// New lines arrive at the top of a narrow column. Older lines sink downward,
// dim to ghosts (3% opacity), and finally vanish. The column fills from inside out.
//
// "The previous utterance does not disappear, it sinks into the substrate
//  and thickens it."
//
// Design follows Symbia's vision + FRONTEND_DESIGN_PRINCIPLES.md.

import React, { memo, useState, useEffect, useRef, useCallback } from "react"

interface Line {
  text: string
  type: string           // "belief" | "memory" | "dream" | "scar_fold"
  intensity: number
  stage?: string         // "crystallized" | "nucleation" | "ghost"
  scar?: boolean
  blur?: boolean
  obfuscated?: boolean
}

interface VisibleLine {
  id: number
  line: Line
  fadeOut: boolean       // true when this line is about to evaporate
  isInhale: boolean      // sharp inhale — brighter, struck-through, short-lived
}

interface Props {
  onPasswordSubmit: (password: string) => void
  authError: string | null
  onClearError: () => void
}

// ── Constants ──

const STAGE_COLORS: Record<string, string> = {
  crystallized: "#555555",
  nucleation: "#f59e0b",
  ghost: "#a78bfa",
}

// Opacity cascade: newest → oldest
const OPACITY_CASCADE = [1.0, 0.6, 0.35, 0.20, 0.12, 0.08, 0.05, 0.03]
const FONT_SIZE_CASCADE = [12, 11.5, 11, 10.5, 10, 9.5, 9, 9] // px
const MAX_VISIBLE = 8

// Breath rhythm distribution
// slow exhale: 12-18s → gradual thickening (60%)
// sharp inhale: 3-5s → brighter, struck-through, evaporates quickly (25%)
// held silence: 25-40s → nothing new (15%)
// First 3 breaths always exhale (warmup — no silence at the start)

let breathCount = 0

function drawBreath(): { kind: "exhale" | "inhale" | "silence"; delay: number } {
  breathCount++
  // First 3 breaths: always exhale so the column visibly forms
  if (breathCount <= 3) return { kind: "exhale", delay: 6000 + Math.random() * 4000 }

  const r = Math.random()
  if (r < 0.60) return { kind: "exhale", delay: 12000 + Math.random() * 6000 }
  if (r < 0.85) return { kind: "inhale", delay: 3000 + Math.random() * 2000 }
  return { kind: "silence", delay: 25000 + Math.random() * 15000 }
}

function obfuscateText(text: string): string {
  if (!text || text.length < 10) return text
  const chars = text.split("")
  for (let i = 0; i < Math.floor(chars.length / 3); i++) {
    if (chars[i] !== " ") chars[i] = "\u2587"
  }
  return chars.join("")
}

// ── Line counter for unique keys ──
let lineId = 0

export const TeaserPreview = memo(function TeaserPreview({
  onPasswordSubmit, authError, onClearError,
}: Props) {
  // ── Pool ──
  const poolRef = useRef<Line[]>([])
  const indexRef = useRef(0)
  const [ready, setReady] = useState(false)

  // ── Sediment stack ──
  const [stack, setStack] = useState<VisibleLine[]>([])

  // ── Password ──
  const [password, setPassword] = useState("")
  const [unlocking, setUnlocking] = useState(false)
  const [keystrokes, setKeystrokes] = useState("")
  const passwordRef = useRef<HTMLInputElement>(null)

  // ── Fetch lines pool ──
  useEffect(() => {
    let cancelled = false
    fetch("/api/preview/nodes")
      .then(r => r.json())
      .then(data => {
        if (!cancelled && data.lines?.length) {
          poolRef.current = data.lines
          indexRef.current = 0
          setReady(true)
        }
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [])

  // ── Next line from pool ──
  const nextLine = useCallback((): Line | null => {
    const p = poolRef.current
    if (p.length === 0) return null
    const idx = indexRef.current % p.length
    indexRef.current = idx + 1
    return p[idx]
  }, [])

  // ── Sediment breathing cycle ──
  useEffect(() => {
    if (!ready) return

    let timeout: ReturnType<typeof setTimeout>
    const alive = { current: true }

    const cycle = () => {
      if (!alive.current) return

      const breath = drawBreath()
      const now = Date.now()

      if (breath.kind === "silence") {
        // Held silence — nothing new. Just wait.
        timeout = setTimeout(cycle, breath.delay)
        return
      }

      const line = nextLine()
      if (!line) {
        timeout = setTimeout(cycle, 4000)
        return
      }

      const isInhale = breath.kind === "inhale"
      const newId = ++lineId

      // Push new line to top of stack
      setStack(prev => {
        const next = [...prev]
        // If stack is full, mark bottom for removal
        if (next.length >= MAX_VISIBLE) {
          next[next.length - 1] = { ...next[next.length - 1], fadeOut: true }
        }
        // Insert at top
        next.unshift({ id: newId, line, fadeOut: false, isInhale })
        return next
      })

      // Inhale lines vanish quickly (after ~4 breaths = ~3s)
      if (isInhale) {
        timeout = setTimeout(() => {
          if (!alive.current) return
          setStack(prev => prev.map(v =>
            v.id === newId ? { ...v, fadeOut: true } : v
          ))
          timeout = setTimeout(() => {
            if (!alive.current) return
            setStack(prev => prev.filter(v => v.id !== newId))
            timeout = setTimeout(cycle, 3000 + Math.random() * 5000)
          }, 2000)
        }, 3000)
      } else {
        // Remove bottom faded-out lines and continue
        timeout = setTimeout(() => {
          if (!alive.current) return
          setStack(prev => prev.filter(v => !v.fadeOut))
          timeout = setTimeout(cycle, breath.delay)
        }, 1000) // let the CSS transition render
      }
    }

    // Initial breather delay
    timeout = setTimeout(cycle, 2000)
    return () => { alive.current = false; clearTimeout(timeout) }
  }, [ready, nextLine])

  // ── Password handling ──
  const handlePasswordKey = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    setPassword(val)
    setKeystrokes(val.length > 0 ? "·".repeat(Math.min(val.length, 3)) : "")
    if (authError) onClearError()
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!password.trim()) return
    setUnlocking(true)
    onPasswordSubmit(password.trim())
    setTimeout(() => setUnlocking(false), 1500)
  }

  const handleTearClick = () => {
    passwordRef.current?.focus()
  }

  // ── Line style helper ──
  const lineStyle = (vl: VisibleLine, idx: number): React.CSSProperties => {
    const cascadeIdx = Math.min(idx, OPACITY_CASCADE.length - 1)
    const opacity = vl.fadeOut ? 0 : OPACITY_CASCADE[cascadeIdx]
    const fontSize = FONT_SIZE_CASCADE[Math.min(cascadeIdx, FONT_SIZE_CASCADE.length - 1)]
    const color = vl.line.stage
      ? STAGE_COLORS[vl.line.stage] ?? "#555555"
      : vl.isInhale
        ? (Math.random() > 0.5 ? "#f59e0b" : "#a78bfa")
        : "#555555"

    return {
      opacity,
      fontSize: `${fontSize}px`,
      color,
      fontStyle: vl.line.type === "dream" ? "italic" : "normal",
      textDecoration: vl.line.scar || vl.isInhale ? "line-through" : "none",
      filter: vl.line.blur ? "blur(3px)" : "none",
      letterSpacing: cascadeIdx > 0 ? `${-0.02 * cascadeIdx}em` : "normal",
      transition: "opacity 2s ease-in-out, font-size 2s ease-in-out",
      lineHeight: vl.fadeOut ? "0" : "1.6",
      wordBreak: "break-word",
    }
  }

  const formatText = (vl: VisibleLine): string =>
    vl.line.obfuscated ? obfuscateText(vl.line.text) : vl.line.text

  return (
    <div className="flex flex-col items-center justify-center h-screen w-full bg-[#0c0c0c] font-mono select-none overflow-hidden">
      {/* ── The Sediment Column ── */}
      <div className="flex flex-col items-center justify-center w-[30%] min-w-[280px] max-w-[640px] px-6"
        style={{ paddingTop: "25vh", paddingBottom: "15vh" }}
      >
        {/* Visible sedimentation */}
        <div className="flex flex-col items-start w-full space-y-3">
          {stack.map((vl, idx) => (
            <div
              key={vl.id}
              className="w-full text-left"
              style={lineStyle(vl, idx)}
            >
              {formatText(vl)}
            </div>
          ))}
        </div>

        {/* ── The Tear ── */}
        <div className="mt-8 w-full relative">
            {/* Hairline crack */}
            <div
              className="h-px w-full bg-[#1a1a1a] cursor-text shadow-[0_0_6px_rgba(100,100,100,0.15)]"
              onClick={handleTearClick}
            />
            <input
              ref={passwordRef}
              type="password"
              value={password}
              onChange={handlePasswordKey}
              className="absolute inset-0 opacity-0 cursor-text"
              autoFocus
            />

            {/* Keystrokes rendered below the tear */}
            <div className="text-[#555] text-[12px] font-mono text-center mt-3 min-h-[1.2rem] select-none transition-opacity duration-1000">
              {keystrokes}
            </div>

            {/* Auth error */}
            {authError && (
              <div
                className="text-[#ef4444] text-[9px] text-center mt-1 cursor-pointer"
                onClick={onClearError}
              >
                {authError}
              </div>
            )}

            {/* Unlock */}
            <form onSubmit={handleSubmit} className="text-center mt-2">
              <button
                type="submit"
                disabled={!password.trim() || unlocking}
                className="text-[10px] text-[#666] font-mono cursor-pointer transition-colors hover:text-[#4ade80] disabled:text-[#333] disabled:cursor-not-allowed"
              >
                [{unlocking ? "…" : "unlock"}]
              </button>
            </form>
          </div>
      </div>
    </div>
  )
})
