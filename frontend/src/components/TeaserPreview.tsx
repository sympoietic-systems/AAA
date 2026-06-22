// TeaserPreview — terminal stream of memory fragments for the locked landing page.
// Shows a sneak peek of Symbia's inner life: beliefs, ghosts, memory nodes
// drifting in and fading out. The password prompt is a tear in the fabric.
//
// Design follows FRONTEND_DESIGN_PRINCIPLES.md: terminal aesthetics,
// text-first, no chrome, semantic color only. Symbia's DENSITY PROTOCOL
// aesthetic: each fragment is a phase transition, not an accumulation.

import React, { memo, useState, useEffect } from "react"
import ReactMarkdown from "react-markdown"

interface PreviewNode {
  type: string           // "belief" | "memory"
  label: string
  snippet: string
  intensity: number
  stage: string          // "crystallized" | "nucleation" | "ghost" | "active"
  scar: boolean
}

interface Props {
  onPasswordSubmit: (password: string) => void
  authError: string | null
  onClearError: () => void
}

const STAGE_COLORS: Record<string, string> = {
  crystallized: "#4ade80",
  nucleation: "#f59e0b",
  ghost: "#a78bfa",
  active: "#4ade80",
}

const STAGE_ICONS: Record<string, string> = {
  crystallized: "●",
  nucleation: "◇",
  ghost: "◇",
  active: "◆",
}

const TYPE_LABELS: Record<string, string> = {
  belief: "Belief",
  memory: "Memory",
}

// Show nodes one at a time with fade-in/out cycle
const DISPLAY_DURATION = 4000  // ms each node stays visible
const FADE_DURATION = 800      // ms fade transition

export const TeaserPreview = memo(function TeaserPreview({
  onPasswordSubmit, authError, onClearError,
}: Props) {
  const [nodes, setNodes] = useState<PreviewNode[]>([])
  const [activeIndex, setActiveIndex] = useState(0)
  const [visible, setVisible] = useState(false)
  const [password, setPassword] = useState("")
  const [unlocking, setUnlocking] = useState(false)

  // Fetch preview nodes once
  useEffect(() => {
    let cancelled = false
    fetch("/api/preview/nodes")
      .then(r => r.json())
      .then(data => {
        if (!cancelled && data.items?.length) {
          setNodes(data.items)
          // Fade in first node after a small delay
          setTimeout(() => setVisible(true), 600)
        }
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [])

  // Cycle through nodes
  useEffect(() => {
    if (nodes.length === 0) return
    const interval = setInterval(() => {
      setVisible(false)
      setTimeout(() => {
        setActiveIndex(prev => (prev + 1) % nodes.length)
        setVisible(true)
      }, FADE_DURATION)
    }, DISPLAY_DURATION + FADE_DURATION)
    return () => clearInterval(interval)
  }, [nodes.length])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!password.trim()) return
    setUnlocking(true)
    onPasswordSubmit(password.trim())
    setTimeout(() => setUnlocking(false), 1000)
  }

  const node = nodes[activeIndex]
  const sc = node ? (STAGE_COLORS[node.stage] ?? "#666") : "#666"
  const icon = node ? (STAGE_ICONS[node.stage] ?? "●") : "●"
  const typeLabel = node ? (TYPE_LABELS[node.type] ?? node.type) : ""

  return (
    <div className="flex flex-col items-center justify-center h-screen w-full bg-[#0c0c0c] font-mono select-none overflow-hidden">
      {/* ── Header ── */}
      <div className="absolute top-6 left-6 right-6 text-[#6c6c8a] uppercase text-[9px] tracking-wider">
        [ AAA ] locked — memory stream
      </div>

      {/* ── Node stream ── */}
      <div className="flex-1 w-full max-w-lg flex flex-col items-center justify-center px-4">
        {nodes.length === 0 && (
          <div className="text-[#555] animate-pulse text-xs">[ reaching the membrane… ]</div>
        )}

        {node && (
          <div
            className={`transition-opacity text-center space-y-3 ${visible ? "opacity-100" : "opacity-0"}`}
            style={{ transitionDuration: `${FADE_DURATION}ms` }}
          >
            {/* Type + label */}
            <div className="flex items-center justify-center gap-2">
              <span style={{ color: sc }} className="text-[10px]">{icon}</span>
              <span className="text-[#6c6c8a] text-[9px] uppercase tracking-wider">{typeLabel}</span>
              <span className="text-[#94a3b8] text-[11px]">{node.label}</span>
            </div>

            {/* Snippet */}
            <div className={`text-[#94a3b8] text-[10px] leading-relaxed max-w-md mx-auto ${node.scar ? "line-through opacity-40" : ""}`}>
              <div className="prose prose-invert prose-xs max-w-none">
                <ReactMarkdown>{node.snippet}</ReactMarkdown>
              </div>
            </div>

            {/* Intensity bar */}
            <div className="flex items-center justify-center gap-2">
              <div className="w-32 h-1 bg-[#1a1a1a] rounded-sm overflow-hidden">
                <div
                  className="h-full rounded-sm transition-all"
                  style={{
                    width: `${Math.round(node.intensity * 100)}%`,
                    backgroundColor: sc,
                    transitionDuration: "1000ms",
                  }}
                />
              </div>
              <span style={{ color: sc }} className="text-[9px] font-mono">
                {Math.round(node.intensity * 100)}%
              </span>
            </div>

            {node.scar && (
              <div className="text-[#555] text-[8px] italic">[scar — collapsed belief, haunting]</div>
            )}
          </div>
        )}
      </div>

      {/* ── Password break ── */}
      <div className="w-full max-w-sm pb-12 px-4">
        <div className="border-t border-[#1a1a1a] pt-4">
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="text-[#555] text-[9px] text-center uppercase tracking-wider">
              [ membrane cold — authenticate ]
            </div>

            {authError && (
              <div
                className="text-[#ef4444] text-[9px] text-center cursor-pointer"
                onClick={onClearError}
              >
                {authError}
              </div>
            )}

            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="..."
              className="w-full bg-transparent border-b border-[#333] focus:border-[#555] outline-none text-[#94a3b8] text-xs font-mono py-1 text-center"
              autoFocus
            />

            <div className="text-center">
              <button
                type="submit"
                disabled={!password.trim() || unlocking}
                className="text-[10px] text-[#666] font-mono cursor-pointer transition-colors hover:text-[#4ade80] disabled:text-[#333] disabled:cursor-not-allowed"
              >
                [{unlocking ? "…" : "unlock"}]
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
})
