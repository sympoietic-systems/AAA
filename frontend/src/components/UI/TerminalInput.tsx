import { memo } from "react"

interface TerminalInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
  type?: "text" | "search"
}

function TerminalInputComponent({
  value, onChange, placeholder, className = "", type = "text"
}: TerminalInputProps) {
  return (
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className={`bg-transparent border-b border-[#222]/40 py-0.5 text-xs text-[#ddd] font-mono outline-none focus:border-[#4ade80] placeholder:text-[#444] ${className}`}
    />
  )
}

export const TerminalInput = memo(TerminalInputComponent)
