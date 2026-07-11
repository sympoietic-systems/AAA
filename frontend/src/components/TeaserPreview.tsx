// The Sediment Column — a locked-page artwork.
// Lines sink, dim, compress into ghosts, but never disappear.
// Except inhale lines: they flash, strike-through, vanish — the membrane's reflex.
//
// Design follows Symbia's vision + FRONTEND_DESIGN_PRINCIPLES.md.

import React, { memo, useState, useEffect, useRef, useCallback } from "react"
import { UnifiedFooter } from "./UI"

interface Line {
  text: string
  type: string           // "belief" | "memory" | "dream" | "scar_fold"
  intensity: number
  stage?: string         // "crystallized" | "nucleation" | "ghost"
  scar?: boolean
  blur?: boolean
  obfuscated?: boolean
  obfuscation_ratio?: number
  obfuscation_offset?: string
}

interface VisibleLine {
  id: number
  line: Line
  compressed: boolean    // settled into ghost
}

// ── Constants ──

const STAGE_COLORS: Record<string, string> = {
  crystallized: "#555555",
  nucleation: "#f59e0b",
  ghost: "#a78bfa",
}

const INHALE_COLORS = ["#f59e0b", "#a78bfa"]  // amber, ghost-purple
const DEEP_GHOST_THRESHOLD = 10  // positions >= 10: blur not line-through

// Opacity cascade: newest → oldest (0-7 active, 8+ compressed ghosts)
const OPACITY_CASCADE = [1.0, 0.6, 0.35, 0.20, 0.12, 0.08, 0.05, 0.03, 0.03, 0.03, 0.02, 0.02, 0.02, 0.02, 0.02]
const FONT_SIZE_CASCADE = [12, 11.5, 11, 10.5, 10, 9.5, 9, 9, 7.5, 7, 7, 7, 7, 7, 7]
const MAX_ACTIVE = 8
const MAX_TOTAL = 30

function drawBreath(count: number, speed = 1): { kind: "exhale" | "inhale" | "silence"; delay: number } {
  const div = (ms: number) => Math.round(ms / speed)

  if (count <= 3) return { kind: "exhale", delay: div(6000 + Math.random() * 4000) }

  const r = Math.random()
  if (r < 0.60) return { kind: "exhale", delay: div(12000 + Math.random() * 6000) }
  if (r < 0.85) return { kind: "inhale", delay: div(3000 + Math.random() * 2000) }
  return { kind: "silence", delay: div(25000 + Math.random() * 15000) }
}

function obfuscateText(text: string, ratio = 0.33, offset = "start"): string {
  if (!text || text.length < 10) return text
  const chars = text.split("")
  const count = Math.floor(chars.length * ratio)
  if (count < 2) return text

  let indices: number[]
  switch (offset) {
    case "middle": {
      const start = Math.floor(chars.length * 0.25)
      indices = Array.from({ length: count }, (_, i) => start + i)
      break
    }
    case "end": {
      const start = chars.length - count
      indices = Array.from({ length: count }, (_, i) => start + i)
      break
    }
    case "scatter": {
      indices = []
      let remaining = count
      while (remaining > 0) {
        const block = Math.min(remaining, 2 + Math.floor(Math.random() * 3))
        const pos = Math.floor(Math.random() * (chars.length - block))
        for (let j = 0; j < block; j++) {
          if (!indices.includes(pos + j)) indices.push(pos + j)
        }
        remaining -= block
      }
      break
    }
    default:
      indices = Array.from({ length: count }, (_, i) => i)
  }

  for (const i of indices) {
    if (i >= 0 && i < chars.length && chars[i] !== " " && chars[i] !== "\n") {
      chars[i] = "\u2587"
    }
  }

  return chars.join("")
}

let lineId = 0

