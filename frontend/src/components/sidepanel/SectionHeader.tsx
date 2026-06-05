interface SectionHeaderProps {
  label: string
  count?: number
  open: boolean
  onToggle: () => void
}

export function SectionHeader({
  label,
  count,
  open,
  onToggle,
}: SectionHeaderProps) {
  return (
    <button
      onClick={onToggle}
      className="w-full flex items-center gap-1.5 py-1 text-left hover:text-[#aaa] text-[#888] text-xs transition-colors font-mono"
    >
      <span className="text-[10px]">{open ? "▼" : "▶"}</span>
      <span>{label}</span>
      {count !== undefined && <span className="text-[#444]">({count})</span>}
    </button>
  )
}
