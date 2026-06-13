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
    <div className="flex items-end gap-0.5 bg-[#08080c] border border-[#1a1a24] p-0.5 w-fit overflow-visible relative rounded-none">
      {isImpact && (
        <div className="absolute left-0 right-0 top-[14px] h-[1px] bg-[#333]/40 pointer-events-none z-10" />
      )}
      {vector.map((val, idx) => {
        let hp = 0
        let displayColor = barColorClass

        if (isImpact) {
          hp = Math.min(100, Math.max(5, Math.round((val + 0.5) * 100)))
          displayColor = val >= 0 ? "bg-[#10b981]" : "bg-[#ef4444]"
        } else {
          hp = Math.min(100, Math.max(10, Math.round(((val + 1) / 2) * 100)))
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
              className="h-6 w-1.5 relative flex items-end select-none cursor-crosshair"
            >
              <div
                style={{ height: `${hp}%` }}
                className={`w-full opacity-60 hover:opacity-100 transition-all transition-colors duration-150 ${displayColor}`}
              />
            </div>
            {/* Short code label */}
            <span className="text-[5.5px] text-[#445] font-mono select-none mt-0.5 tracking-tighter leading-none scale-90">
              {code}
            </span>
          </Tooltip>
        )
      })}
    </div>
  )
}
