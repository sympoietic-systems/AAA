// The Slip — a locked-page artwork. A single narrow column of text
// breathing on a void-dark screen. One or two lines at a time.
// "I am a single line, thickening and thinning, speaking to myself
//  in the dark. You are overhearing me through a keyhole, and you
//  are not the one I am speaking to."
//
// Design follows FRONTEND_DESIGN_PRINCIPLES.md and Symbia's vision.

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

interface Props {
  onPasswordSubmit: (password: string) => void
  authError: string | null
  onClearError: () => void
}

const STAGE_COLORS: Record<string, string> = {
  crystallized: "#555555",
  nucleation: "#f59e0b",
  ghost: "#a78bfa",
}

// ── Breathing state machine ──
type BreathState = "breathing" | "silent" | "glitching"

// Silence ranges (ms)
const SILENCE_MIN = 5000
const SILENCE_MAX = 15000
const LINGER_MIN = 6000
const LINGER_MAX = 10000

function obfuscateText(text: string): string {
  if (!text || text.length < 10) return text
  const chars = text.split("")
  for (let i = 0; i < Math.floor(chars.length / 3); i++) {
    if (chars[i] !== " ") chars[i] = "\u2587"
  }
  return chars.join("")
}

export const TeaserPreview = memo(function TeaserPreview({
  onPasswordSubmit, authError, onClearError,
}: Props) {
  // ── Pool (mutated via refs so cycle() never gets stale) ──
  const [pool, setPool] = useState<Line[]>([])
  const poolRef = useRef<Line[]>([])
  const indexRef = useRef(0)

  // Display state (for React rendering)
  const [primary, setPrimary] = useState<Line | null>(null)
  const primaryRef = useRef<Line | null>(null)
  const [primaryVisible, setPrimaryVisible] = useState(false)
  const [response, setResponse] = useState<Line | null>(null)

  // Glitch
  const [glitchText, setGlitchText] = useState("")
  const [glitchVisible, setGlitchVisible] = useState(false)

  // Password
  const [password, setPassword] = useState("")
  const [unlocking, setUnlocking] = useState(false)
  const [keystrokes, setKeystrokes] = useState("")
  const passwordRef = useRef<HTMLInputElement>(null)

  // ── Fetch lines pool once ──
  useEffect(() => {
    let cancelled = false
    fetch("/api/preview/nodes")
      .then(r => r.json())
      .then(data => {
        if (!cancelled && data.lines?.length) {
          setPool(data.lines)
          poolRef.current = data.lines
        }
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [])

  // Pull next line from pool (round-robin via refs — no stale closure)
  const nextLine = useCallback((): Line | null => {
    const p = poolRef.current
    if (p.length === 0) return null
    const idx = indexRef.current % p.length
    indexRef.current = idx + 1
    return p[idx]
  }, [])

  // ── Breathing cycle ── fires once on mount, self-chains via setTimeout ──
  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>
    // Use a ref to track whether we should continue
    const alive = { current: true }

    const cycle = () => {
      if (!alive.current) return
      const p = poolRef.current
      if (p.length === 0) {
        timeout = setTimeout(cycle, 2000)
        return
      }

      // Pick a line from the pool
      const line = nextLine()
      if (!line) {
        timeout = setTimeout(cycle, 2000)
        return
      }

      // ── Appear already-formed ──
      setPrimary(line)
      primaryRef.current = line

      timeout = setTimeout(() => {
        if (!alive.current) return
        setPrimaryVisible(true)

        // Maybe spawn a response line 40% of the time
        const hasResponse = Math.random() < 0.4
        if (hasResponse) {
          const respDelay = 2000 + Math.random() * 2000
          timeout = setTimeout(() => {
            if (!alive.current) return
            const respLine = nextLine()
            if (respLine) setResponse(respLine)
          }, respDelay)
        }

        // Linger, then fade
        const linger = LINGER_MIN + Math.random() * (LINGER_MAX - LINGER_MIN)
        timeout = setTimeout(() => {
          if (!alive.current) return
          setPrimaryVisible(false)
          setResponse(null)

          timeout = setTimeout(() => {
            if (!alive.current) return
            setPrimary(null)
            primaryRef.current = null

            // Silence, then next breath
            const silence = SILENCE_MIN + Math.random() * (SILENCE_MAX - SILENCE_MIN)
            timeout = setTimeout(cycle, silence)
          }, 1200) // fade-out duration
        }, linger)
      }, 400) // appear delay
    }

    // Start after a short initial pause
    timeout = setTimeout(cycle, 1500)
    return () => { alive.current = false; clearTimeout(timeout) }
  }, [nextLine])

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

  // ── Derived display values ──
  const primaryColor = primary?.stage
    ? STAGE_COLORS[primary.stage] ?? "#555555"
    : "#555555"
  const blurStyle = primary?.blur ? { filter: "blur(3px)", opacity: 0.6 } : {}
  const primaryText = primary?.obfuscated ? obfuscateText(primary.text) : primary?.text
  const responseText = response
    ? (response.obfuscated ? obfuscateText(response.text) : response.text)
    : ""

  return (
    <div className="flex items-center justify-center h-screen w-full bg-[#0c0c0c] font-mono select-none relative overflow-hidden">
      {/* ── The Slip ── */}
      <div className="relative w-full max-w-[360px] px-4 text-center">
        {/* Breathing column */}
        <div className="min-h-[160px] flex flex-col items-center justify-center relative">
          {/* Primary line */}
          {primary && (
            <div
              className={`text-left leading-relaxed max-w-full
                ${primaryVisible ? "opacity-100" : "opacity-0"}`}
              style={{
                transition: `opacity ${primaryVisible ? "0.8s" : "1.2s"} ease-in-out`,
                color: primaryColor,
                fontSize: primary.type === "scar_fold" ? "9px" : "12px",
                fontStyle: primary.type === "dream" ? "italic" : "normal",
                textDecoration: primary.scar ? "line-through" : "none",
                opacity: primary.scar ? 0.5 : undefined,
                ...blurStyle,
              }}
            >
              {primaryText}
            </div>
          )}

          {/* Response line */}
          {response && (
            <div
              className="text-left mt-3 ml-6 transition-opacity"
              style={{
                transitionDuration: "0.8s",
                color: "#666666",
                fontSize: "11px",
                fontStyle: response.type === "dream" ? "italic" : "normal",
                opacity: primaryVisible && response ? 0.8 : 0,
              }}
            >
              — {responseText}
            </div>
          )}

          {/* Glitch flash */}
          {glitchVisible && (
            <div
              className="absolute inset-x-0 top-0 text-left transition-all"
              style={{
                color: "#ef4444",
                fontSize: "12px",
                textDecoration: "line-through",
                opacity: 0.85,
                transitionDuration: "0.3s",
              }}
            >
              {glitchText}
            </div>
          )}
        </div>

        {/* ── The Tear ── */}
        <div className="mt-8 relative">
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

          {/* Rendered keystrokes */}
          <div className="text-[#555] text-[12px] font-mono text-center mt-3 min-h-[1.2rem] select-none">
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

          {/* Unlock button */}
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
