import telemetrySchemas from "../config/telemetry_schemas.json"
import { Tooltip } from "./Tooltip"

const { SIGNATURE_DIMENSIONS_16, IMPACT_DIMENSIONS_16 } = telemetrySchemas

const SHORT_CODES = [
  "HO", "AM", "CY", "BI", "DE", "RH", "BP", "RD",
  "VF", "NC", "TL", "AD", "SY", "NO", "CO", "SM"
]

const IMPACT_SHORT_CODES = [
  "VE", "ID", "RC", "AT", "AB", "RhC", "BP", "DT",
  "VF", "DC", "LT", "OM", "SA", "ND", "EP", "HD"
]

interface VectorVisualizerProps {
  vector: number[]
  titleColorClass?: string
  barColorClass?: string
  variant?: "signature" | "impact"
  allowNegative?: boolean
  onHoverDim?: (dim: { index: number; label: string; desc: string; val: number } | null) => void
}

export function VectorVisualizer({
  vector,
  titleColorClass = "text-[#a78bfa]",
  barColorClass = "bg-[#a78bfa]",
  variant = "signature",
  allowNegative,
  onHoverDim
}: VectorVisualizerProps) {
  if (!vector || vector.length === 0) return null

  const isImpact = variant === "impact"
  const shouldAllowNegative = allowNegative !== undefined ? allowNegative : isImpact

  return (
    <div className="flex items-end gap-0.5 bg-[#08080c] border border-[#1a1a24] p-0.5 w-fit overflow-visible relative rounded-none">
      {/* Centerline baseline: only render if negative values are allowed */}
      {shouldAllowNegative && (
        <div className="absolute left-0 right-0 top-[14px] h-[1px] bg-[#333]/30 pointer-events-none z-10" />
      )}

      {vector.map((val, idx) => {
        const isPositive = val >= 0
        let displayColor = barColorClass
        let magnitude = 0

        if (isImpact) {
          // Impact vector values range roughly in [-0.5, 0.5]
          magnitude = Math.min(1.0, Math.abs(val) / 0.5)
          displayColor = isPositive ? "bg-[#10b981]" : "bg-[#ef4444]"
        } else {
          // Signature vector values range in [0.0, 1.0]
          magnitude = Math.min(1.0, Math.abs(val))
        }

        // Height scale max: 50% for centerline-based, 100% for bottom-based
        const scaleMax = shouldAllowNegative ? 50 : 100
        const heightPercent = Math.max(4, Math.round(magnitude * scaleMax))
        
        const dimensions = isImpact ? IMPACT_DIMENSIONS_16 : SIGNATURE_DIMENSIONS_16
        const shortCodes = isImpact ? IMPACT_SHORT_CODES : SHORT_CODES
        
        const dimInfo = dimensions[idx] || { label: `Dimension ${idx + 1}`, desc: "" }
        const code = shortCodes[idx] || `D${idx + 1}`

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
            {/* The Bar container (h-6 = 24px) */}
            <div 
              onMouseEnter={() => onHoverDim?.({ index: idx, label: dimInfo.label, desc: dimInfo.desc, val })}
              onMouseLeave={() => onHoverDim?.(null)}
              className="h-6 w-1.5 relative select-none cursor-crosshair bg-[#14141d]/30"
            >
              {/* Actual bar absolute-anchored */}
              <div
                style={shouldAllowNegative ? {
                  height: `${heightPercent}%`,
                  bottom: isPositive ? "50%" : "auto",
                  top: isPositive ? "auto" : "50%",
                } : {
                  height: `${heightPercent}%`,
                  bottom: 0,
                  top: "auto",
                }}
                className={`absolute left-0 right-0 opacity-60 hover:opacity-100 transition-all transition-colors duration-150 ${displayColor}`}
              />
            </div>
            {/* Short code label */}
            <span className="text-[4.5px] text-[#445] font-mono select-none mt-0.5 tracking-tighter leading-none scale-90">
              {code}
            </span>
          </Tooltip>
        )
      })}
    </div>
  )
}
