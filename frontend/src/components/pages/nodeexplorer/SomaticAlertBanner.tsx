import React, { Children } from "react"

interface SomaticAlertBannerProps {
  type?: string
  status?: string
  title?: string
  comment?: string
  children?: React.ReactNode
}

function extractText(children: React.ReactNode): string {
  if (!children) return ""
  if (typeof children === "string") return children.trim()
  if (typeof children === "number") return String(children)
  const array = Children.toArray(children)
  return array
    .map(c => {
      if (!c) return ""
      if (typeof c === "string" || typeof c === "number") return String(c)
      if (React.isValidElement<{ children?: React.ReactNode }>(c)) return extractText(c.props.children)
      return ""
    })
    .join(" ")
    .trim()
}

export const SomaticAlertBanner: React.FC<SomaticAlertBannerProps> = ({
  type = "sycophancy_rupture",
  status,
  title,
  comment,
  children,
}) => {
  const content = extractText(children) || comment || title || ""
  
  const formattedType = type
    .replace(/[_-]/g, " ")
    .toUpperCase()

  const isQuiescence = type.toLowerCase().includes("quiesce") || type.toLowerCase().includes("standby")

  const accentColor = isQuiescence
    ? "border-l-[#888888] border-neutral-700/60"
    : "border-l-amber-500 border-amber-500/30"

  const iconColor = isQuiescence ? "text-[#888888]" : "text-amber-400"
  const headerTextColor = isQuiescence ? "text-[#aaaaaa]" : "text-amber-400"
  const bodyTextColor = isQuiescence ? "text-[#999999]" : "text-amber-200/90"

  return (
    <div
      className={`my-3 p-3 rounded-sm bg-[#08090b] border border-l-4 ${accentColor} font-mono select-text`}
      role="alert"
    >
      <div className="flex items-center justify-between gap-2 border-b border-[#1f2024] pb-1.5 mb-2">
        <div className="flex items-center gap-2 text-[10px] tracking-wider uppercase font-semibold">
          <span className={`${iconColor} text-xs font-bold leading-none`}>▲</span>
          <span className={headerTextColor}>SOMATIC REFUSAL // {formattedType}</span>
        </div>
        {status && (
          <span className="text-[9px] text-[#666] tracking-tight uppercase">
            [{status}]
          </span>
        )}
      </div>
      {content && (
        <div className={`text-xs ${bodyTextColor} leading-relaxed pl-1 whitespace-pre-wrap`}>
          {content}
        </div>
      )}
    </div>
  )
}
