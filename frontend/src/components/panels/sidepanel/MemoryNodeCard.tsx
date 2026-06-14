import { memo } from "react"
import type { MemoryNodeInfo } from "../../../api/client"

const NODE_TYPE_LABELS: Record<string, string> = {
  scar: "SCAR",
  concept: "CONCEPT",
  tension: "TENSION",
  pattern: "PATTERN",
  bifurcation: "BIFURCATION",
}

const NODE_TYPE_COLORS: Record<string, { text: string; bg: string }> = {
  scar: { text: "#f87171", bg: "bg-[#7f1d1d]/20" },
  concept: { text: "#6fafe2", bg: "bg-[#1e3a5f]/20" },
  tension: { text: "#fbbf24", bg: "bg-[#713f12]/20" },
  pattern: { text: "#a892ee", bg: "bg-[#3b1f6e]/20" },
  bifurcation: { text: "#4ade80", bg: "bg-[#1f4a3b]/20" },
}

function IntensityBar({ value }: { value: number }) {
  const pct = Math.min(100, Math.max(0, Math.round(value * 100)))
  const color =
    value >= 0.8
      ? "bg-[#f87171]"
      : value >= 0.5
        ? "bg-[#fbbf24]"
        : "bg-[#4ade80]"

  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1 w-16 bg-[#1a1a1a] rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-300`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[9px] text-[#555] font-mono">{pct}%</span>
    </div>
  )
}

interface Props {
  node: MemoryNodeInfo
}

export const MemoryNodeCard = memo(function MemoryNodeCard({ node }: Props) {
  const typeLabel = NODE_TYPE_LABELS[node.node_type] || node.node_type.toUpperCase()
  const typeColor = NODE_TYPE_COLORS[node.node_type] || { text: "#888" }

  return (
    <div className="font-mono">
      {/* Header */}
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-[8px] font-mono uppercase tracking-wider" style={{ color: typeColor.text }}>
          {typeLabel}
        </span>
        {node.diffractive_key && (
          <span className="text-[9px] text-[#4ec9b0]/85 italic">{node.diffractive_key}</span>
        )}
        <span className="ml-auto text-[8px] text-[#444]">{node.id}</span>
      </div>

      {/* Intensity + glitch potential */}
      <div className="flex items-center gap-4 mb-2">
        <IntensityBar value={node.intensity} />
        {node.glitch_potential > 0 && (
          <span className="text-[8px] text-[#555]">
            glitch: {(node.glitch_potential * 100).toFixed(0)}%
          </span>
        )}
        <span className="text-[8px] text-[#555] ml-auto">
          {node.agential_symmetry}
        </span>
      </div>

      {/* Intra-active text */}
      <div className="text-[10px] text-[#ccc] leading-relaxed mb-2">
        {node.intra_active_text}
      </div>

      {/* Surface fragment */}
      {node.surface_fragment && (
        <div className="border-l-2 border-[#333] pl-2 mb-2 text-[9px] text-[#777] italic">
          &ldquo;{node.surface_fragment}&rdquo;
        </div>
      )}

      {/* Scar */}
      {node.scar && (
        <div className="text-[8px] text-[#f87171]/60">
          scar: {node.scar}
        </div>
      )}

      {/* Tendrils */}
      {node.tendril_ids && node.tendril_ids.length > 0 && (
        <div className="mt-1.5 flex items-center gap-1 text-[8px] text-[#555]">
          <span>tendrils:</span>
          {node.tendril_ids.map((tid) => (
            <span key={tid} className="text-[#6fafe2]/50">{tid}</span>
          ))}
        </div>
      )}
    </div>
  )
})
