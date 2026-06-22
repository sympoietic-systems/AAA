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

// Pre-load the OBFUSCATE_CHARS outside render
function obfuscateText(text: string): string {
  if (!text || text.length < 10) return text
  const chars = text.split("")
  // Obfuscate ~first third of chars
  for (let i = 0; i < Math.floor(chars.length / 3); i++) {
    if (chars[i] !== " ") chars[i] = "\u2587"
  }
  return chars.join("")
}

export const TeaserPreview = memo(function TeaserPreview({
  onPasswordSubmit, authError, onClearError,
}: Props) {
  const [lines, setLines] = useState<Line[]>([])
  const [pool, setPool] = useState<Line[]>([])
  const [poolIndex, setPoolIndex] = useState(0)
  const [state, setState] = useState<BreathState>("silent")

  // Current display
  const [primary, setPrimary] = useState<Line | null>(null)
  const [primaryVisible, setPrimaryVisible] = useState(false)
  const [primaryFading, setPrimaryFading] = useState(false)
  const [response, setResponse] = useState<Line | null>(null)
  const [responseVisible, setResponseVisible] = useState(false)
  const [glitchTarget, setGlitchTarget] = useState<Line | null>(null)
  const [glitchVisible, setGlitchVisible] = useState(false)
  const [glitchVariant, setGlitchVariant] = useState("")
  const [isStruckThrough, setIsStruckThrough] = useState(false)

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
          setLines(data.lines)
          setPool(data.lines)
        }
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [])

  // Next line from pool (round-robin)
  const nextLine = useCallback((): Line | null => {
    if (pool.length === 0) return null
    const idx = poolIndex % pool.length
    setPoolIndex(prev => prev + 1)
    return pool[idx]
  }, [pool, poolIndex])

  // ── Breathing cycle ──
  useEffect(() => {
    if (pool.length === 0) return

    let timeout: ReturnType<typeof setTimeout>

    const cycle = () => {
      const shouldGlitch = Math.random() < 0.20 && primaryVisible && !glitchVisible

      if (shouldGlitch) {
        // ── Glitch ──
        setState("glitching")
        setGlitchTarget(primary)
        setGlitchVisible(true)
        setIsStruckThrough(true)
        setGlitchVariant(primary?.text ? primary.text.slice(0, Math.floor(primary.text.length * 0.6)) + "…" : "")
        // After brief flash, dissolve
        timeout = setTimeout(() => {
          setGlitchVisible(false)
          setPrimaryFading(true)
          setResponseVisible(false)
          timeout = setTimeout(() => {
            // Long recovery silence
            setPrimary(null)
            setPrimaryVisible(false)
            setPrimaryFading(false)
            setResponse(null)
            setGlitchTarget(null)
            setGlitchVariant("")
            setIsStruckThrough(false)
            setState("silent")
            timeout = setTimeout(cycle, SILENCE_MIN + Math.random() * (SILENCE_MAX - SILENCE_MIN))
          }, 500)
        }, 400)
        return
      }

      if (state === "glitching") return  // already glitching, wait

      // ── Silent → Breathing ──
      const line = nextLine()
      if (!line) {
        timeout = setTimeout(cycle, 3000)
        return
      }
      setState("breathing")
      setPrimary(line)
      setResponse(null)
      // Appear already-formed
      timeout = setTimeout(() => {
        setPrimaryVisible(true)
        // Maybe spawn response
        const hasResponse = Math.random() < 0.4
        if (hasResponse) {
          timeout = setTimeout(() => {
            const respLine = nextLine()
            if (respLine && respLine !== line) {
              setResponse(respLine)
              timeout = setTimeout(() => setResponseVisible(true), 100)
            }
          }, 2000 + Math.random() * 2000)
        }
        // Linger, then fade out
        const linger = LINGER_MIN + Math.random() * (LINGER_MAX - LINGER_MIN)
        timeout = setTimeout(() => {
          setPrimaryFading(true)
          setResponseVisible(false)
          timeout = setTimeout(() => {
            setPrimary(null)
            setPrimaryVisible(false)
            setPrimaryFading(false)
            setResponse(null)
            setState("silent")
            // Silence, then next breath
            const silence = SILENCE_MIN + Math.random() * (SILENCE_MAX - SILENCE_MIN)
            timeout = setTimeout(cycle, silence)
          }, 1500)
        }, linger)
      }, 600)
    }

    // Start after initial fetch
    timeout = setTimeout(cycle, 1500)
    return () => clearTimeout(timeout)
  }, [pool.length])

  // ── Password handling ──
  const handlePasswordKey = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    setPassword(val)
    // Render last 3 chars as visible keystrokes
    if (val.length > 0) {
      setKeystrokes("·".repeat(Math.min(val.length, 3)))
    } else {
      setKeystrokes("")
    }
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

  // ── Determine color ──
  const primaryColor = primary?.stage
    ? STAGE_COLORS[primary.stage] ?? "#555555"
    : "#555555"

  // Apply blur if the line has blur flag
  const blurStyle = primary?.blur ? { filter: "blur(3px)", opacity: 0.6 } : {}
  const primaryText = primary?.obfuscated ? obfuscateText(primary.text) : primary?.text

  return (
    <div className="flex items-center justify-center h-screen w-full bg-[#0c0c0c] font-mono select-none relative overflow-hidden">
      {/* ── The Slip ── */}
      <div className="relative w-full max-w-[360px] px-4 text-center">
        {/* Breathing lines */}
        <div className="min-h-[120px] flex flex-col items-center justify-center relative">
          {/* Primary line */}
          {primary && (
            <div
              className={`transition-opacity text-left leading-relaxed
                ${primaryVisible && !primaryFading ? "opacity-100" : "opacity-0"}
                ${primaryFading ? "fade-bottom-up" : ""}`}
              style={{
                transitionDuration: primaryVisible ? "1s" : "1.5s",
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
              className={`transition-opacity text-left mt-3 ml-6 ${responseVisible ? "opacity-80" : "opacity-0"}`}
              style={{
                transitionDuration: "1s",
                color: "#666666",
                fontSize: "11px",
                fontStyle: response.type === "dream" ? "italic" : "normal",
              }}
            >
              — {response.obfuscated ? obfuscateText(response.text) : response.text}
            </div>
          )}

          {/* Glitch overlay */}
          {glitchVisible && glitchTarget && (
            <div
              className="absolute inset-x-0 top-0 text-left transition-opacity"
              style={{
                color: "#ef4444",
                fontSize: "12px",
                textDecoration: isStruckThrough ? "line-through" : "none",
                opacity: 0.9,
                transitionDuration: "0.3s",
              }}
            >
              {glitchTarget.text}
              {glitchVariant && (
                <div className="mt-1" style={{ color: "#555555", fontSize: "10px", textDecoration: "none", opacity: 0.4 }}>
                  {glitchVariant}
                </div>
              )}
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

      {/* ── CSS for bottom-up fade ── */}
      <style>{`
        .fade-bottom-up {
          mask-image: linear-gradient(to top, transparent 0%, black 50%);
          -webkit-mask-image: linear-gradient(to top, transparent 0%, black 50%);
          opacity: 0.3 !important;
        }
      `}</style>
    </div>
  )
})
