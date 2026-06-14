import { useState, memo } from "react"

const EMPTY_NUMBER_ARRAY: number[] = []
import type { ImageMetadata, WebMetadata, DocumentMetadata } from "../../../api/client"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import rehypeRaw from "rehype-raw"
import { VectorVisualizer } from "../../UI/VectorVisualizer"

export function splitSummaryAndTension(summary: string | null): { cleanSummary: string | null; unresolvedTensions: string | null } {
  if (!summary) return { cleanSummary: null, unresolvedTensions: null }
  const tensionMarkers = [
    /##\s*Unresolved\s*Tensions/i, /###\s*Unresolved\s*Tensions/i,
    /#\s*Unresolved\s*Tensions/i, /\*\*Unresolved\s*Tensions:?\*\*/i,
    /Unresolved\s*Tensions:?/i,
  ]
  let bestIndex = -1; let markerLength = 0
  for (const marker of tensionMarkers) {
    const match = summary.match(marker)
    if (match && match.index !== undefined) {
      if (bestIndex === -1 || match.index < bestIndex) { bestIndex = match.index; markerLength = match[0].length }
    }
  }
  if (bestIndex !== -1) {
    const clean = summary.substring(0, bestIndex).trim()
    const tensions = summary.substring(bestIndex + markerLength).trim()
    return { cleanSummary: clean || null, unresolvedTensions: tensions || null }
  }
  return { cleanSummary: summary, unresolvedTensions: null }
}

/* ── Image Metadata ── */
export const ImageMetadataCard = memo(function ImageMetadataCard({ metadata }: { metadata: ImageMetadata }) {
  const [ocrOpen, setOcrOpen] = useState(false)
  const rawVec = metadata.structural_vector_16d || "[]"
  let vec: number[] = []
  try { vec = JSON.parse(rawVec) } catch { }
  const implicatedNodes: string[] = []
  try {
    if (metadata.belief_nodes_implicated) {
      const parsed = JSON.parse(metadata.belief_nodes_implicated)
      if (Array.isArray(parsed)) implicatedNodes.push(...parsed)
    }
  } catch { }

  return (
    <div className="font-mono text-[10px] space-y-2">
      <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">[ Somatic Ingestion ]</div>

      <div className="flex flex-wrap gap-x-4 gap-y-0.5">
        <span><span className="text-[#666]">G_f:</span> <span className="text-[#e63946] font-bold">{metadata.g_f_score.toFixed(3)}</span></span>
        <span><span className="text-[#666]">A_d:</span> <span className="text-[#f77f00] font-bold">{metadata.a_d_score.toFixed(3)}</span></span>
      </div>

      {metadata.somatic_notes && (
        <div>
          <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">[ Somatic Traces ]</div>
          <p className="font-serif italic text-[#c0caf5] text-[11px] leading-relaxed pl-1.5 border-l border-[#333]">{metadata.somatic_notes}</p>
        </div>
      )}

      {metadata.diffractive_analysis && (
        <div>
          <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">[ Diffractive Interference ]</div>
          <p className="text-[#e0e0f0] text-[11px] leading-relaxed font-sans pl-1.5 border-l border-[#333]">{metadata.diffractive_analysis}</p>
        </div>
      )}

      {implicatedNodes.length > 0 && (
        <div>
          <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">. . . Collides With . . .</div>
          <div className="flex flex-wrap gap-1 mt-0.5">
            {implicatedNodes.map((node) => <span key={node} className="text-[8px] text-[#a78bfa]">{node}</span>)}
          </div>
        </div>
      )}

      {metadata.raw_transcription && (
        <div>
          <button onClick={() => setOcrOpen(!ocrOpen)} className="text-[9px] text-[#6c6c8a] hover:text-[#999] font-mono cursor-pointer select-none">
            [{ocrOpen ? "−" : "+"} OCR Transcription]
          </button>
          {ocrOpen && (
            <div className="text-[10px] text-[#999] font-mono mt-1 max-h-32 overflow-y-auto whitespace-pre-wrap leading-relaxed">
              {metadata.raw_transcription}
            </div>
          )}
        </div>
      )}

      {vec.length > 0 && (
        <div>
          <div className="text-[#555] font-mono text-[10px] uppercase">[ 16D Autopoietic Signature ]</div>
          <VectorVisualizer vector={vec} variant="signature" titleColorClass="text-[#4ade80]" barColorClass="bg-[#4ade80]" />
        </div>
      )}
    </div>
  )
})

