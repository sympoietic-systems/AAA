import { useState } from "react"
import type { ImageMetadata, WebMetadata, DocumentMetadata } from "../../api/client"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import rehypeRaw from "rehype-raw"
import telemetrySchemas from "../../config/telemetry_schemas.json"

const { DIMENSIONS_16 } = telemetrySchemas

export function splitSummaryAndTension(summary: string | null): { cleanSummary: string | null; unresolvedTensions: string | null } {
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

export function ImageMetadataCard({ metadata }: { metadata: ImageMetadata }) {
  const [hoveredDim, setHoveredDim] = useState<{ index: number; label: string; desc: string; val: number } | null>(null)
  const [ocrOpen, setOcrOpen] = useState(false)

  const rawVec = metadata.structural_vector_16d || "[]"
  let vec: number[] = []
  try {
    vec = JSON.parse(rawVec)
  } catch { }

  const implicatedNodes: string[] = []
  try {
    if (metadata.belief_nodes_implicated) {
      const parsed = JSON.parse(metadata.belief_nodes_implicated)
      if (Array.isArray(parsed)) {
        implicatedNodes.push(...parsed)
      }
    }
  } catch { }

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

export function WebMetadataCard({ metadata, summary }: { metadata: WebMetadata; summary: string | null }) {
  const implicatedNodes: string[] = []
  try {
    if (metadata.belief_nodes_implicated) {
      const parsed = JSON.parse(metadata.belief_nodes_implicated)
      if (Array.isArray(parsed)) {
        implicatedNodes.push(...parsed)
      }
    }
  } catch { }

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

export function DocumentMetadataCard({ metadata, summary }: { metadata: DocumentMetadata; summary: string | null }) {
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
