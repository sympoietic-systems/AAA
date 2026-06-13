import telemetrySchemas from "../config/telemetry_schemas.json"
import { Tooltip } from "./Tooltip"

const { DIMENSIONS_16 } = telemetrySchemas

const SHORT_CODES = [
  "HO", "AM", "CY", "BI", "DE", "RH", "BP", "RD",
  "VF", "NC", "TL", "AD", "SY", "NO", "CO", "SM"
]

interface VectorVisualizerProps {
  vector: number[]
  titleColorClass?: string
  barColorClass?: string
  variant?: "signature" | "impact"
  onHoverDim?: (dim: { index: number; label: string; desc: string; val: number } | null) => void
}

export function VectorVisualizer({
  vector,
  titleColorClass = "text-[#a78bfa]",
  barColorClass = "bg-[#a78bfa]",
  variant = "signature",
  onHoverDim
}: VectorVisualizerProps) {
  if (!vector || vector.length === 0) return null

  const isImpact = variant === "impact"

  return (
    <div className="flex items-end gap-1 bg-[#08080c] border border-[#1a1a24] p-1.5 rounded w-fit overflow-visible relative">
      {isImpact && (
        <div className="absolute left-0 right-0 top-[22px] h-[1px] bg-[#333]/50 pointer-events-none z-10" />
      )}
      {vector.map((val, idx) => {
        let hp = 0
        let displayColor = barColorClass

        if (isImpact) {
          hp = Math.min(100, Math.max(5, Math.round((val + 0.5) * 100)))
          displayColor = val >= 0 ? "bg-[#10b981]" : "bg-[#ef4444]"
        } else {
          hp = Math.min(100, Math.max(8, Math.round(((val + 1) / 2) * 100)))
        }

        const dimInfo = DIMENSIONS_16[idx] || { label: `Dimension ${idx + 1}`, desc: "" }
        const code = SHORT_CODES[idx] || `D${idx + 1}`

        return (
          <Tooltip
            key={idx}
            title={dimInfo.label}
            subtitle={val.toFixed(4)}
            description={dimInfo.desc}
            titleColorClass={isImpact ? (val >= 0 ? "text-[#10b981]" : "text-[#ef4444]") : titleColorClass}
            position="top-center"
            className="flex flex-col items-center shrink-0"
          >
            {/* The Bar wrapper */}
            <div 
              onMouseEnter={() => onHoverDim?.({ index: idx, label: dimInfo.label, desc: dimInfo.desc, val })}
              onMouseLeave={() => onHoverDim?.(null)}
              className="h-10 w-2.5 bg-[#14141d]/50 border border-[#222]/30 rounded-sm relative overflow-hidden flex items-end"
            >
              <div
                style={{ height: `${hp}%` }}
                className={`w-full opacity-60 hover:opacity-100 transition-all transition-colors duration-200 cursor-crosshair ${displayColor}`}
              />
            </div>
            {/* Short code label */}
            <span className="text-[7px] text-[#555] font-mono select-none mt-1 tracking-tighter leading-none">
              {code}
            </span>
          </Tooltip>
        )
      })}
    </div>
  )
}