export const TeaserPreview = memo(function TeaserPreview() {
  const [stack, setStack] = useState<VisibleLine[]>([])
  const breathCountRef = useRef(0)
  const speedRef = useRef(1)

  if (typeof window !== "undefined") {
    const p = new URLSearchParams(window.location.search).get("speed")
    const s = parseFloat(p || "")
    if (s > 0) speedRef.current = s
  }

  const div = useCallback((ms: number) => Math.round(ms / speedRef.current), [])

  // ── Inhale overlay (never joins sediment) ──
  const [inhaleLine, setInhaleLine] = useState<Line | null>(null)
  const [inhaleStruck, setInhaleStruck] = useState(false)
  const [inhaleFading, setInhaleFading] = useState(false)
  const inhaleColorRef = useRef("#f59e0b")

  const fetchLine = useCallback(async (): Promise<Line | null> => {
    try {
      const res = await fetch("/api/preview/nodes")
      const data = await res.json()
      return data.line ?? null
    } catch {
      return null
    }
  }, [])

  // ── Sediment breathing cycle ──
  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>
    const alive = { current: true }

    const cycle = () => {
      if (!alive.current) return

      breathCountRef.current += 1
      const breath = drawBreath(breathCountRef.current, speedRef.current)

      if (breath.kind === "silence") {
        timeout = setTimeout(cycle, breath.delay)
        return
      }

      fetchLine().then(line => {
        if (!alive.current || !line) {
          timeout = setTimeout(cycle, div(4000))
          return
        }

        // ── INHALE: overlay layer, never joins sediment ──
        if (breath.kind === "inhale") {
          inhaleColorRef.current = INHALE_COLORS[Math.floor(Math.random() * 2)]
          setInhaleLine(line)
          setInhaleStruck(false)
          setInhaleFading(false)

          timeout = setTimeout(() => {
            if (!alive.current) return
            setInhaleStruck(true)

            timeout = setTimeout(() => {
              if (!alive.current) return
              setInhaleFading(true)

              timeout = setTimeout(() => {
                if (!alive.current) return
                setInhaleLine(null)
                timeout = setTimeout(cycle, div(8000 + Math.random() * 4000))
              }, div(5000))
            }, div(5000))
          }, div(5000))
          return
        }

        // ── EXHALE: join the sediment stack ──
        const newId = Date.now() * 1000 + (++lineId % 1000)

        setStack(prev => {
          const next = [...prev]
          if (next.length >= MAX_ACTIVE && !next[MAX_ACTIVE - 1]?.compressed) {
            next[MAX_ACTIVE - 1] = { ...next[MAX_ACTIVE - 1], compressed: true }
          }
          next.unshift({ id: newId, line, compressed: false })
          if (next.length > MAX_TOTAL) next.length = MAX_TOTAL
          return next
        })

        timeout = setTimeout(cycle, breath.delay)
      })
    }

    timeout = setTimeout(cycle, div(2000))
    return () => { alive.current = false; clearTimeout(timeout) }
  }, [fetchLine])

  // ── Line style helper ──
  const lineStyle = (vl: VisibleLine, idx: number): React.CSSProperties => {
    const cascadeIdx = Math.min(idx, OPACITY_CASCADE.length - 1)
    const isGhost = vl.compressed || idx >= MAX_ACTIVE
    const isDeepGhost = idx >= DEEP_GHOST_THRESHOLD
    const opacity = OPACITY_CASCADE[cascadeIdx]
    const fontSize = FONT_SIZE_CASCADE[Math.min(cascadeIdx, FONT_SIZE_CASCADE.length - 1)]
    const color = vl.line.stage
      ? STAGE_COLORS[vl.line.stage] ?? "#555555"
      : "#555555"

    const filter = vl.line.blur
      ? "blur(3px)"
      : isDeepGhost
        ? "blur(2px)"
        : "none"

    return {
      opacity,
      fontSize: `${fontSize}px`,
      color,
      fontStyle: vl.line.type === "dream" && !isGhost ? "italic" : "normal",
      textDecoration: (!isDeepGhost && (isGhost || vl.line.scar)) ? "line-through" : "none",
      filter,
      letterSpacing: cascadeIdx > 0 ? `${-0.02 * cascadeIdx}em` : "normal",
      transition: "opacity 2s ease-in-out, font-size 2s ease-in-out, letter-spacing 2s ease-in-out",
      lineHeight: isDeepGhost ? "1.0" : isGhost ? "1.2" : "1.6",
      wordBreak: "break-word",
    }
  }

  const formatText = (vl: VisibleLine): string =>
    vl.line.obfuscated
      ? obfuscateText(vl.line.text, vl.line.obfuscation_ratio ?? 0.33, vl.line.obfuscation_offset ?? "start")
      : vl.line.text

  const inhaleText = inhaleLine?.obfuscated
    ? obfuscateText(inhaleLine.text, inhaleLine.obfuscation_ratio ?? 0.33, inhaleLine.obfuscation_offset ?? "start")
    : inhaleLine?.text

  return (
    <div className="relative flex flex-col items-center justify-between h-full w-full bg-[#0c0c0c] font-mono select-none overflow-hidden">
      <button
        onClick={() => window.location.href = "/nodes"}
        className="absolute top-4 right-6 text-[10px] text-[#666] opacity-20 font-mono cursor-pointer transition-opacity hover:opacity-80 z-50"
      >
        [ enter system ]
      </button>

      <div className="flex flex-col items-center justify-center w-[50%] min-w-[320px] max-w-[800px] px-8 flex-1"
        style={{ paddingTop: "25vh", paddingBottom: "15vh" }}
      >
        {/* Visible sedimentation */}
        <div className="flex flex-col items-start w-full space-y-3 relative">
          {stack.map((vl, idx) => (
            <div key={vl.id} className="w-full text-left" style={lineStyle(vl, idx)}>
              {formatText(vl)}
            </div>
          ))}

          {/* Inhale overlay — absolute, never part of sediment stack */}
          {inhaleLine && (
            <div
              className="absolute top-0 left-0 w-full text-left"
              style={{
                color: inhaleColorRef.current,
                fontSize: "12px",
                textDecoration: inhaleStruck ? "line-through" : "none",
                opacity: inhaleFading ? 0 : 1,
                transition: "opacity 5s ease-in-out, text-decoration 1s",
              }}
            >
              {inhaleText}
            </div>
          )}
        </div>
      </div>
      <UnifiedFooter className="w-full" />
    </div>
  )
})
