import { memo } from "react"

type Intent = "save" | "delete" | "edit" | "neutral" | "cyan" | "purple"

const INTENT_HOVER: Record<Intent, string> = {
  save:    "#ff6b00", // hot orange
  delete:  "#b86a6a", // semantic-red (desaturated red)
  edit:    "#ff6b00", // hot orange
  neutral: "#ff6b00", // hot orange
  cyan:    "#ff6b00", // hot orange
  purple:  "#ff6b00", // hot orange
}

interface TerminalButtonProps {
  children: React.ReactNode
  intent?: Intent
  onClick?: () => void
  disabled?: boolean
  className?: string
  title?: string
}

function TerminalButtonComponent({
  children, intent = "neutral", onClick, disabled, className = "", title
}: TerminalButtonProps) {
  const hoverColor = INTENT_HOVER[intent]

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`text-[10px] text-action-dim font-mono cursor-pointer select-none transition-colors disabled:text-[#333] disabled:cursor-not-allowed ${className}`}
      style={{ color: "#b37e5d" }}
      onMouseEnter={e => { if (!disabled) (e.target as HTMLElement).style.color = hoverColor }}
      onMouseLeave={e => { if (!disabled) (e.target as HTMLElement).style.color = "#b37e5d" }}
    >
      [{children}]
    </button>
  )
}

export const TerminalButton = memo(TerminalButtonComponent)
