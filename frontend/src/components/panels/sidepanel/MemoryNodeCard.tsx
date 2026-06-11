import type { MemoryNodeInfo } from "../../../api/client"

const NODE_TYPE_LABELS: Record<string, string> = {
  scar: "SCAR",
  concept: "CONCEPT",
  tension: "TENSION",
  pattern: "PATTERN",
  bifurcation: "BIFURCATION",
}

const NODE_TYPE_COLORS: Record<string, string> = {
  scar: "bg-[#7f1d1d]/20 text-[#f87171] border-[#7f1d1d]/40",
  concept: "bg-[#1e3a5f]/20 text-[#6fafe2] border-[#1e3a5f]/40",
  tension: "bg-[#713f12]/20 text-[#fbbf24] border-[#713f12]/40",
  pattern: "bg-[#3b1f6e]/20 text-[#a892ee] border-[#3b1f6e]/40",
  bifurcation: "bg-[#1f4a3b]/20 text-[#4ade80] border-[#1f4a3b]/40",
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

export function MemoryNodeCard({ node }: Props) {
  const typeLabel = NODE_TYPE_LABELS[node.node_type] || node.node_type.toUpperCase()
  const typeColor = NODE_TYPE_COLORS[node.node_type] || "bg-[#141414] text-[#888] border-[#222]"

  return (
    <div className="border border-[#1a1a1a] bg-[#0c0c0c] rounded-[3px] p-3 font-mono">
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <span className={`text-[8px] px-1.5 py-[1px] rounded-[2px] border font-mono uppercase tracking-wider ${typeColor}`}>
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
}
