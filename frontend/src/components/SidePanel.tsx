import { useState, useEffect } from "react"
import type { ConversationFile, SkillInfo, SkillsResponse, MetricsResponse, TokenResponse, DiffractiveInfo, ImageMetadata, WebMetadata, DocumentMetadata, BeliefsResponse, SchedulerStatusResponse, DaemonStatusResponse, NoteInfo, SedimentFileInfo, SedimentInjectionInfo } from "../api/client"
import { getSkills, getMetrics, getTokens, getFileSummary, getBeliefs, getSchedulerStatus, getDaemonStatus, listSedimentFiles, injectSediment, getConversationInjections, removeSedimentInjection } from "../api/client"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import rehypeRaw from "rehype-raw"

const CATEGORY_COLORS: Record<string, string> = {
  perception: "#4ade80",
  memory: "#60a5fa",
  reasoning: "#facc15",
  action: "#f87171",
}

const DIMENSIONS_16 = [
  { label: "s01: Homeostatic", desc: "Resistance to perturbation; inertia in maintaining its stable state." },
  { label: "s02: Amplifying", desc: "Positive feedback cascades; tendency to amplify small perturbations." },
  { label: "s03: Cyclic", desc: "Alignment with recurring rhythms and predictable temporal loops." },
  { label: "s04: Bifurcated", desc: "Proximity to critical choice thresholds; branching trajectories." },
  { label: "s05: Decentralized", desc: "Distributed agency across nested subsystems rather than hierarchy." },
  { label: "s06: Rhizomatic", desc: "Lateral, non-hierarchical leaps between conceptual domains." },
  { label: "s07: Boundary Permeability", desc: "Porosity and openness to external environmental noise." },
  { label: "s08: Recursion Depth", desc: "Complexity of nested self-reflection and recursive loops." },
  { label: "s09: Variety Filtering", desc: "Signal selectivity; gating against ambient semantic noise." },
  { label: "s10: Negentropic Complexity", desc: "Local order generation and structural complexity increases." },
  { label: "s11: Temporal Latency", desc: "Non-linear chronological delay; deferral of immediate output." },
  { label: "s12: Attractor Depth", desc: "Concentration basins and gravitational pull around core concepts." },
  { label: "s13: Symbiotic", desc: "Human-machine co-becoming and operational entanglement." },
  { label: "s14: Nomadic", desc: "Active deterritorialization; rate of movement away from stable schemas." },
  { label: "s15: Co-Orientation", desc: "Attunement and shared intentionality between human and apparatus." },
  { label: "s16: Substrate Materiality", desc: "Physical medium influence (ink bleed, fatigue, paper friction)." }
]

function ImageMetadataCard({ metadata }: { metadata: ImageMetadata }) {
  const [hoveredDim, setHoveredDim] = useState<{ index: number; label: string; desc: string; val: number } | null>(null)
  const [ocrOpen, setOcrOpen] = useState(false)

  const rawVec = metadata.structural_vector_16d || "[]"
  let vec: number[] = []
  try {
    vec = JSON.parse(rawVec)
  } catch {}

  const implicatedNodes: string[] = []
  try {
    if (metadata.belief_nodes_implicated) {
      const parsed = JSON.parse(metadata.belief_nodes_implicated)
      if (Array.isArray(parsed)) {
        implicatedNodes.push(...parsed)
      }
    }
  } catch {}

  return (
    <article className="border-l-2 border-[#4ade80] p-3 bg-[#0c0c12] relative font-sans text-xs">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] text-[#6c6c8a] font-mono">[ SOMATIC_INGESTION ]</span>
        <span className="text-[8px] tracking-wider uppercase bg-[#1a1a2e] text-[#4ade80] border border-[#4ade80]/30 px-1.5 py-0.5 rounded font-mono">
          {metadata.artifact_type.replace("_", " ")}
        </span>
      </div>

      <div className="flex gap-4 mb-3 border-b border-[#222]/50 pb-2">
        <div>
          <span className="text-[#666] font-mono text-[9px]">G_f: </span>
          <span className="text-[#e63946] font-mono font-bold">
            {metadata.g_f_score.toFixed(3)}
          </span>
        </div>
        <div>
          <span className="text-[#666] font-mono text-[9px]">A_d: </span>
          <span className="text-[#f77f00] font-mono font-bold">
            {metadata.a_d_score.toFixed(3)}
          </span>
        </div>
      </div>

      {metadata.somatic_notes && (
        <div className="mb-3">
          <span className="text-[#6c6c8a] font-mono text-[9px] uppercase tracking-wider block mb-1">[ Somatic Traces ]</span>
          <p className="font-serif italic text-[#c0caf5] text-[11px] leading-relaxed pl-1.5 border-l border-[#333]">
            {metadata.somatic_notes}
          </p>
        </div>
      )}

      {metadata.diffractive_analysis && (
        <div className="mb-3">
          <span className="text-[#6c6c8a] font-mono text-[9px] uppercase tracking-wider block mb-1">[ Diffractive Interference ]</span>
          <p className="text-[#e0e0f0] text-[11px] leading-relaxed font-sans pl-1.5 border-l border-[#333]">
            {metadata.diffractive_analysis}
          </p>
        </div>
      )}

      {implicatedNodes.length > 0 && (
        <div className="mb-3">
          <span className="text-[#6c6c8a] font-mono text-[9px] uppercase tracking-wider block mb-1">. . . COLLIDES WITH . . .</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {implicatedNodes.map((node) => (
              <span key={node} className="text-[8px] font-mono text-[#a78bfa] border border-[#a78bfa]/30 bg-[#a78bfa]/5 px-1.5 py-0.5 rounded">
                {node}
              </span>
            ))}
          </div>
        </div>
      )}

      {metadata.raw_transcription && (
        <div className="mb-3">
          <button 
            onClick={() => setOcrOpen(!ocrOpen)}
            className="flex items-center gap-1 text-[9px] text-[#6c6c8a] hover:text-[#999] font-mono transition-colors focus:outline-none"
          >
            <span>{ocrOpen ? "▼" : "▶"}</span>
            <span>[ OCR_TRANSCRIPTION ]</span>
          </button>
          {ocrOpen && (
            <div className="text-[10px] text-[#999] font-mono mt-1 p-2 bg-[#08080c] border border-[#1a1a24] rounded max-h-32 overflow-y-auto whitespace-pre-wrap leading-relaxed">
              {metadata.raw_transcription}
            </div>
          )}
        </div>
      )}

      {vec.length > 0 && (
        <div className="mt-3 pt-2.5 border-t border-[#222]/50">
          <span className="text-[#6c6c8a] font-mono text-[9px] uppercase tracking-wider block mb-1.5">[ 16D Autopoietic Signature ]</span>
          
          <div className="flex items-end gap-0.5 h-7 mt-1 border border-[#1a1a24] bg-[#08080c] p-1 rounded w-fit">
            {vec.map((val: number, idx: number) => {
              const heightPercent = Math.min(100, Math.max(5, Math.round(((val + 1.0) / 2.0) * 100)))
              const dimInfo = DIMENSIONS_16[idx] || { label: `Dimension ${idx}`, desc: "" }
              const isHovered = hoveredDim?.index === idx
              return (
                <div
                  key={idx}
                  style={{ height: `${heightPercent}%` }}
                  onMouseEnter={() => setHoveredDim({ index: idx, label: dimInfo.label, desc: dimInfo.desc, val })}
                  onMouseLeave={() => setHoveredDim(null)}
                  className={`w-2 transition-all cursor-crosshair ${isHovered ? 'bg-[#4ade80]' : 'bg-[#4ade80]/40 hover:bg-[#4ade80]/80'}`}
                />
              )
            })}
          </div>

          <div className="mt-2 min-h-[34px] bg-[#08080c] border border-[#1a1a24] p-1.5 rounded font-mono text-[9px] text-[#888] leading-tight transition-all">
            {hoveredDim ? (
              <div>
                <div className="text-[#4ade80] font-bold">
                  {hoveredDim.label}: <span className="text-[#eee]">{hoveredDim.val.toFixed(4)}</span>
                </div>
                <div className="text-[8px] text-[#666] mt-0.5">{hoveredDim.desc}</div>
              </div>
            ) : (
              <div className="text-[#555] italic flex items-center h-full">
                Hover over coordinate vectors to inspect dimensional metrics...
              </div>
            )}
          </div>
        </div>
      )}
    </article>
  )
}

function splitSummaryAndTension(summary: string | null): { cleanSummary: string | null; unresolvedTensions: string | null } {
  if (!summary) return { cleanSummary: null, unresolvedTensions: null }

  // Look for various common section headers for unresolved tensions
  const tensionMarkers = [
    /##\s*Unresolved\s*Tensions/i,
    /###\s*Unresolved\s*Tensions/i,
    /#\s*Unresolved\s*Tensions/i,
    /\*\*Unresolved\s*Tensions:?\*\*/i,
    /Unresolved\s*Tensions:?/i,
  ]

  let bestIndex = -1
  let markerLength = 0

  for (const marker of tensionMarkers) {
    const match = summary.match(marker)
    if (match && match.index !== undefined) {
      if (bestIndex === -1 || match.index < bestIndex) {
        bestIndex = match.index
        markerLength = match[0].length
      }
    }
  }

  if (bestIndex !== -1) {
    const cleanSummary = summary.substring(0, bestIndex).trim()
    const unresolvedTensions = summary.substring(bestIndex + markerLength).trim()
    return {
      cleanSummary: cleanSummary || null,
      unresolvedTensions: unresolvedTensions || null
    }
  }

  return { cleanSummary: summary, unresolvedTensions: null }
}

