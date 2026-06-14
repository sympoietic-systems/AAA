import { memo } from "react"

type Intent = "save" | "delete" | "edit" | "neutral" | "cyan" | "purple"

const INTENT_HOVER: Record<Intent, string> = {
  save:    "#4ade80",
  delete:  "#ef4444",
  edit:    "#a78bfa",
  neutral: "#888",
  cyan:    "#00e5ff",
  purple:  "#a78bfa",
}

interface TerminalButtonProps {
  children: React.ReactNode
  intent?: Intent
  onClick?: () => void
  disabled?: boolean
  className?: string
}

function TerminalButtonComponent({
  children, intent = "neutral", onClick, disabled, className = ""
}: TerminalButtonProps) {
  const hoverColor = INTENT_HOVER[intent]

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`text-[10px] text-[#666] font-mono cursor-pointer select-none transition-colors disabled:text-[#333] disabled:cursor-not-allowed ${className}`}
      style={{ color: "#666" }}
      onMouseEnter={e => { if (!disabled) (e.target as HTMLElement).style.color = hoverColor }}
      onMouseLeave={e => { if (!disabled) (e.target as HTMLElement).style.color = "#666" }}
    >
      [{children}]
    </button>
  )
}

export const TerminalButton = memo(TerminalButtonComponent)
