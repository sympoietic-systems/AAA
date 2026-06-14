import { memo } from "react"

const DOT_MAP: Record<string, string> = {
  circle:   "●",
  diamond:  "◆",
  triangle: "▲",
  cross:    "✖",
  open:     "◇",
}

interface DotIconProps {
  type?: keyof typeof DOT_MAP
  color: string
  className?: string
}

function DotIconComponent({ type = "circle", color, className = "" }: DotIconProps) {
  return (
    <span
      className={`text-[10px] shrink-0 leading-none select-none ${className}`}
      style={{ color }}
    >
      {DOT_MAP[type]}
    </span>
  )
}

export const DotIcon = memo(DotIconComponent)
