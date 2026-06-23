import { memo } from "react"

interface TerminalHeaderProps {
  children: React.ReactNode
  className?: string
}

function TerminalHeaderComponent({ children, className = "" }: TerminalHeaderProps) {
  return (
    <div className={`text-semantic-header uppercase text-[9px] tracking-wider ${className}`}>
      {children}
    </div>
  )
}

export const TerminalHeader = memo(TerminalHeaderComponent)