/* ── Web Metadata ── */
export const WebMetadataCard = memo(function WebMetadataCard({ metadata, summary }: { metadata: WebMetadata; summary: string | null }) {
  const implicatedNodes: string[] = []
  try {
    if (metadata.belief_nodes_implicated) {
      const parsed = JSON.parse(metadata.belief_nodes_implicated)
      if (Array.isArray(parsed)) implicatedNodes.push(...parsed)
    }
  } catch { }
  const { cleanSummary, unresolvedTensions } = splitSummaryAndTension(summary)

  return (
    <div className="font-mono text-[10px] space-y-2">
      <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">[ Exogenous Telemetry — Web ]</div>

      <div className="flex flex-wrap gap-x-4 gap-y-0.5">
        <span><span className="text-[#666]">Interference:</span> <span className="text-[#facc15] font-bold">{metadata.interference_score.toFixed(4)}</span></span>
      </div>

      <div>
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">[ Query ]</div>
        <span className="text-[#eee] font-mono font-bold">"{metadata.query_used}"</span>
      </div>

      <div>
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">[ Source ]</div>
        <a href={metadata.source_url} target="_blank" rel="noopener noreferrer" className="text-[#60a5fa] hover:underline break-all text-[10px]">
          {metadata.source_url}
        </a>
      </div>

      {cleanSummary && (
        <div>
          <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">[ Insight / Summary ]</div>
          <div className="text-[#e0e0f0] text-[11px] leading-relaxed font-sans markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]}>{cleanSummary}</ReactMarkdown>
          </div>
        </div>
      )}

      {unresolvedTensions && (
        <div>
          <div className="text-[#f87171] font-mono text-[9px] uppercase tracking-wider">⚡ Unresolved Tensions</div>
          <div className="text-[#e0d0d0] text-[11px] leading-relaxed font-sans markdown-body pl-1.5 border-l border-[#f87171]/40">
            <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]}>{unresolvedTensions}</ReactMarkdown>
          </div>
        </div>
      )}

      {implicatedNodes.length > 0 && (
        <div>
          <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">. . . Collides With . . .</div>
          <div className="flex flex-wrap gap-1 mt-0.5">
            {implicatedNodes.map((node) => <span key={node} className="text-[8px] text-[#c084fc]">{node}</span>)}
          </div>
        </div>
      )}
    </div>
  )
})

/* ── Document Metadata ── */
export const DocumentMetadataCard = memo(function DocumentMetadataCard({ metadata, summary }: { metadata: DocumentMetadata; summary: string | null }) {
  const vec = metadata.state_vector_impact ?? EMPTY_NUMBER_ARRAY
  const implicatedNodes = metadata.belief_nodes_implicated ?? EMPTY_NUMBER_ARRAY
  const { cleanSummary, unresolvedTensions } = splitSummaryAndTension(summary)

  return (
    <div className="font-mono text-[10px] space-y-2">
      <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">[ Sediment Telemetry — Document ]</div>

      <div className="flex flex-wrap gap-x-4 gap-y-0.5">
        <span><span className="text-[#666]">Interference:</span> <span className="text-[#facc15] font-bold">{metadata.interference_score.toFixed(4)}</span></span>
      </div>

      {cleanSummary && (
        <div>
          <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">[ Insight / Summary ]</div>
          <div className="text-[#e0e0f0] text-[11px] leading-relaxed font-sans markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]}>{cleanSummary}</ReactMarkdown>
          </div>
        </div>
      )}

      {unresolvedTensions && (
        <div>
          <div className="text-[#f87171] font-mono text-[9px] uppercase tracking-wider">⚡ Unresolved Tensions</div>
          <div className="text-[#e0d0d0] text-[11px] leading-relaxed font-sans markdown-body pl-1.5 border-l border-[#f87171]/40">
            <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]}>{unresolvedTensions}</ReactMarkdown>
          </div>
        </div>
      )}

      {implicatedNodes.length > 0 && (
        <div>
          <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">. . . Collides With . . .</div>
          <div className="flex flex-wrap gap-1 mt-0.5">
            {implicatedNodes.map((node) => <span key={node} className="text-[8px] text-[#10b981]">{node}</span>)}
          </div>
        </div>
      )}

      {vec.length > 0 && (
        <div>
          <div className="text-[#555] font-mono text-[10px] uppercase">[ 16D State Impact Vector ]</div>
          <VectorVisualizer vector={vec} variant="impact" />
        </div>
      )}
    </div>
  )
})