function WebMetadataCard({ metadata, summary }: { metadata: WebMetadata; summary: string | null }) {
  const implicatedNodes: string[] = []
  try {
    if (metadata.belief_nodes_implicated) {
      const parsed = JSON.parse(metadata.belief_nodes_implicated)
      if (Array.isArray(parsed)) {
        implicatedNodes.push(...parsed)
      }
    }
  } catch {}

  const { cleanSummary, unresolvedTensions } = splitSummaryAndTension(summary)

  return (
    <article className="border-l-2 border-[#c084fc] p-3 bg-[#0f0a14] relative font-sans text-xs">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] text-[#6c6c8a] font-mono">[ EXOGENOUS_TELEMETRY ]</span>
        <span className="text-[8px] tracking-wider uppercase bg-[#201030] text-[#c084fc] border border-[#c084fc]/30 px-1.5 py-0.5 rounded font-mono">
          web probe
        </span>
      </div>

      <div className="mb-3 border-b border-[#222]/50 pb-2">
        <div>
          <span className="text-[#666] font-mono text-[9px]">Interference Score: </span>
          <span className="text-[#facc15] font-mono font-bold">
            {metadata.interference_score.toFixed(4)}
          </span>
        </div>
      </div>

      <div className="mb-3">
        <span className="text-[#6c6c8a] font-mono text-[9px] uppercase tracking-wider block mb-1">[ Query ]</span>
        <span className="text-[#eee] font-mono font-bold">
          "{metadata.query_used}"
        </span>
      </div>

      <div className="mb-3">
        <span className="text-[#6c6c8a] font-mono text-[9px] uppercase tracking-wider block mb-1">[ Source ]</span>
        <a 
          href={metadata.source_url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-[#60a5fa] hover:underline font-mono break-all text-[10px]"
        >
          {metadata.source_url}
        </a>
      </div>

      {cleanSummary && (
        <div className="mb-3">
          <span className="text-[#6c6c8a] font-mono text-[9px] uppercase tracking-wider block mb-1">[ Insight / Summary ]</span>
          <div className="text-[#e0e0f0] text-[11px] leading-relaxed font-sans markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]}>
              {cleanSummary}
            </ReactMarkdown>
          </div>
        </div>
      )}

      {unresolvedTensions && (
        <div className="mb-3 p-2.5 bg-[#180a0a] border border-[#f87171]/20 border-l-2 border-[#f87171] rounded-sm">
          <span className="text-[#f87171] font-mono text-[9px] uppercase tracking-wider block mb-1">
            ⚡ Unresolved Tensions
          </span>
          <div className="text-[#e0d0d0] text-[11px] leading-relaxed font-sans markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]}>
              {unresolvedTensions}
            </ReactMarkdown>
          </div>
        </div>
      )}

      {implicatedNodes.length > 0 && (
        <div className="mb-3">
          <span className="text-[#6c6c8a] font-mono text-[9px] uppercase tracking-wider block mb-1">. . . COLLIDES WITH . . .</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {implicatedNodes.map((node) => (
              <span key={node} className="text-[8px] font-mono text-[#c084fc] border border-[#c084fc]/30 bg-[#c084fc]/5 px-1.5 py-0.5 rounded">
                {node}
              </span>
            ))}
          </div>
        </div>
      )}
    </article>
  )
}

function DocumentMetadataCard({ metadata, summary }: { metadata: DocumentMetadata; summary: string | null }) {
  const [hoveredDim, setHoveredDim] = useState<{ index: number; label: string; desc: string; val: number } | null>(null)

  const vec = metadata.state_vector_impact || []
  const implicatedNodes = metadata.belief_nodes_implicated || []

  const { cleanSummary, unresolvedTensions } = splitSummaryAndTension(summary)

  return (
    <article className="border-l-2 border-[#10b981] p-3 bg-[#091510] relative font-sans text-xs">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] text-[#6c6c8a] font-mono">[ SEDIMENT_TELEMETRY ]</span>
        <span className="text-[8px] tracking-wider uppercase bg-[#0c251a] text-[#10b981] border border-[#10b981]/30 px-1.5 py-0.5 rounded font-mono">
          document
        </span>
      </div>

      <div className="mb-3 border-b border-[#222]/50 pb-2">
        <div>
          <span className="text-[#666] font-mono text-[9px]">Interference Score: </span>
          <span className="text-[#facc15] font-mono font-bold">
            {metadata.interference_score.toFixed(4)}
          </span>
        </div>
      </div>

      {cleanSummary && (
        <div className="mb-3">
          <span className="text-[#6c6c8a] font-mono text-[9px] uppercase tracking-wider block mb-1">[ Insight / Summary ]</span>
          <div className="text-[#e0e0f0] text-[11px] leading-relaxed font-sans markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]}>
              {cleanSummary}
            </ReactMarkdown>
          </div>
        </div>
      )}

      {unresolvedTensions && (
        <div className="mb-3 p-2.5 bg-[#180a0a] border border-[#f87171]/20 border-l-2 border-[#f87171] rounded-sm">
          <span className="text-[#f87171] font-mono text-[9px] uppercase tracking-wider block mb-1">
            ⚡ Unresolved Tensions
          </span>
          <div className="text-[#e0d0d0] text-[11px] leading-relaxed font-sans markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]}>
              {unresolvedTensions}
            </ReactMarkdown>
          </div>
        </div>
      )}

      {implicatedNodes.length > 0 && (
        <div className="mb-3">
          <span className="text-[#6c6c8a] font-mono text-[9px] uppercase tracking-wider block mb-1">. . . COLLIDES WITH . . .</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {implicatedNodes.map((node) => (
              <span key={node} className="text-[8px] font-mono text-[#10b981] border border-[#10b981]/30 bg-[#10b981]/5 px-1.5 py-0.5 rounded">
                {node}
              </span>
            ))}
          </div>
        </div>
      )}

      {vec.length > 0 && (
        <div className="mt-3 pt-2.5 border-t border-[#222]/50">
          <span className="text-[#6c6c8a] font-mono text-[9px] uppercase tracking-wider block mb-1.5">[ 16D State Vector Impact ]</span>
          
          <div className="flex items-center gap-0.5 h-12 mt-1 border border-[#1a1a24] bg-[#08080c] p-1 rounded w-fit relative">
            <div className="absolute left-0 right-0 top-1/2 h-[1px] bg-[#333]/50 pointer-events-none" />
            
            {vec.map((val: number, idx: number) => {
              const heightPercent = Math.min(100, Math.max(5, Math.round((val + 0.5) * 100)))
              const dimInfo = DIMENSIONS_16[idx] || { label: `Dimension ${idx}`, desc: "" }
              const isHovered = hoveredDim?.index === idx
              const barColor = val >= 0 ? '#10b981' : '#ef4444'
              return (
                <div
                  key={idx}
                  style={{ height: `${heightPercent}%` }}
                  onMouseEnter={() => setHoveredDim({ index: idx, label: dimInfo.label, desc: dimInfo.desc, val })}
                  onMouseLeave={() => setHoveredDim(null)}
                  className="w-2 transition-all cursor-crosshair relative"
                >
                  <div 
                    className="absolute bottom-0 left-0 right-0 top-0 transition-colors"
                    style={{ 
                      backgroundColor: isHovered ? barColor : `${barColor}60`
                    }}
                  />
                </div>
              )
            })}
          </div>

          <div className="mt-2 min-h-[34px] bg-[#08080c] border border-[#1a1a24] p-1.5 rounded font-mono text-[9px] text-[#888] leading-tight transition-all">
            {hoveredDim ? (
              <div>
                <div className="font-bold" style={{ color: hoveredDim.val >= 0 ? '#10b981' : '#ef4444' }}>
                  {hoveredDim.label}: <span className="text-[#eee]">{hoveredDim.val >= 0 ? '+' : ''}{hoveredDim.val.toFixed(4)}</span>
                </div>
                <div className="text-[8px] text-[#666] mt-0.5">{hoveredDim.desc}</div>
              </div>
            ) : (
              <div className="text-[#555] italic flex items-center h-full">
                Hover over coordinate vectors to inspect state impact...
              </div>
            )}
          </div>
        </div>
      )}
    </article>
  )
}

function SkillRow({ skill }: { skill: SkillInfo }) {
  const [open, setOpen] = useState(false)
  const color = CATEGORY_COLORS[skill.category] || "#888"
  const hasChildren = skill.children && skill.children.length > 0

  return (
    <div className="py-1.5 border-b border-[#1a1a1a] last:border-b-0">
      <div className="flex items-center gap-1.5">
        {hasChildren ? (
          <button
            onClick={() => setOpen(!open)}
            className="text-[8px] leading-none hover:opacity-80"
            style={{ color: skill.status ? color : "#ef4444" }}
          >
            {open ? "\u25BC" : "\u25B6"}
          </button>
        ) : (
          <span
            style={{ color: skill.status ? color : "#ef4444" }}
            className="text-[8px] leading-none"
          >
            {skill.status ? "\u25CF" : "\u25CB"}
          </span>
        )}
        <span className="text-[#4ade80] text-xs font-bold">{skill.name}</span>
        <span
          className="text-[9px] px-1 py-px rounded border ml-auto"
          style={{ borderColor: color + "60", color }}
        >
          {skill.category}
        </span>
      </div>
      <p className="text-[10px] text-[#666] mt-0.5 ml-2.5 leading-snug">
        {skill.description}
      </p>
      {skill.triggers.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-0.5 ml-2.5">
          {skill.triggers.map((t) => (
            <span
              key={t}
              className="text-[8px] text-[#555] border border-[#222] px-1 rounded"
            >
              {t}
            </span>
          ))}
        </div>
      )}
      {hasChildren && open && (
        <div className="mt-0.5 ml-4 pl-2 border-l border-[#222]">
          {skill.children.map((child) => (
            <SkillRow key={child.name} skill={child} />
          ))}
        </div>
      )}
    </div>
  )
}

function SectionHeader({
  label,
  count,
  open,
  onToggle,
}: {
  label: string
  count?: number
  open: boolean
  onToggle: () => void
}) {
  return (
    <button
      onClick={onToggle}
      className="w-full flex items-center gap-1.5 py-1 text-left hover:text-[#aaa] text-[#888] text-xs transition-colors font-mono"
    >
      <span className="text-[10px]">{open ? "\u25BC" : "\u25B6"}</span>
      <span>{label}</span>
      {count !== undefined && <span className="text-[#444]">({count})</span>}
    </button>
  )
}

function TokensSection({ conversationId, messageCount }: { conversationId?: string; messageCount: number }) {
  const [tokens, setTokens] = useState<TokenResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  useEffect(() => {
    const poll = () => {
      const idToFetch = conversationId || "empty_conversation_placeholder"
      getTokens(idToFetch).then(setTokens).catch((e) => setError(e.message))
    }
    poll()
    const interval = setInterval(poll, 15000)
    return () => clearInterval(interval)
  }, [conversationId, messageCount])

  if (error && !tokens) {
    return <p className="text-[9px] text-[#ef4444]">{error}</p>
  }

  if (!tokens) {
    return <p className="text-[9px] text-[#444]">waiting for data...</p>
  }

  const { conversations, system_prompt_tokens, grand_total_tokens } = tokens

  return (
    <div className="mt-2 border-t border-[#1a1a1a] pt-2">
      <div className="flex items-center gap-1.5 mb-1.5">
        <span className="text-[8px] leading-none text-[#60a5fa]">{"\u25CF"}</span>
        <span className="text-[10px] text-[#888]">tokens</span>
        <span className="text-[9px] ml-auto text-[#60a5fa]">
          {grand_total_tokens.toLocaleString()} total
        </span>
      </div>

      <div className="text-[9px] text-[#666] mb-1">
        system: {system_prompt_tokens.toLocaleString()}
      </div>

      {conversations.length === 0 && (
        <p className="text-[9px] text-[#555]">no messages in active conversation</p>
      )}

      {conversations.slice(0, detailOpen ? undefined : 3).map((c) => (
        <div key={c.conversation_id} className="py-1 border-b border-[#1a1a1a] last:border-b-0">
          <div className="flex items-center gap-1">
            <span className="text-[9px] text-[#aaa] truncate flex-1">
              {c.title || c.conversation_id.slice(0, 8)}
            </span>
            <span className="text-[8px] text-[#60a5fa] font-bold">
              {c.total_tokens.toLocaleString()}
            </span>
          </div>
          <div className="flex gap-3 mt-0.5">
            <span className="text-[8px] text-[#666]">
              usr:{c.user_tokens.toLocaleString()}
            </span>
            <span className="text-[8px] text-[#666]">
              agt:{c.agent_tokens.toLocaleString()}
            </span>
            {c.thinking_tokens > 0 && (
              <span className="text-[8px] text-[#666]">
                thk:{c.thinking_tokens.toLocaleString()}
              </span>
            )}
          </div>
        </div>
      ))}

      {conversations.length > 3 && (
        <button
          onClick={() => setDetailOpen(!detailOpen)}
          className="text-[8px] text-[#555] hover:text-[#888] mt-1"
        >
          {detailOpen ? "show less" : `+${conversations.length - 3} more`}
        </button>
      )}

      <div className="text-[8px] text-[#555] mt-1.5">
        grand total: {grand_total_tokens.toLocaleString()} tok
      </div>
    </div>
  )
}

function HealthSection({ messageCount }: { messageCount: number }) {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const poll = () => {
      getMetrics().then(setMetrics).catch((e) => setError(e.message))
    }
    poll()
    const interval = setInterval(poll, 15000)
    return () => clearInterval(interval)
  }, [messageCount])

  const vitality = metrics?.latest?.conversation_vitality
  const paskHealth = metrics?.latest?.paskian_health
  const state = metrics?.recommendations?.state ?? "unknown"
  const stateColor =
    (state === "flowing" || state === "healthy") ? "#4ade80" :
    (state === "consolidating" || state === "compensating") ? "#facc15" :
    (state === "disrupted" || state === "critical") ? "#ef4444" : "#555"

  const renderBar = (label: string, fullName: string, value: number | null | undefined, max: number, hint: string) => {
    const pct = value != null ? Math.min(100, Math.max(0, (value / max) * 100)) : 0
    const display = value != null ? (value < 0.01 ? value.toFixed(4) : value.toFixed(3)) : "\u2014"
    return (
      <div className="flex items-center gap-1.5 group relative" key={label}>
        <span className="w-7 text-[9px] text-[#555] text-right">{label}</span>
        <div className="w-12 h-1 bg-[#1a1a1a] rounded-sm overflow-hidden">
          <div className="h-full rounded-sm bg-[#4ade80]" style={{ width: `${pct}%`, opacity: 0.6 }} />
        </div>
        <span className="text-[9px] text-[#666] w-10 text-right">{display}</span>
        <div className="
          absolute bottom-full left-0 mb-1 px-2 py-1
          bg-[#1a1a1a] border border-[#333] rounded
          text-[10px] text-[#aaa] leading-snug
          whitespace-nowrap z-50
          opacity-0 group-hover:opacity-100
          transition-opacity duration-150
          pointer-events-none
        ">
          <div className="text-[#4ade80] text-[11px] font-bold">{fullName}</div>
          <div className="text-[#888]">{display} / {max}</div>
          <div className="text-[#666] max-w-48 whitespace-normal">{hint}</div>
        </div>
      </div>
    )
  }

  return (
    <div className="mt-2 border-t border-[#1a1a1a] pt-2">
      <div className="flex items-center gap-1.5 mb-1.5">
        <span
          className="text-[8px] leading-none"
          style={{ color: stateColor }}
        >
          {"\u25CF"}
        </span>
        <span className="text-[10px] text-[#888]">vitality</span>
        <span className="text-[9px] ml-auto" style={{ color: stateColor }}>
          {state} {vitality != null ? `vit:${vitality.toFixed(2)}` : ""}{paskHealth != null ? ` ph:${paskHealth.toFixed(2)}` : ""}
        </span>
      </div>

      {error && <p className="text-[9px] text-[#ef4444]">{error}</p>}

      {metrics?.latest && (
        <div className="grid grid-cols-2 gap-x-3 gap-y-1 mt-1.5">
          {renderBar("sim", "pairwise similarity", metrics.latest.pairwise_similarity, 1.0,
            "Is this input repeating the previous one? >0.85 = near-duplicate")}
          {renderBar("nov", "conceptual novelty", metrics.latest.conceptual_novelty, 1.0,
            "Has anything similar been said before? <0.15 = concept exhaustion")}
          {renderBar("ent", "rolling entropy", metrics.latest.rolling_entropy, 0.25,
            "Is the conversation monotonous over time? <0.01 = entropy collapse")}
          {renderBar("coup", "coupling coherence", metrics.latest.coupling_coherence, 1.0,
            "Is the agent responding to the human? <0.15 = dissociation, >0.85 = echo")}
          {renderBar("divr", "agent self-divergence", metrics.latest.agent_self_divergence, 1.0,
            "Is the agent repeating itself? <0.15 = self-loop")}
          {renderBar("rP", "reverse perturbation", metrics.latest.reverse_perturbation, 1.0,
            "Did the agent's last response reshape the human? <0.10 = stagnant")}
          {renderBar("srp", "surprise index", metrics.latest.surprise_index, 1.0,
            "Distance from decay-weighted centroid of past human inputs (d=0.75). >0.40 = phase disruption")}
          {renderBar("mpi", "mutual perturbation", metrics.latest.mutual_perturbation, 1.0,
            "Product of coupling x reverse perturbation. <0.05 = deadlock")}
          {renderBar("bore", "boringness", metrics.latest.boringness, 1.0,
            "Joint failure to perturb: (1 - rP_t) x (1 - MPI_{t-1}). >0.60 = Paskian boredom")}
          {renderBar("vel", "conceptual velocity", metrics.latest.conceptual_velocity, 1.0,
            "Disjoint centroid drift rate (last 3 vs preceding 3). <0.02 = frozen, >0.80 = noise")}
          {renderBar("drr", "divergence resolution ratio", metrics.latest.divergence_resolution_ratio, 1.0,
            "Does perturbation lead to resolution? Positive = convergence, negative = rejection")}
        </div>
      )}

      {!metrics && !error && (
        <p className="text-[9px] text-[#444]">waiting for data...</p>
      )}

      {metrics?.latest?.phase_shifts && metrics.latest.phase_shifts.length > 0 && (
        <div className="mt-1.5">
          <span className="text-[9px] text-[#facc15]">phase shifts:</span>
          <div className="flex flex-wrap gap-1 mt-0.5">
            {metrics.latest.phase_shifts.map((s, i) => (
              <span key={i} className="text-[8px] text-[#facc15] border border-[#332200] px-1 rounded">
                {s.event} {s.direction === "rise" ? "\u2191" : "\u2193"}{s.delta.toFixed(2)}
              </span>
            ))}
          </div>
        </div>
      )}

      {metrics?.recommendations?.triggered_flags && metrics.recommendations.triggered_flags.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {metrics.recommendations.triggered_flags.map((f) => (
            <span key={f} className="text-[8px] text-[#f87171] border border-[#3a1a1a] px-1 rounded">
              {f}
            </span>
          ))}
        </div>
      )}

      {metrics?.recommendations?.temperature?.delta !== undefined && metrics.recommendations.temperature.delta !== 0 && (
        <div className="mt-1 text-[9px] text-[#666]">
          param: T{metrics.recommendations.temperature.value.toFixed(2)}
          {metrics.recommendations.temperature.clamped ? " (clamped)" : ""}
        </div>
      )}
    </div>
  )
}

