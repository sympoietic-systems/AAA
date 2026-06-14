import { useState, memo } from "react"

interface CollapsibleSectionProps {
  label: string
  count: number
  icon?: string
  iconColor?: string
  children: React.ReactNode
  defaultOpen?: boolean
}

export const CollapsibleSection = memo(function CollapsibleSection({
  label, count, icon, iconColor, children, defaultOpen = true,
}: CollapsibleSectionProps) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 w-full text-left cursor-pointer select-none pb-0.5"
      >
        <span className="text-[9px] text-[#666] font-mono leading-none">{open ? "▼" : "▶"}</span>
        {icon && <span style={{ color: iconColor }} className="text-[10px]">{icon}</span>}
        <span className="text-[#6c6c8a] font-mono text-[9px] uppercase tracking-wider">{label}</span>
        <span className="text-[9px] text-[#444] ml-0.5">({count})</span>
      </button>
      {open && <div className="space-y-0.5">{children}</div>}
    </div>
  )
})
