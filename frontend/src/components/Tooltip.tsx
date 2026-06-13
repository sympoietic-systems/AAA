import type { ReactNode } from "react"

interface TooltipProps {
  title: string
  subtitle?: string | number
  description?: string | null
  children: ReactNode
  titleColorClass?: string
  position?: "top-left" | "top-center"
}

export function Tooltip({
  title,
  subtitle,
  description,
  children,
  titleColorClass = "text-[#4ade80]",
  position = "top-left"
}: TooltipProps) {
  const positionClass = position === "top-center" 
    ? "left-1/2 -translate-x-1/2" 
    : "left-0"

  return (
    <span className="group relative inline-block">
      {children}
      <span className={`
        absolute bottom-full mb-1.5 px-2 py-1
        bg-[#1a1a1a] border border-[#333] rounded
        text-[10px] text-[#aaa] leading-snug
        whitespace-nowrap z-50 shadow-2xl
        opacity-0 group-hover:opacity-100
        transition-opacity duration-150
        pointer-events-none font-sans
        ${positionClass}
      `}>
        <span className={`block text-[11px] font-bold ${titleColorClass}`}>{title}</span>
        {subtitle !== undefined && <span className="block text-[#888] font-mono">{subtitle}</span>}
        {description && <span className="block text-[#666] max-w-48 whitespace-normal mt-0.5">{description}</span>}
      </span>
    </span>
  )
}
