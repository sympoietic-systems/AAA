import type { ReactNode } from "react"

interface TooltipProps {
  title: string
  subtitle?: string | number
  description?: string | null
  children: ReactNode
  titleColorClass?: string
  position?: "top-left" | "top-center" | "top-right" | "bottom-left" | "bottom-center" | "bottom-right"
  className?: string
}

export function Tooltip({
  title,
  subtitle,
  description,
  children,
  titleColorClass = "text-semantic-green",
  position = "top-left",
  className = "inline-block"
}: TooltipProps) {
  const getPositionClasses = () => {
    switch (position) {
      case "top-center":
        return "bottom-full mb-1.5 left-1/2 -translate-x-1/2"
      case "top-right":
        return "bottom-full mb-1.5 right-0"
      case "bottom-left":
        return "top-full mt-1.5 left-0"
      case "bottom-center":
        return "top-full mt-1.5 left-1/2 -translate-x-1/2"
      case "bottom-right":
        return "top-full mt-1.5 right-0"
      case "top-left":
      default:
        return "bottom-full mb-1.5 left-0"
    }
  }

  const positionClass = getPositionClasses()

  return (
    <span className={`group relative ${className}`}>
      {children}
      <span className={`
        absolute px-2 py-1
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