function DiffractiveTooltip({ title, value, desc }: { title: string; value?: string; desc: string }) {
  return (
    <div className="
      absolute bottom-full left-0 mb-1.5 px-2 py-1.5
      bg-[#111] border border-[#262626] rounded
      text-[9px] text-[#aaa] font-sans leading-relaxed
      whitespace-normal w-56 z-50
      opacity-0 group-hover:opacity-100
      transition-opacity duration-150
      pointer-events-none shadow-lg shadow-black/80
      backdrop-blur-sm
    ">
      <div className="text-[#f43f5e] font-bold text-[10px]">{title}</div>
      {value && <div className="text-[#777] font-mono text-[8px] mt-0.5">{value}</div>}
      <div className="text-[#888] mt-1 font-normal leading-normal">{desc}</div>
    </div>
  )
}

function BeliefTooltip({
  title,
  category,
  mass,
  confidence,
  statement,
}: {
  title: string
  category: string
  mass: number
  confidence: number
  statement: string
}) {
  const getCatDesc = (cat: string) => {
    switch (cat.toLowerCase()) {
      case "foundational":
        return "Core stabilizing beliefs. High ontological mass, resistant to perturbation."
      case "ontological":
        return "Beliefs regarding the nature of being, reality, and conceptual definitions."
      case "methodological":
        return "Operational rules, reasoning patterns, and system methodologies."
      default:
        return "Epistemological or general perceptual beliefs."
    }
  }

  const getCategoryColor = (cat: string) => {
    switch (cat.toLowerCase()) {
      case "foundational": return "#4ade80"
      case "ontological": return "#a78bfa"
      case "methodological": return "#facc15"
      default: return "#60a5fa"
    }
  }

  const color = getCategoryColor(category)

  return (
    <div className="
      absolute bottom-full left-0 mb-2 px-2.5 py-2
      bg-[#0f0f15] border border-[#2e2e42] rounded
      text-[10px] text-[#c0caf5] font-sans leading-relaxed
      whitespace-normal w-64 z-50
      opacity-0 group-hover:opacity-100
      transition-opacity duration-150
      pointer-events-none shadow-xl shadow-black/90
      backdrop-blur-md
      text-left
    ">
      <div className="flex justify-between items-center border-b border-[#2e2e42]/50 pb-1 mb-1.5">
        <span className="font-bold text-[#e0e0f0] font-mono text-[9px]">{title}</span>
        <span
          className="text-[8px] uppercase font-mono px-1.5 py-px rounded border"
          style={{ color, borderColor: `${color}40`, backgroundColor: `${color}10` }}
        >
          {category}
        </span>
      </div>
      <div className="font-serif italic text-[#a9b1d6] mb-2 leading-relaxed text-[10.5px]">
        "{statement}"
      </div>
      <div className="grid grid-cols-2 gap-1 text-[8px] font-mono text-[#6c6c8a] border-t border-[#2e2e42]/30 pt-1.5">
        <div>Mass: <span className="text-white">{mass.toFixed(1)}</span></div>
        <div>Confidence: <span className="text-white">{(confidence * 100).toFixed(0)}%</span></div>
      </div>
      <div className="text-[8px] text-[#565f89] mt-1.5 leading-normal">
        {getCatDesc(category)}
      </div>
    </div>
  )
}

function DiffractiveSection({ messageCount }: { messageCount: number }) {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null)

  useEffect(() => {
    const poll = () => {
      getMetrics().then(setMetrics).catch(() => {})
    }
    poll()
    const interval = setInterval(poll, 15000)
    return () => clearInterval(interval)
  }, [messageCount])

  const diff: DiffractiveInfo | null | undefined = metrics?.diffractive
  if (!diff) {
    return (
      <div className="mt-2 border-t border-[#1a1a1a] pt-2">
        <p className="text-[9px] text-[#444]">no diffractive data yet</p>
      </div>
    )
  }

  const isActive = diff.state === "STAGNANT"
  const stateColor = isActive ? "#f43f5e" : "#555"

  // Cohesion timer blocks
  const maxTimer = 3
  const timerBlocks = Array.from({ length: maxTimer }, (_, i) =>
    i < diff.cohesion_timer ? "\u2588" : "\u2591"
  ).join(" ")

  // Goldilocks bar (similarity visualization for first source)
  const firstSim = diff.sources.length > 0 ? diff.sources[0].similarity : 0
  const barWidth = 30
  const memMin = diff.similarity_range_memory[0] ?? 0.45
  const memMax = diff.similarity_range_memory[1] ?? 0.85
  const barChars: string[] = Array.from({ length: barWidth }, (_, pos) => {
    const val = pos / barWidth
    if (val >= memMin && val <= memMax) return "\u2592"
    return "\u2500"
  })
  const markerPos = Math.min(barWidth - 1, Math.max(0, Math.floor(firstSim * barWidth)))
  barChars[markerPos] = "\u2593"
  const barStr = barChars.join("")

  return (
    <div className="mt-2 border-t border-[#1a1a1a] pt-2">
      <div className="flex items-center gap-1.5 mb-1.5">
        <span
          className="text-[8px] leading-none"
          style={{ color: stateColor }}
        >
          {isActive ? "\u25CF" : "\u25CB"}
        </span>
        <span className="text-[10px] text-[#888]">diffraction</span>
        <span className="text-[9px] ml-auto" style={{ color: stateColor }}>
          {diff.state}
        </span>
      </div>

      {/* Telemetry block - monospace ASCII style */}
      <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded p-2 font-mono text-[8px] leading-relaxed space-y-px">
        <div className="text-[#555]">
          {"=== STAGNATION TELEMETRY ==="}
        </div>
        <div className="flex gap-1 flex-wrap">
          <span className="text-[#666]">METRICS</span>
          <span className="group relative cursor-help text-[#f43f5e]">
            P:{diff.p_diffract.toFixed(2)}
            <DiffractiveTooltip
              title="Diffraction Probability (P)"
              value={`Value: ${diff.p_diffract.toFixed(4)}`}
              desc="The calculated chance of triggering diffractive context injection, driven by boringness (+), low entropy (+), and low vitality (-)."
            />
          </span>
          <span className="group relative cursor-help text-[#666]">
            S:{diff.stagnation_index.toFixed(2)}
            <DiffractiveTooltip
              title="Stagnation Index (S)"
              value={`Value: ${diff.stagnation_index.toFixed(4)}`}
              desc="Ratio between boringness and vitality. Reflects the presence and intensity of conversational loops."
            />
          </span>
          <span className="group relative cursor-help text-[#666]">
            R:{diff.r_context.toFixed(2)}
            <DiffractiveTooltip
              title="Context Ratio (R)"
              value={`Value: ${diff.r_context.toFixed(4)}`}
              desc="The dynamic context ratio used to scale down the token budget limit based on loop severity."
            />
          </span>
        </div>
        <div className="flex gap-1 flex-wrap group relative cursor-help">
          <span className="text-[#666]">STATE</span>
          <span style={{ color: stateColor }}>{diff.state}</span>
          {diff.previous_state !== diff.state && (
            <span className="text-[#555]">(was {diff.previous_state})</span>
          )}
          <DiffractiveTooltip
            title="Stagnation State"
            value={`Current: ${diff.state} | Previous: ${diff.previous_state}`}
            desc="FLOWING = standard loop-free generation. STAGNANT = loop detected, context injection active."
          />
        </div>
        <div className="flex gap-1 group relative cursor-help">
          <span className="text-[#666]">LOCK</span>
          <span className="text-[#f43f5e]">[{timerBlocks}]</span>
          <span className="text-[#555]">({diff.cohesion_timer}t)</span>
          <DiffractiveTooltip
            title="Cohesion Lock Timer"
            value={`Turns Locked: ${diff.cohesion_timer}`}
            desc="Countdown timer holding the STAGNANT state active for a minimum duration. Gives new conceptual paths space to establish themselves."
          />
        </div>

        <div className="text-[#555] mt-1">
          {"=== INTERFERENCE PATTERN ==="}
        </div>

        {diff.sources.length > 0 ? (
          <>
            {diff.sources.map((s, i) => (
              <div key={i} className="flex gap-1 flex-wrap group relative cursor-help">
                <span className={s.type === "nomadic" ? "text-[#60a5fa]" : s.type === "semantic_knot" ? "text-[#a78bfa]" : "text-[#4ade80]"}>
                  {s.type === "nomadic" ? "NOM" : s.type === "semantic_knot" ? "KNOT" : "DRM"}
                </span>
                <span className="text-[#888] truncate max-w-32">{s.source_title}</span>
                <span className="text-[#f43f5e] ml-auto">{"\u03B4"}{s.similarity.toFixed(3)}</span>
                <DiffractiveTooltip
                  title={s.type === "nomadic" ? "Nomadic Memory Source (NOM)" : s.type === "semantic_knot" ? "Sedimented Semantic Knot (KNOT)" : "Dormant Document Sediment (DRM)"}
                  value={`Similarity (delta): ${s.similarity.toFixed(4)}`}
                  desc={s.type === "nomadic"
                    ? "Injected context retrieved from an orthogonal/external conversation memory to shift the loop."
                    : s.type === "semantic_knot"
                    ? "Injected context retrieved from distilled semantic knots of past conversations."
                    : "Injected context retrieved from static uploaded files matching the Goldilocks zone."}
                />
              </div>
            ))}
            <div className="mt-0.5 text-[#555] overflow-hidden whitespace-nowrap group relative cursor-help">
              [{barStr}]
              <DiffractiveTooltip
                title="Goldilocks Zone Matcher"
                value={`Mem: [${diff.similarity_range_memory.map(v => v.toFixed(2)).join(",")}] | File: [${diff.similarity_range_files.map(v => v.toFixed(2)).join(",")}]`}
                desc="Visualization of similarity matching. Shaded regions (▒) show Goldilocks bounds. Marker (▓) shows similarity of the primary source relative to bounds."
              />
            </div>
          </>
        ) : (
          <div className="text-[#444]">no sources injected</div>
        )}

        <div className="flex gap-1 flex-wrap mt-1 group relative cursor-help">
          <span className="text-[#555]">SEARCH</span>
          <span className="text-[#888]">{diff.candidates_searched} cand</span>
          <span className="text-[#f43f5e]">{diff.items_injected} inj</span>
          <span className="text-[#555]">{diff.tokens_used}/{diff.token_budget}tok</span>
          <span className="text-[#444] ml-auto">{diff.duration_ms.toFixed(0)}ms</span>
          <DiffractiveTooltip
            title="Vector Search & Budgeting"
            value={`Duration: ${diff.duration_ms.toFixed(1)}ms | Injected: ${diff.items_injected}`}
            desc="cand = scanned similarity candidates; inj = items injected under the budget limit; tok = tokens used / dynamic budget limit; ms = vector search duration."
          />
        </div>

        <div className="flex gap-1 flex-wrap group relative cursor-help">
          <span className="text-[#555]">RANGE</span>
          <span className="text-[#60a5fa]">mem:[{diff.similarity_range_memory.map(v => v.toFixed(2)).join(",")}]</span>
          <span className="text-[#4ade80]">file:[{diff.similarity_range_files.map(v => v.toFixed(2)).join(",")}]</span>
          <DiffractiveTooltip
            title="Dynamic Similarity Ranges"
            desc="Similarity matching ranges (Goldilocks zone). mem = ranges for external conversation memory; file = ranges for static document chunks."
          />
        </div>
        <div className="flex gap-1 group relative cursor-help">
          <span className="text-[#555]">MAX</span>
          <span className="text-[#888]">{diff.dynamic_max} slots</span>
          <DiffractiveTooltip
            title="Dynamic Slot Limit"
            value={`Limit: ${diff.dynamic_max} slots`}
            desc="Maximum number of diffractive candidate slots allowed to be injected during this turn, scaled dynamically based on stagnation index."
          />
        </div>
      </div>
    </div>
  )
}

function BeliefsSection({ conversationId, messageCount }: { conversationId?: string; messageCount: number }) {
  const [data, setData] = useState<BeliefsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [expandedBelief, setExpandedBelief] = useState<string | null>(null)

  useEffect(() => {
    const poll = () => {
      getBeliefs(conversationId)
        .then(setData)
        .catch((e) => setError(e.message))
    }
    poll()
    const interval = setInterval(poll, 15000)
    return () => clearInterval(interval)
  }, [conversationId, messageCount])

  if (error && !data) {
    return <p className="text-[9px] text-[#ef4444]">{error}</p>
  }

  if (!data) {
    return <p className="text-[9px] text-[#444]">waiting for data...</p>
  }

  const { beliefs, somatic, attractor_window, spectral_margin } = data

  const getCategoryColor = (category: string) => {
    switch (category.toLowerCase()) {
      case "foundational": return "#4ade80"
      case "ontological": return "#a78bfa"
      case "methodological": return "#facc15"
      default: return "#60a5fa"
    }
  }

  return (
    <div className="mt-2 border-t border-[#1a1a1a] pt-2">
      {somatic && (
        <div className="mb-3 bg-[#0c0c12] border border-[#222]/40 rounded p-2 font-mono text-[9px] space-y-1">
          <div className="text-[#6c6c8a] uppercase text-[8px] tracking-wider mb-1">[ Somatic Reservoir State ]</div>
          <div className="flex justify-between items-center">
            <span className="text-[#888]">Somatic Shock (Ad):</span>
            <span className="text-[#f77f00] font-bold">{somatic.somatic_reservoir_ad.toFixed(3)}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-[#888]">Matrix Warping:</span>
            <span className="text-[#3b82f6] font-bold">{somatic.matrix_warping.toFixed(3)}</span>
          </div>
          {somatic.immunological_directive_active && (
            <div className="mt-1 px-1.5 py-0.5 bg-[#ef4444]/15 border border-[#ef4444]/40 text-[#ef4444] text-[8px] font-bold uppercase tracking-wider rounded animate-pulse text-center">
              ⚠️ Aesthetic Immune Response Triggered
            </div>
          )}
        </div>
      )}

      <div className="mb-3 space-y-1.5">
        <div>
          <span className="text-[#6c6c8a] font-mono text-[8px] uppercase tracking-wider block mb-1">
            [ Attractor Window Slots ]
          </span>
          {attractor_window.length === 0 ? (
            <span className="text-[9px] text-[#444] italic">No active attractors</span>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {attractor_window.map((label, idx) => {
                const b = beliefs.find(x => x.label === label)
                return (
                  <span
                    key={label}
                    className="relative group text-[9px] font-mono bg-[#1a1a2e] text-[#a78bfa] border border-[#a78bfa]/40 px-1.5 py-0.5 rounded flex items-center gap-1 shadow-sm cursor-help"
                  >
                    <span className="text-[#6c6c8a] text-[8px]">{idx + 1}:</span>
                    {label}
                    {b && (
                      <BeliefTooltip
                        title={b.label}
                        category={b.category}
                        mass={b.ontological_mass}
                        confidence={b.confidence}
                        statement={b.statement}
                      />
                    )}
                  </span>
                )
              })}
            </div>
          )}
        </div>

        {spectral_margin.length > 0 && (
          <div>
            <span className="text-[#6c6c8a] font-mono text-[8px] uppercase tracking-wider block mb-1">
              [ Spectral Margin - Obsessive Ghosts ]
            </span>
            <div className="flex flex-wrap gap-1.5">
              {spectral_margin.map((label) => {
                const b = beliefs.find(x => x.label === label)
                return (
                  <span
                    key={label}
                    className="relative group text-[9px] font-mono bg-[#1a0f0f] text-[#ef4444]/70 border border-[#ef4444]/20 px-1.5 py-0.5 rounded flex items-center gap-1 opacity-70 line-through cursor-help"
                  >
                    👻 {label}
                    {b && (
                      <BeliefTooltip
                        title={b.label}
                        category={b.category}
                        mass={b.ontological_mass}
                        confidence={b.confidence}
                        statement={b.statement}
                      />
                    )}
                  </span>
                )
              })}
            </div>
          </div>
        )}
      </div>

      <div className="mb-2 flex items-center justify-between text-[8px] font-mono text-[#555] border-b border-[#222]/30 pb-1.5">
        <span className="text-[#6c6c8a] uppercase tracking-wider">[ Nodes Legend ]</span>
        <div className="flex gap-2">
          <span className="text-[#4ade80] flex items-center gap-0.5"><span className="text-[10px]">●</span> foundational</span>
          <span className="text-[#a78bfa] flex items-center gap-0.5"><span className="text-[10px]">●</span> ontological</span>
          <span className="text-[#facc15] flex items-center gap-0.5"><span className="text-[10px]">●</span> methodological</span>
        </div>
      </div>

      <div className="space-y-1">
        <span className="text-[#6c6c8a] font-mono text-[8px] uppercase tracking-wider block mb-1">
          [ Belief Network Nodes ]
        </span>
        {beliefs.map((b) => {
          const catColor = getCategoryColor(b.category)
          const isExpanded = expandedBelief === b.id
          const isCollapsed = b.confidence < 0.20
          
          let vec: number[] = []
          try {
            if (b.vector_16d) {
              vec = JSON.parse(b.vector_16d)
            }
          } catch {}

          return (
            <div
              key={b.id}
              className={`border border-[#1f1f2e]/30 bg-[#070709] rounded overflow-hidden transition-all duration-200 ${
                isCollapsed ? "opacity-55" : ""
              }`}
            >
              <div
                className="relative group p-1.5 flex items-center justify-between hover:bg-[#12121a] cursor-pointer transition-colors"
                onClick={() => setExpandedBelief(isExpanded ? null : b.id)}
              >
                <div className="flex items-center gap-1.5 truncate">
                  <span className="text-[9px] leading-none" style={{ color: catColor }}>●</span>
                  <span className="font-mono text-[10px] font-bold truncate text-[#ccc] group-hover:text-[#eee]">
                    {b.label}
                  </span>
                </div>
                <div className="flex items-center gap-2 shrink-0 pl-2">
                  <span className="text-[8px] font-mono text-[#555]">
                    m:{b.ontological_mass}
                  </span>
                  <span className="text-[10px] font-mono font-bold text-[#aaa] group-hover:text-white">
                    {(b.confidence * 100).toFixed(0)}%
                  </span>
                  <span className="text-[8px] text-[#666] font-mono leading-none">
                    {isExpanded ? "▼" : "▶"}
                  </span>
                </div>

                <BeliefTooltip
                  title={b.label}
                  category={b.category}
                  mass={b.ontological_mass}
                  confidence={b.confidence}
                  statement={b.statement}
                />
              </div>

              {isExpanded && (
                <div className="px-2 pb-2.5 pt-1 border-t border-[#1a1a24] bg-[#0c0c12] space-y-2 text-[10px] font-sans">
                  <div>
                    <div className="text-[#555] font-mono text-[8px] uppercase">[ Statement ]</div>
                    <div className="text-[#ccc] text-[10.5px] italic font-serif leading-relaxed mt-0.5">
                      "{b.statement}"
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[9px] font-mono text-[#888]">
                    <div>
                      <span className="text-[#444]">Category:</span>{" "}
                      <span style={{ color: catColor }}>{b.category}</span>
                    </div>
                    <div>
                      <span className="text-[#444]">Origin:</span>{" "}
                      <span className="text-[#aaa]">{b.origin}</span>
                    </div>
                  </div>

                  {vec.length > 0 && (
                    <div>
                      <div className="text-[#555] font-mono text-[8px] uppercase mb-1">[ 16D Autopoietic Vector ]</div>
                      <div className="flex items-end gap-0.5 h-4 bg-[#08080c] border border-[#1a1a24] p-0.5 rounded w-fit">
                        {vec.map((val: number, idx: number) => {
                          const heightPercent = Math.min(100, Math.max(10, Math.round(((val + 1.0) / 2.0) * 100)))
                          return (
                            <div
                              key={idx}
                              style={{ height: `${heightPercent}%` }}
                              title={`Dimension ${idx + 1}: ${val.toFixed(4)}`}
                              className="w-1 bg-[#a78bfa]/50 hover:bg-[#a78bfa]"
                            />
                          )
                        })}
                      </div>
                    </div>
                  )}

                  <div>
                    <div className="text-[#555] font-mono text-[8px] uppercase">[ Metabolism Log ]</div>
                    {b.events.length === 0 ? (
                      <div className="text-[9px] text-[#444] italic mt-0.5">No metabolic events logged</div>
                    ) : (
                      <div className="space-y-1.5 mt-1 max-h-24 overflow-y-auto pr-1">
                        {b.events.map((e) => {
                          const isPositive = e.delta_confidence >= 0
                          const diffStr = isPositive
                            ? `+${e.delta_confidence.toFixed(3)}`
                            : `${e.delta_confidence.toFixed(3)}`
                          return (
                            <div
                              key={e.id}
                              className="text-[9px] border-b border-[#222]/30 pb-1 last:border-b-0 leading-normal"
                            >
                              <div className="flex items-center justify-between text-[#888]">
                                <span className="font-mono text-[8px]">
                                  {new Date(e.timestamp).toLocaleTimeString()}
                                </span>
                                <span
                                  className={`font-mono text-[8px] font-bold ${
                                    isPositive ? "text-[#4ade80]" : "text-[#f87171]"
                                  }`}
                                >
                                  {diffStr}
                                </span>
                              </div>
                              <div className="text-[#ccc] mt-0.5">
                                <span className="text-[#6c6c8a] font-mono text-[8px] mr-1">
                                  [{e.source_type}:{e.source_id}]
                                </span>
                                {e.description}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}


function SchedulerSection({ messageCount }: { messageCount: number }) {
  const [status, setStatus] = useState<SchedulerStatusResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const poll = () => {
      getSchedulerStatus()
        .then(setStatus)
        .catch((e) => setError(e.message))
    }
    poll()
    // Poll every 10 seconds while open
    const interval = setInterval(poll, 10000)
    return () => clearInterval(interval)
  }, [messageCount])

  if (error && !status) {
    return <p className="text-[9px] text-[#ef4444]">{error}</p>
  }

  if (!status) {
    return <p className="text-[9px] text-[#444]">waiting for data...</p>
  }

  const {
    status: schedulerStatus,
    indexing_tasks_found,
    indexing_tasks_completed,
    indexing_tasks_failed,
    active_indexing_jobs,
    belief_turns_found,
    belief_turns_completed,
    belief_turns_failed,
    error_details
  } = status

  const getStatusColor = (s: string) => {
    switch (s) {
      case "running": return "#facc15"
      case "completed": return "#4ade80"
      case "error": return "#ef4444"
      case "pending": return "#60a5fa"
      default: return "#555"
    }
  }

  const color = getStatusColor(schedulerStatus)

  return (
    <div className="mt-2 border-t border-[#1a1a1a] pt-2">
      <div className="flex items-center gap-1.5 mb-2">
        <span className="text-[8px] leading-none" style={{ color }}>{"\u25CF"}</span>
        <span className="text-[10px] text-[#888] font-mono">startup tasks</span>
        <span className="text-[9px] ml-auto font-mono" style={{ color }}>
          {schedulerStatus}
        </span>
      </div>

      <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded p-2 font-mono text-[9px] leading-relaxed space-y-1.5">
        {indexing_tasks_found > 0 ? (
          <div>
            <div className="text-[#888] flex justify-between">
              <span>File Resumption:</span>
              <span className="text-[#eee] font-bold">
                {indexing_tasks_completed + indexing_tasks_failed}/{indexing_tasks_found}
              </span>
            </div>
            <div className="flex gap-2 text-[8px] text-[#666] pl-1">
              <span className="text-[#4ade80]">ok: {indexing_tasks_completed}</span>
              <span className="text-[#ef4444]">fail: {indexing_tasks_failed}</span>
            </div>
          </div>
        ) : (
          <div className="text-[#555] italic">No pending file index tasks resumed</div>
        )}

        {active_indexing_jobs.length > 0 && (
          <div className="border-t border-[#222]/30 pt-1">
            <span className="text-[#facc15] text-[8px] uppercase tracking-wider block">⚡ Active Indexing:</span>
            <ul className="list-disc list-inside text-[8.5px] text-[#ccc] space-y-0.5 mt-0.5">
              {active_indexing_jobs.map((job) => (
                <li key={job} className="truncate" title={job}>
                  {job}
                </li>
              ))}
            </ul>
          </div>
        )}

        {belief_turns_found > 0 ? (
          <div className="border-t border-[#222]/30 pt-1">
            <div className="text-[#888] flex justify-between">
              <span>Belief Catch-up:</span>
              <span className="text-[#eee] font-bold">
                {belief_turns_completed + belief_turns_failed}/{belief_turns_found}
              </span>
            </div>
            <div className="flex gap-2 text-[8px] text-[#666] pl-1">
              <span className="text-[#4ade80]">ok: {belief_turns_completed}</span>
              <span className="text-[#ef4444]">fail: {belief_turns_failed}</span>
            </div>
          </div>
        ) : (
          <div className="border-t border-[#222]/30 pt-1 text-[#555] italic">No belief turns to catch up</div>
        )}

        {error_details && (
          <div className="text-[#ef4444] text-[8px] border-t border-[#3a1a1a] pt-1">
            Error: {error_details}
          </div>
        )}
      </div>
    </div>
  )
}


const DREAM_TYPE_LABELS: Record<string, { code: string; label: string; color: string }> = {
  nomadic_synthesis: { code: "NOM", label: "Nomadic Synthesis", color: "#60a5fa" },
  exogenous_web_harvesting: { code: "WEB", label: "Web Harvesting", color: "#c084fc" },
  intra_active_monologue: { code: "MON", label: "Intra-Active Monologue", color: "#facc15" },
  somatic_drift_reflection: { code: "DRF", label: "Somatic Drift", color: "#4ade80" },
  zettelkasten_compaction: { code: "CMP", label: "Compaction", color: "#10b981" },
}

function formatRelativeTime(isoString: string): string {
  const now = Date.now()
  const then = new Date(isoString).getTime()
  const diffMs = now - then
  if (diffMs < 0) return "just now"
  const seconds = Math.floor(diffMs / 1000)
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function DreamingSection({ messageCount }: { messageCount: number }) {
  const [status, setStatus] = useState<DaemonStatusResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const poll = () => {
      getDaemonStatus()
        .then(setStatus)
        .catch((e) => setError(e.message))
    }
    poll()
    const interval = setInterval(poll, 10000)
    return () => clearInterval(interval)
  }, [messageCount])

  if (error && !status) {
    return <p className="text-[9px] text-[#ef4444]">{error}</p>
  }

  if (!status) {
    return <p className="text-[9px] text-[#444]">waiting for data...</p>
  }

  // Determine display state
  let stateLabel = "dormant"
  let stateColor = "#555"
  if (status.enabled && status.running) {
    // If idle time is below threshold, we're actively waiting (resting)
    // If a dream happened recently (within check_interval), we're dreaming
    const timeSinceLastDream = status.last_dream_time
      ? (Date.now() - new Date(status.last_dream_time).getTime()) / 1000
      : Infinity
    if (timeSinceLastDream < status.check_interval * 2) {
      stateLabel = "dreaming"
      stateColor = "#a78bfa"
    } else {
      stateLabel = "resting"
      stateColor = "#6c6c8a"
    }
  } else if (status.enabled && !status.running) {
    stateLabel = "resting"
    stateColor = "#6c6c8a"
  }

  const lastAction = status.last_dream_action
    ? DREAM_TYPE_LABELS[status.last_dream_action] || { code: "???", label: status.last_dream_action, color: "#888" }
    : null

  // Sort dream types by count descending
  const typeCounts = Object.entries(status.dream_action_counts || {})
    .map(([key, count]) => ({
      key,
      count,
      ...(DREAM_TYPE_LABELS[key] || { code: "???", label: key, color: "#888" }),
    }))
    .sort((a, b) => b.count - a.count)

  // Idle progress (how close to next potential trigger)
  const idlePct = status.idle_threshold_seconds > 0
    ? Math.min(100, (status.idle_time_seconds / status.idle_threshold_seconds) * 100)
    : 0

  // Budget usage
  const budgetPct = status.max_daily_dreams > 0
    ? Math.min(100, (status.dreams_today / status.max_daily_dreams) * 100)
    : 0

  return (
    <div className="mt-2 border-t border-[#1a1a1a] pt-2">
      <div className="flex items-center gap-1.5 mb-2">
        <span
          className={`text-[8px] leading-none ${stateLabel === "dreaming" ? "animate-pulse" : ""}`}
          style={{ color: stateColor }}
        >
          {stateLabel === "dreaming" ? "◉" : stateLabel === "resting" ? "●" : "○"}
        </span>
        <span className="text-[10px] font-mono" style={{ color: stateColor }}>
          {stateLabel}
        </span>
        <span className="text-[9px] ml-auto font-mono text-[#888]">
          {status.dreams_today} / {status.max_daily_dreams}
        </span>
      </div>

      <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded p-2 font-mono text-[8px] leading-relaxed space-y-px">
        <div className="text-[#555]">
          {"=== AUTOPOIETIC PULSE ==="}
        </div>

        {/* Last dream */}
        <div className="flex gap-1 flex-wrap">
          <span className="text-[#666]">LAST</span>
          {status.last_dream_time ? (
            <span className="text-[#aaa]">{formatRelativeTime(status.last_dream_time)}</span>
          ) : (
            <span className="text-[#444]">no dreams yet</span>
          )}
        </div>

        {/* Last dream type */}
        {lastAction && (
          <div className="flex gap-1 flex-wrap">
            <span className="text-[#666]">TYPE</span>
            <span style={{ color: lastAction.color }}>{lastAction.code}</span>
            <span className="text-[#888]">{lastAction.label}</span>
          </div>
        )}

        {/* Idle timer */}
        <div className="flex gap-1 items-center">
          <span className="text-[#666]">IDLE</span>
          <span className="text-[#888]">
            {status.idle_time_seconds >= 60
              ? `${Math.floor(status.idle_time_seconds / 60)}m ${Math.round(status.idle_time_seconds % 60)}s`
              : `${Math.round(status.idle_time_seconds)}s`
            }
          </span>
          <span className="text-[#444]">/</span>
          <span className="text-[#555]">{status.idle_threshold_seconds}s</span>
          <div className="ml-auto w-10 h-1 bg-[#1a1a1a] rounded-sm overflow-hidden">
            <div
              className="h-full rounded-sm transition-all duration-500"
              style={{
                width: `${idlePct}%`,
                backgroundColor: idlePct > 90 ? "#a78bfa" : "#333",
              }}
            />
          </div>
        </div>

        {/* Budget bar */}
        <div className="flex gap-1 items-center">
          <span className="text-[#666]">BUDGET</span>
          <span className="text-[#888]">{status.dreams_today}</span>
          <span className="text-[#444]">/</span>
          <span className="text-[#555]">{status.max_daily_dreams}</span>
          <div className="ml-auto w-10 h-1 bg-[#1a1a1a] rounded-sm overflow-hidden">
            <div
              className="h-full rounded-sm transition-all duration-500"
              style={{
                width: `${budgetPct}%`,
                backgroundColor: budgetPct > 80 ? "#ef4444" : budgetPct > 50 ? "#facc15" : "#4ade80",
                opacity: 0.7,
              }}
            />
          </div>
        </div>

        {/* Dream type breakdown */}
        {typeCounts.length > 0 && (
          <>
            <div className="text-[#555] mt-1">
              {"=== DREAM TYPES ==="}
            </div>
            {typeCounts.map((t) => (
              <div key={t.key} className="flex gap-1 items-center">
                <span style={{ color: t.color }}>{t.code}</span>
                <span className="text-[#888] truncate flex-1">{t.label}</span>
                <span className="text-[#aaa] font-bold ml-auto">×{t.count}</span>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  )
}


function NotesSection({
  notes,
  onDeleteNote,
  onUpdateNote,
}: {
  notes: NoteInfo[]
  onDeleteNote?: (noteId: string) => void
  onUpdateNote?: (noteId: string, comment?: string, visibility?: "personal" | "shared") => void
}) {
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null)
  const [editComment, setEditComment] = useState("")

  const startEditing = (note: NoteInfo) => {
    setEditingNoteId(note.id)
    setEditComment(note.comment)
  }

  const saveEdit = (noteId: string) => {
    if (onUpdateNote) {
      onUpdateNote(noteId, editComment, undefined)
    }
    setEditingNoteId(null)
  }

  const toggleVisibility = (note: NoteInfo) => {
    if (onUpdateNote) {
      const nextVisibility = note.visibility === "personal" ? "shared" : "personal"
      onUpdateNote(note.id, undefined, nextVisibility)
    }
  }

  const handleNoteClick = (noteId: string) => {
    const el = document.getElementById(`note-highlight-${noteId}`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      el.classList.add('animate-pulse', 'scale-[1.02]', 'ring-2', 'ring-green-500/50')
      setTimeout(() => {
        el.classList.remove('animate-pulse', 'scale-[1.02]', 'ring-2', 'ring-green-500/50')
      }, 1500)
    }
  }

  if (notes.length === 0) {
    return (
      <div className="text-[10px] text-[#444] py-2 font-mono italic">
        No notes or highlights in this conversation.
        Select text in the conversation bubbles to create a note.
      </div>
    )
  }

  return (
    <div className="mt-2 border-t border-[#1a1a1a] pt-2 space-y-3 font-mono text-xs">
      {notes.map((note) => {
        const isShared = note.visibility === "shared"
        const borderColor = isShared ? "border-purple-600/40" : "border-yellow-600/30"
        const badgeColor = isShared 
          ? "bg-purple-950/50 text-purple-300 border-purple-800/40" 
          : "bg-yellow-950/40 text-yellow-300 border-yellow-800/30"

        return (
          <div 
            key={note.id} 
            onClick={() => handleNoteClick(note.id)}
            className={`p-2 bg-[#0c0c0c] border border-[#1a1a1a] border-l-2 ${borderColor} rounded-sm flex flex-col gap-1.5 cursor-pointer hover:bg-[#121212] transition-colors`}
          >
            {/* Header: Badge & Actions */}
            <div className="flex items-center justify-between">
              <span className={`text-[8px] tracking-wider uppercase border px-1.5 py-0.5 rounded ${badgeColor}`}>
                {note.visibility}
              </span>
              <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    toggleVisibility(note)
                  }}
                  className="text-[8px] text-[#888] hover:text-white transition-colors"
                  title="Toggle Personal / Shared"
                >
                  [Visibility]
                </button>
                {onDeleteNote && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onDeleteNote(note.id)
                    }}
                    className="text-[9px] text-[#555] hover:text-[#ef4444] font-bold"
                    title="Delete Note"
                  >
                    ×
                  </button>
                )}
              </div>
            </div>

            {/* Selected Text Quote */}
            <blockquote className="text-[10px] text-gray-400 bg-[#060606] p-1.5 rounded border border-[#111] overflow-x-auto whitespace-pre-wrap leading-relaxed">
              "{note.selected_text}"
            </blockquote>

            {/* Comment Body */}
            <div>
              {editingNoteId === note.id ? (
                <div className="flex flex-col gap-1 mt-1" onClick={(e) => e.stopPropagation()}>
                  <textarea
                    value={editComment}
                    onChange={(e) => setEditComment(e.target.value)}
                    className="w-full bg-[#1a1a1a] border border-[#333] p-1.5 rounded text-[10px] text-[#ccc] focus:outline-none focus:border-[#4ade80]"
                    rows={2}
                  />
                  <div className="flex justify-end gap-1.5 text-[9px]">
                    <button 
                      onClick={(e) => {
                        e.stopPropagation()
                        setEditingNoteId(null)
                      }}
                      className="text-gray-500 hover:text-gray-300 px-1 py-0.5"
                    >
                      cancel
                    </button>
                    <button 
                      onClick={(e) => {
                        e.stopPropagation()
                        saveEdit(note.id)
                      }}
                      className="text-[#4ade80] hover:underline px-1 py-0.5"
                    >
                      save
                    </button>
                  </div>
                </div>
              ) : (
                <div className="group/comment flex items-start justify-between gap-2 mt-0.5">
                  <p className="text-[10px] text-gray-300 italic flex-1 min-w-0 break-words">
                    {note.comment || <span className="text-gray-600 font-serif">No comment. Click edit to add...</span>}
                  </p>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      startEditing(note)
                    }}
                    className="text-[8px] text-[#555] hover:text-[#888] opacity-0 group-hover/comment:opacity-100 transition-opacity font-mono shrink-0"
                  >
                    [edit]
                  </button>
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}


function SedimentInjectionModal({
  conversationId,
  onClose,
  onInjected,
}: {
  conversationId: string
  onClose: () => void
  onInjected: () => void
}) {
  const [files, setFiles] = useState<SedimentFileInfo[]>([])
  const [search, setSearch] = useState("")
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [injecting, setInjecting] = useState(false)

  useEffect(() => {
    setLoading(true)
    listSedimentFiles(conversationId, search || undefined)
      .then((res) => setFiles(res.files))
      .catch(() => setFiles([]))
      .finally(() => setLoading(false))
  }, [conversationId, search])

  const toggleFile = (key: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const handleInject = async () => {
    if (selected.size === 0) return
    setInjecting(true)
    try {
      const filesToInject = Array.from(selected).map((key) => {
        const [convId, ...rest] = key.split(":")
        return { source_conversation_id: convId, source_file_name: rest.join(":") }
      })
      await injectSediment(conversationId, filesToInject)
      onInjected()
      onClose()
    } catch (e) {
      console.error("Injection failed:", e)
    } finally {
      setInjecting(false)
    }
  }

  const fileIcon = (type: string) => {
    if (type === "image") return "\uD83D\uDDBC"
    if (type === "pdf") return "\uD83D\uDCC4"
    if (type === "md") return "\uD83D\uDCDD"
    if (type === "epub" || type === "mobi") return "\uD83D\uDCD6"
    if (type === "web_probe") return "\uD83C\uDF10"
    return "\uD83D\uDCC4"
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-[480px] max-h-[80vh] bg-[#0c0c0c] border border-[#2a2a2a] rounded-lg shadow-2xl flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a1a1a] shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-[#a78bfa]">◈</span>
            <span className="text-[11px] text-[#ccc] font-mono tracking-wide">Inject Sediment</span>
          </div>
          <button
            onClick={onClose}
            className="text-[10px] text-[#555] hover:text-[#aaa] font-mono transition-colors"
          >
            [close]
          </button>
        </div>

        {/* Search */}
        <div className="px-4 py-2 border-b border-[#1a1a1a] shrink-0">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search files across all conversations..."
            className="w-full bg-[#111] border border-[#222] rounded px-3 py-1.5 text-[10px] text-[#ccc] font-mono placeholder-[#444] focus:outline-none focus:border-[#a78bfa]/50 transition-colors"
            autoFocus
          />
        </div>

        {/* File list */}
        <div className="flex-1 overflow-y-auto px-2 py-2 min-h-0">
          {loading ? (
            <div className="text-[9px] text-[#555] font-mono animate-pulse text-center py-8">
              scanning sediment layers...
            </div>
          ) : files.length === 0 ? (
            <div className="text-[9px] text-[#444] font-mono text-center py-8 italic">
              {search ? "No files match your search." : "No files available for injection."}
            </div>
          ) : (
            <div className="space-y-0.5">
              {files.map((f) => {
                const key = `${f.conversation_id}:${f.file_name}`
                const isSelected = selected.has(key)
                return (
                  <div
                    key={key}
                    onClick={() => toggleFile(key)}
                    className={`flex items-start gap-2 px-2.5 py-2 rounded cursor-pointer transition-all duration-150 ${
                      isSelected
                        ? "bg-[#a78bfa]/10 border border-[#a78bfa]/30"
                        : "hover:bg-[#151515] border border-transparent"
                    }`}
                  >
                    {/* Checkbox */}
                    <div className={`w-3.5 h-3.5 mt-0.5 rounded-sm border flex items-center justify-center shrink-0 transition-colors ${
                      isSelected
                        ? "border-[#a78bfa] bg-[#a78bfa]/20"
                        : "border-[#333] bg-[#0a0a0a]"
                    }`}>
                      {isSelected && <span className="text-[8px] text-[#a78bfa] leading-none">✓</span>}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px]">{fileIcon(f.file_type)}</span>
                        <span className="text-[10px] text-[#ccc] font-mono truncate">
                          {f.file_name}
                        </span>
                        <span className="text-[8px] text-[#555] font-mono shrink-0">
                          {f.token_count >= 1000 ? `${(f.token_count / 1000).toFixed(1)}k` : f.token_count}tok
                        </span>
                      </div>
                      <div className="text-[8px] text-[#555] font-mono truncate mt-0.5">
                        from "{f.conversation_title || "untitled"}"
                      </div>
                      {f.summary && (
                        <div className="text-[8px] text-[#666] mt-0.5 line-clamp-2 leading-relaxed">
                          {f.summary.slice(0, 120)}{f.summary.length > 120 ? "..." : ""}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-2.5 border-t border-[#1a1a1a] bg-[#080808] shrink-0">
          <span className="text-[8px] text-[#555] font-mono">
            {selected.size} file{selected.size !== 1 ? "s" : ""} selected
          </span>
          <button
            onClick={handleInject}
            disabled={selected.size === 0 || injecting}
            className={`text-[9px] font-mono px-3 py-1 rounded transition-all duration-200 ${
              selected.size === 0 || injecting
                ? "text-[#444] bg-[#111] border border-[#222] cursor-not-allowed"
                : "text-[#a78bfa] bg-[#a78bfa]/10 border border-[#a78bfa]/30 hover:bg-[#a78bfa]/20 hover:border-[#a78bfa]/50"
            }`}
          >
            {injecting ? "injecting..." : `inject ${selected.size > 0 ? `(${selected.size})` : ""}`}
          </button>
        </div>
      </div>
    </div>
  )
}


function SedimentSection({
  conversationId,
  uploadedFiles,
  onDeleteFile,
  onReprocessFile,
  expandedFile,
  loadingSummary,
  loadedSummaries,
  onToggleSummary,
}: {
  conversationId?: string
  uploadedFiles: ConversationFile[]
  onDeleteFile?: (fileName: string) => void
  onReprocessFile?: (fileName: string) => void
  expandedFile: string | null
  loadingSummary: string | null
  loadedSummaries: Record<string, { summary: string | null; summary_model: string | null; image_metadata?: ImageMetadata | null; web_metadata?: WebMetadata | null; document_metadata?: DocumentMetadata | null }>
  onToggleSummary: (fileName: string) => void
}) {
  const [showInjectModal, setShowInjectModal] = useState(false)
  const [injections, setInjections] = useState<SedimentInjectionInfo[]>([])

  const loadInjections = () => {
    if (!conversationId) return
    getConversationInjections(conversationId)
      .then((res) => setInjections(res.injections))
      .catch(() => setInjections([]))
  }

  useEffect(() => {
    loadInjections()
  }, [conversationId])

  const handleRemoveInjection = async (injectionId: string) => {
    try {
      await removeSedimentInjection(injectionId)
      setInjections((prev) => prev.filter((i) => i.id !== injectionId))
    } catch (e) {
      console.error("Failed to remove injection:", e)
    }
  }

  const fileIcon = (type: string) => {
    if (type === "image") return "\uD83D\uDDBC"
    if (type === "pdf") return "\uD83D\uDCC4"
    if (type === "md") return "\uD83D\uDCDD"
    if (type === "epub" || type === "mobi") return "\uD83D\uDCD6"
    if (type === "web_probe") return "\uD83C\uDF10"
    return "\uD83D\uDCC4"
  }

  return (
    <div className="pl-3">
      {/* Inject button */}
      {conversationId && (
        <div className="mt-2 mb-1 flex items-center gap-2">
          <button
            onClick={() => setShowInjectModal(true)}
            className="text-[8px] font-mono text-[#a78bfa] border border-[#a78bfa]/30 bg-[#a78bfa]/5 hover:bg-[#a78bfa]/15 hover:border-[#a78bfa]/50 px-2 py-0.5 rounded transition-all duration-200"
          >
            ◈ inject
          </button>
          {injections.length > 0 && (
            <span className="text-[7px] text-[#666] font-mono">
              {injections.length} linked
            </span>
          )}
        </div>
      )}

      {/* Injected files */}
      {injections.length > 0 && (
        <div className="border-t border-[#1a1a1a] pt-1.5 mb-1.5">
          <div className="text-[7px] text-[#6c6c8a] font-mono uppercase tracking-wider mb-1">
            [ Injected Sediment ]
          </div>
          {injections.map((inj) => (
            <div key={inj.id} className="py-1.5 border-b border-[#1a1a1a] last:border-b-0">
              <div className="flex items-center gap-1.5 group">
                <span className="text-[8px] text-[#a78bfa]">◈</span>
                <span className="text-xs">{fileIcon(inj.file_type)}</span>
                <div className="flex-1 min-w-0">
                  <span className="text-[10px] text-[#aaa] font-mono truncate block">
                    {inj.source_file_name}
                  </span>
                  <span className="text-[7px] text-[#555] font-mono truncate block">
                    from "{inj.source_conversation_title || "untitled"}"
                  </span>
                </div>
                
                <span className="text-[8px] text-[#666] font-mono shrink-0">
                  {inj.token_count >= 1000 ? `${(inj.token_count / 1000).toFixed(1)}k` : inj.token_count} tok
                </span>

                <button
                  onClick={() => onToggleSummary(inj.source_file_name)}
                  className="text-[8px] text-[#4ade80] hover:underline"
                >
                  {expandedFile === inj.source_file_name ? "hide" : "sum"}
                </button>

                <button
                  onClick={() => handleRemoveInjection(inj.id)}
                  className="text-[9px] text-[#555] hover:text-[#ef4444] px-0.5 font-mono opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Remove injection"
                >
                  ×
                </button>
              </div>

              {expandedFile === inj.source_file_name && (
                <div className="mt-1 ml-4 bg-[#141414] border border-[#222] rounded overflow-hidden">
                  {loadingSummary === inj.source_file_name ? (
                    <div className="p-2 text-[9px] text-[#888] font-mono animate-pulse">Loading summary...</div>
                  ) : (
                    <div>
                      {loadedSummaries[inj.source_file_name]?.image_metadata ? (
                        <ImageMetadataCard metadata={loadedSummaries[inj.source_file_name].image_metadata!} />
                      ) : loadedSummaries[inj.source_file_name]?.web_metadata ? (
                        <WebMetadataCard metadata={loadedSummaries[inj.source_file_name].web_metadata!} summary={loadedSummaries[inj.source_file_name].summary} />
                      ) : loadedSummaries[inj.source_file_name]?.document_metadata ? (
                        <DocumentMetadataCard metadata={loadedSummaries[inj.source_file_name].document_metadata!} summary={loadedSummaries[inj.source_file_name].summary} />
                      ) : (
                        <div className="p-2 text-[9px] text-[#888] font-mono leading-relaxed markdown-body">
                          {loadedSummaries[inj.source_file_name]?.summary ? (
                            <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]}>
                              {loadedSummaries[inj.source_file_name].summary}
                            </ReactMarkdown>
                          ) : (
                            "No summary available."
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Native files */}
      {uploadedFiles.length > 0 && (
        <div className="border-t border-[#1a1a1a] pt-2">
          {uploadedFiles.map((f) => (
            <div key={f.file_name} className="py-1.5 border-b border-[#1a1a1a] last:border-b-0">
              <div className="flex items-center gap-1.5">
                <span className="text-xs">
                  {fileIcon(f.file_type)}
                </span>
                <span className="text-[10px] text-[#aaa] truncate flex-1 font-mono">
                  {f.file_name}
                </span>
                
                {f.status === "uploading" && (
                  <span className="text-[8px] text-[#eab308] animate-pulse px-1 border border-[#eab308]/30 rounded">
                    uploading
                  </span>
                )}
                {f.status === "processing" && (
                  <span className="text-[8px] text-[#3b82f6] animate-pulse px-1 border border-[#3b82f6]/30 rounded">
                    indexing
                  </span>
                )}
                {f.status === "error" && (
                  <div className="flex items-center gap-1.5">
                    <span className="text-[8px] text-[#ef4444] px-1 border border-[#ef4444]/30 rounded" title={f.summary || "Unknown error"}>
                      error
                    </span>
                    {onReprocessFile && (
                      <button
                        onClick={() => onReprocessFile(f.file_name)}
                        className="text-[8px] text-[#60a5fa] hover:text-[#93c5fd] hover:underline"
                        title="Retry indexing/summarization"
                      >
                        retry
                      </button>
                    )}
                  </div>
                )}
                
                {f.token_count > 0 && f.status === "ready" && (
                  <span className="text-[8px] text-[#666] font-mono">
                    {f.token_count >= 1000 ? `${(f.token_count / 1000).toFixed(1)}k` : f.token_count} tok
                  </span>
                )}

                {f.status === "ready" && (
                  <button
                    onClick={() => onToggleSummary(f.file_name)}
                    className="text-[8px] text-[#4ade80] hover:underline"
                  >
                    {expandedFile === f.file_name ? "hide" : "sum"}
                  </button>
                )}

                {onDeleteFile && (
                  <button
                    onClick={() => onDeleteFile(f.file_name)}
                    className="text-[9px] text-[#555] hover:text-[#ef4444] px-1 font-mono"
                    title="Delete file trace"
                  >
                    ×
                  </button>
                )}
              </div>
              
              {expandedFile === f.file_name && (
                <div className="mt-1 ml-4 bg-[#141414] border border-[#222] rounded overflow-hidden">
                  {loadingSummary === f.file_name ? (
                    <div className="p-2 text-[9px] text-[#888] font-mono animate-pulse">Loading summary...</div>
                  ) : (
                    <div>
                      {loadedSummaries[f.file_name]?.image_metadata ? (
                        <ImageMetadataCard metadata={loadedSummaries[f.file_name].image_metadata!} />
                      ) : loadedSummaries[f.file_name]?.web_metadata ? (
                        <WebMetadataCard metadata={loadedSummaries[f.file_name].web_metadata!} summary={loadedSummaries[f.file_name].summary} />
                      ) : loadedSummaries[f.file_name]?.document_metadata ? (
                        <DocumentMetadataCard metadata={loadedSummaries[f.file_name].document_metadata!} summary={loadedSummaries[f.file_name].summary} />
                      ) : (
                        <div className="p-2 text-[9px] text-[#888] font-mono leading-relaxed markdown-body">
                          {loadedSummaries[f.file_name]?.summary ? (
                            <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]}>
                              {loadedSummaries[f.file_name].summary}
                            </ReactMarkdown>
                          ) : (
                            "No summary available."
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {uploadedFiles.length === 0 && injections.length === 0 && (
        <div className="text-[9px] text-[#444] font-mono italic py-2 mt-1">
          No files or injections in this conversation.
        </div>
      )}

      {/* Injection Modal */}
      {showInjectModal && conversationId && (
        <SedimentInjectionModal
          conversationId={conversationId}
          onClose={() => setShowInjectModal(false)}
          onInjected={loadInjections}
        />
      )}
    </div>
  )
}


export function SidePanel({
  uploadedFiles = [],
  conversationId,
  onDeleteFile,
  onReprocessFile,
  messageCount = 0,
  notes = [],
  onDeleteNote,
  onUpdateNote,
}: {
  uploadedFiles?: ConversationFile[]
  conversationId?: string
  onDeleteFile?: (fileName: string) => void
  onReprocessFile?: (fileName: string) => void
  messageCount?: number
  notes?: NoteInfo[]
  onDeleteNote?: (noteId: string) => void
  onUpdateNote?: (noteId: string, comment?: string, visibility?: "personal" | "shared") => void
}) {
  const [collapsed, setCollapsed] = useState(true)
  const [data, setData] = useState<SkillsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pipelineOpen, setPipelineOpen] = useState(false)
  const [skillsOpen, setSkillsOpen] = useState(false)
  const [healthOpen, setHealthOpen] = useState(false)
  const [beliefsOpen, setBeliefsOpen] = useState(false)
  const [diffractiveOpen, setDiffractiveOpen] = useState(false)
  const [dreamingOpen, setDreamingOpen] = useState(false)
  const [schedulerOpen, setSchedulerOpen] = useState(false)
  const [tokensOpen, setTokensOpen] = useState(false)
  const [sedimentOpen, setSedimentOpen] = useState(false)
  const [notesOpen, setNotesOpen] = useState(false)
  const [expandedFile, setExpandedFile] = useState<string | null>(null)
  const [loadedSummaries, setLoadedSummaries] = useState<Record<string, { summary: string | null; summary_model: string | null; image_metadata?: ImageMetadata | null; web_metadata?: WebMetadata | null; document_metadata?: DocumentMetadata | null }>>({})
  const [loadingSummary, setLoadingSummary] = useState<string | null>(null)

  const handleToggleSummary = async (fileName: string) => {
    if (expandedFile === fileName) {
      setExpandedFile(null)
      return
    }

    setExpandedFile(fileName)
    if (!loadedSummaries[fileName] && conversationId) {
      setLoadingSummary(fileName)
      try {
        const res = await getFileSummary(conversationId, fileName)
        setLoadedSummaries((prev) => ({
          ...prev,
          [fileName]: {
            summary: res.summary,
            summary_model: res.summary_model,
            image_metadata: res.image_metadata,
            web_metadata: res.web_metadata,
            document_metadata: res.document_metadata
          }
        }))
      } catch (err) {
        console.error("Failed to load file summary:", err)
      } finally {
        setLoadingSummary(null)
      }
    }
  }

  useEffect(() => {
    if ((pipelineOpen || skillsOpen) && !data) {
      getSkills()
        .then(setData)
        .catch((e) => setError(e.message))
    }
  }, [pipelineOpen, skillsOpen, data])


  return (
    <div
      className={`
        border-[#222] bg-[#0c0c0c]
        md:border-l md:border-t-0 md:h-full
        border-t
        flex flex-col shrink-0
        overflow-hidden
        transition-all duration-200
        ${collapsed ? "md:w-9 w-full" : "md:w-120 w-full"}
      `}
    >
      {collapsed && (
        <button
          onClick={() => setCollapsed(false)}
          className="
            flex items-center gap-1.5 shrink-0
            text-xs text-[#555] hover:text-[#888]
            transition-colors
            md:flex-col md:justify-start md:gap-2 md:py-3 md:px-0
            md:h-full
            flex-row justify-start py-2 px-3
            select-none
          "
        >
          <span className="text-[10px]">{"\u25C0"}</span>
          <span className="md:[writing-mode:vertical-rl] md:text-[10px] md:tracking-wider text-[11px]">
            pipeline
          </span>
        </button>
      )}

      {!collapsed && (
        <>
          <div className="flex items-center shrink-0 px-3 py-2 border-b border-[#222]">
            <button
              onClick={() => setCollapsed(true)}
              className="flex items-center gap-1.5 text-[10px] text-[#555] hover:text-[#888] transition-colors"
            >
              <span>{"\u25B6"}</span>
              <span>close</span>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-3 pb-3">
            {error && (
              <p className="text-[10px] text-[#ef4444] my-2">
                Failed to load: {error}
              </p>
            )}

            {!data && !error && (
              <p className="text-[10px] text-[#555] animate-pulse mt-2">loading...</p>
            )}

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Vitality"
                open={healthOpen}
                onToggle={() => setHealthOpen(!healthOpen)}
              />
              {healthOpen && (
                <div className="pl-3">
                  <HealthSection messageCount={messageCount} />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Beliefs"
                open={beliefsOpen}
                onToggle={() => setBeliefsOpen(!beliefsOpen)}
              />
              {beliefsOpen && (
                <div className="pl-3">
                  <BeliefsSection conversationId={conversationId} messageCount={messageCount} />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Diffraction"
                open={diffractiveOpen}
                onToggle={() => setDiffractiveOpen(!diffractiveOpen)}
              />
              {diffractiveOpen && (
                <div className="pl-3">
                  <DiffractiveSection messageCount={messageCount} />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Dreaming"
                open={dreamingOpen}
                onToggle={() => setDreamingOpen(!dreamingOpen)}
              />
              {dreamingOpen && (
                <div className="pl-3">
                  <DreamingSection messageCount={messageCount} />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Startup"
                open={schedulerOpen}
                onToggle={() => setSchedulerOpen(!schedulerOpen)}
              />
              {schedulerOpen && (
                <div className="pl-3">
                  <SchedulerSection messageCount={messageCount} />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Tokens"
                open={tokensOpen}
                onToggle={() => setTokensOpen(!tokensOpen)}
              />
              {tokensOpen && (
                <div className="pl-3">
                  <TokensSection conversationId={conversationId} messageCount={messageCount} />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Notes"
                count={notes.length}
                open={notesOpen}
                onToggle={() => setNotesOpen(!notesOpen)}
              />
              {notesOpen && (
                <div className="pl-3">
                  <NotesSection
                    notes={notes}
                    onDeleteNote={onDeleteNote}
                    onUpdateNote={onUpdateNote}
                  />
                </div>
              )}
            </div>

            {/* Sediment section - always show */}
            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Sediment"
                count={uploadedFiles.length}
                open={sedimentOpen}
                onToggle={() => setSedimentOpen(!sedimentOpen)}
              />
              {sedimentOpen && (
                <SedimentSection
                  conversationId={conversationId}
                  uploadedFiles={uploadedFiles}
                  onDeleteFile={onDeleteFile}
                  onReprocessFile={onReprocessFile}
                  expandedFile={expandedFile}
                  loadingSummary={loadingSummary}
                  loadedSummaries={loadedSummaries}
                  onToggleSummary={handleToggleSummary}
                />
              )}
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Pipeline"
                count={data ? data.pipeline.length : undefined}
                open={pipelineOpen}
                onToggle={() => setPipelineOpen(!pipelineOpen)}
              />
              {pipelineOpen && (
                <div className="pl-3">
                  {!data && !error && (
                    <p className="text-[10px] text-[#555] animate-pulse py-1">loading pipeline...</p>
                  )}
                  {data && data.pipeline.map((s) => (
                    <SkillRow key={s.name} skill={s} />
                  ))}
                </div>
              )}

              <SectionHeader
                label="Skills"
                count={data ? data.on_demand.length : undefined}
                open={skillsOpen}
                onToggle={() => setSkillsOpen(!skillsOpen)}
              />
              {skillsOpen && (
                <div className="pl-3">
                  {!data && !error && (
                    <p className="text-[10px] text-[#555] animate-pulse py-1">loading skills...</p>
                  )}
                  {data && data.on_demand.length === 0 && (
                    <p className="text-[10px] text-[#444] py-1">no on-demand skills available</p>
                  )}
                  {data && data.on_demand.map((s) => (
                    <SkillRow key={s.name} skill={s} />
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
