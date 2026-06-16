import { useRef, useState, useCallback } from "react"
import type { BeliefTimeseriesPoint } from "../../api/client"

interface Props {
  points: BeliefTimeseriesPoint[]
  spanDays: number
  bucketSize: string
  beliefLabel: string
}

const W = 560
const H = 200
const PAD_LEFT = 44
const PAD_RIGHT = 12
const PAD_TOP = 16
const PAD_BOT = 24
const PLOT_W = W - PAD_LEFT - PAD_RIGHT
const PLOT_H = H - PAD_TOP - PAD_BOT

function fmtNum(n: number): string {
  if (n < 0.01) return n.toFixed(3)
  if (n < 1) return n.toFixed(2)
  return n.toFixed(1)
}

export function BeliefTimelineChart({ points, spanDays, bucketSize, beliefLabel }: Props) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [tooltip, setTooltip] = useState<{ x: number; y: number; ts: string; mass: number | null; conf: number | null } | null>(null)

  const hasMass = points.some((p) => p.mass !== null)
  const hasConf = points.some((p) => p.confidence !== null)

  const massMax = hasMass ? 3.0 : 1
  const confMax = 1.0

  // Map value to Y (0=bottom, massMax/confMax=top)
  const yForMass = (v: number) => PAD_TOP + PLOT_H * (1 - v / massMax)
  const yForConf = (v: number) => PAD_TOP + PLOT_H * (1 - v / confMax)

  // Build polyline strings
  const massPoints: string[] = []
  const confPoints: string[] = []

  if (points.length > 1 && hasMass) {
    points.forEach((p, i) => {
      const x = PAD_LEFT + (i / (points.length - 1)) * PLOT_W
      if (p.mass !== null) {
        massPoints.push(`${x.toFixed(1)},${yForMass(p.mass).toFixed(1)}`)
      }
      if (p.confidence !== null) {
        confPoints.push(`${x.toFixed(1)},${yForConf(p.confidence).toFixed(1)}`)
      }
    })
  }

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (points.length < 2) return
      const rect = e.currentTarget.getBoundingClientRect()
      const mx = e.clientX - rect.left
      if (mx < PAD_LEFT || mx > PAD_LEFT + PLOT_W) { setTooltip(null); return }
      const frac = (mx - PAD_LEFT) / PLOT_W
      const idx = Math.round(frac * (points.length - 1))
      const p = points[idx]
      const cx = PAD_LEFT + (idx / (points.length - 1)) * PLOT_W
      setTooltip({ x: cx, y: PAD_TOP, ts: p.timestamp, mass: p.mass, conf: p.confidence })
    },
    [points],
  )

  const handleMouseLeave = () => setTooltip(null)

  // Y-axis ticks
  const massTicks = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
  const confTicks = [0, 0.25, 0.5, 0.75, 1.0]

  // X-axis labels (max ~6)
  const xLabels: { x: number; label: string }[] = []
  if (points.length >= 2) {
    const step = Math.max(1, Math.floor(points.length / 5))
    for (let i = 0; i < points.length; i += step) {
      const p = points[i]
      const x = PAD_LEFT + (i / (points.length - 1)) * PLOT_W
      const d = new Date(p.timestamp)
      const label =
        bucketSize === "day" || spanDays > 7
          ? `${d.getMonth() + 1}/${d.getDate()}`
          : `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`
      xLabels.push({ x, label })
    }
  }

  if (points.length === 0) {
    return (
      <div className="text-[#555] italic font-mono text-[10px] mt-2">
        No timeseries data available for this belief.
      </div>
    )
  }

  return (
    <div className="font-mono text-[10px] mt-2">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-[1.5px] bg-[#60a5fa]" />
            <span className="text-[#93c5fd]">mass</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-[1.5px] bg-[#4ade80]" />
            <span className="text-[#4ade80]">confidence</span>
          </span>
        </div>
        <span className="text-[#555]">
          {spanDays > 7 ? `${spanDays.toFixed(0)}d · daily` : `${spanDays.toFixed(1)}d · ${bucketSize}ly`}
        </span>
      </div>

      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        height={H}
        className="bg-[#0a0a0a] border border-[#222] select-none"
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        style={{ maxWidth: W }}
      >
        {/* Grid lines */}
        <g stroke="#1a1a2e" strokeWidth="0.5">
          {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
            const y = PAD_TOP + PLOT_H * (1 - frac)
            return <line key={frac} x1={PAD_LEFT} y1={y} x2={PAD_LEFT + PLOT_W} y2={y} />
          })}
        </g>

        {/* Y-axis labels (mass, left) */}
        <g fill="#93c5fd" fontSize="8" textAnchor="end">
          {massTicks.map((v) => (
            <text key={`m${v}`} x={PAD_LEFT - 4} y={yForMass(v) + 3}>{v.toFixed(1)}</text>
          ))}
        </g>
        <text fill="#93c5fd" fontSize="7" textAnchor="middle" transform={`translate(10,${PAD_TOP + PLOT_H / 2}) rotate(-90)`}>
          mass
        </text>

        {/* Y-axis labels (confidence, right) */}
        <g fill="#4ade80" fontSize="8" textAnchor="start">
          {confTicks.map((v) => (
            <text key={`c${v}`} x={PAD_LEFT + PLOT_W + 4} y={yForConf(v) + 3}>{v.toFixed(2)}</text>
          ))}
        </g>
        <text fill="#4ade80" fontSize="7" textAnchor="middle" transform={`translate(${W - 10},${PAD_TOP + PLOT_H / 2}) rotate(90)`}>
          conf
        </text>

        {/* X-axis labels */}
        <g fill="#555" fontSize="7" textAnchor="middle">
          {xLabels.map(({ x, label }) => (
            <text key={label} x={x} y={H - 6}>{label}</text>
          ))}
        </g>

        {/* Mass line */}
        {hasMass && massPoints.length > 1 && (
          <polyline
            points={massPoints.join(" ")}
            fill="none"
            stroke="#60a5fa"
            strokeWidth="1.2"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        )}

        {/* Confidence line */}
        {hasConf && confPoints.length > 1 && (
          <polyline
            points={confPoints.join(" ")}
            fill="none"
            stroke="#4ade80"
            strokeWidth="1.2"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        )}

        {/* Hover cursor */}
        {tooltip && (
          <>
            <line x1={tooltip.x} y1={PAD_TOP} x2={tooltip.x} y2={PAD_TOP + PLOT_H} stroke="#fff" strokeWidth="0.5" strokeDasharray="2,2" opacity={0.5} />
            {tooltip.mass !== null && (
              <circle cx={tooltip.x} cy={yForMass(tooltip.mass)} r="2.5" fill="#60a5fa" stroke="#0a0a0a" strokeWidth="0.8" />
            )}
            {tooltip.conf !== null && (
              <circle cx={tooltip.x} cy={yForConf(tooltip.conf)} r="2.5" fill="#4ade80" stroke="#0a0a0a" strokeWidth="0.8" />
            )}
            <rect x={tooltip.x - 30} y={tooltip.y + 2} width="60" height="24" rx="2" fill="#1a1a2e" stroke="#444" strokeWidth="0.5" opacity={0.92} />
            <text x={tooltip.x} y={tooltip.y + 12} fill="#ccc" fontSize="7" textAnchor="middle">
              {tooltip.mass !== null ? `m:${fmtNum(tooltip.mass)}` : ""}
              {tooltip.mass !== null && tooltip.conf !== null ? " " : ""}
              {tooltip.conf !== null ? `c:${fmtNum(tooltip.conf)}` : ""}
            </text>
          </>
        )}
      </svg>
    </div>
  )
}
