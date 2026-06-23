import { memo } from "react"
import type { MemoryNodeInfo } from "../../api/client"

const NODE_TYPE_LABELS: Record<string, string> = {
  scar: "SCAR",
  concept: "CONCEPT",
  tension: "TENSION",
  pattern: "PATTERN",
  bifurcation: "BIFURCATION",
}

const NODE_TYPE_COLORS: Record<string, { text: string; bg: string }> = {
  scar: { text: "var(--color-semantic-red)", bg: "bg-semantic-red/10" },          // semantic-red
  concept: { text: "var(--color-semantic-blue)", bg: "bg-semantic-blue/10" },      // semantic-blue
  tension: { text: "var(--color-semantic-gold)", bg: "bg-semantic-gold/10" },      // semantic-gold
  pattern: { text: "var(--color-semantic-purple)", bg: "bg-semantic-purple/10" },    // semantic-purple
  bifurcation: { text: "var(--color-semantic-green)", bg: "bg-semantic-green/10" },  // semantic-green
}

function IntensityBar({ value }: { value: number }) {
  const pct = Math.min(100, Math.max(0, Math.round(value * 100)))
  const color =
    value >= 0.8
      ? "bg-semantic-red"
      : value >= 0.5
        ? "bg-semantic-gold"
        : "bg-semantic-green"

  return (
    <div className="flex items-center gap-1.5 font-mono">
      <div className="h-1 w-16 bg-ui-border rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-300`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[9px] text-ui-dim font-mono">{pct}%</span>
    </div>
  )
}

interface Props {
  node: MemoryNodeInfo
}

export const MemoryNodeCard = memo(function MemoryNodeCard({ node }: Props) {
  const typeLabel = NODE_TYPE_LABELS[node.node_type] || node.node_type.toUpperCase()
  const typeColor = NODE_TYPE_COLORS[node.node_type] || { text: "var(--color-ui-dim)" }

  return (
    <div className="font-mono min-w-0">
      {/* Header */}
      <div className="flex items-center gap-2 mb-1.5 min-w-0">
        <span className="text-[8px] font-mono uppercase tracking-wider shrink-0" style={{ color: typeColor.text }}>
          {typeLabel}
        </span>
        {node.diffractive_key && (
          <span className="text-[9px] text-semantic-green italic truncate">{node.diffractive_key}</span>
        )}
        <span className="ml-auto text-[8px] text-ui-dim shrink-0">{node.id}</span>
      </div>

      {/* Intensity + glitch potential */}
      <div className="flex items-center gap-4 mb-2 flex-wrap">
        <IntensityBar value={node.intensity} />
        {node.glitch_potential > 0 && (
          <span className="text-[8px] text-ui-dim shrink-0">
            glitch: {(node.glitch_potential * 100).toFixed(0)}%
          </span>
        )}
        <span className="text-[8px] text-ui-dim ml-auto shrink-0 font-mono">
          {node.agential_symmetry}
        </span>
      </div>

      {/* Intra-active text */}
      <div className="text-[10px] text-ui-primary leading-relaxed mb-2 break-words font-sans">
        {node.intra_active_text}
      </div>

      {/* Surface fragment */}
      {node.surface_fragment && (
        <div className="border-l-2 border-ui-border pl-2 mb-2 text-[9px] text-ui-dim italic font-sans">
          &ldquo;{node.surface_fragment}&rdquo;
        </div>
      )}

      {/* Scar */}
      {node.scar && (
        <div className="text-[8px] text-semantic-red/60 font-mono">
          scar: {node.scar}
        </div>
      )}

      {/* Tendrils */}
      {node.tendril_ids && node.tendril_ids.length > 0 && (
        <div className="mt-1.5 flex items-center gap-1 text-[8px] text-ui-dim">
          <span>tendrils:</span>
          {node.tendril_ids.map((tid) => (
            <span key={tid} className="text-action-dim/60 font-mono">{tid}</span>
          ))}
        </div>
      )}
    </div>
  )
})
