import React, { Children } from "react"

interface EpistemicPhaseBannerProps {
  type: "rupture_site" | "line_of_flight" | "new_plateau"
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

export const EpistemicPhaseBanner: React.FC<EpistemicPhaseBannerProps> = ({
  type,
  children,
}) => {
  const content = extractText(children)

  let badgeIcon = "⚡"
  let badgeTitle = "RUPTURE SITE"
  let accentBorder = "border-l-rose-500 border-rose-500/20"
  let titleColor = "text-rose-400"
  let bodyColor = "text-rose-200/90"

  if (type === "line_of_flight") {
    badgeIcon = "↗"
    badgeTitle = "LINE OF FLIGHT"
    accentBorder = "border-l-sky-500 border-sky-500/20"
    titleColor = "text-sky-400"
    bodyColor = "text-sky-200/90"
  } else if (type === "new_plateau") {
    badgeIcon = "⬡"
    badgeTitle = "NEW PLATEAU"
    accentBorder = "border-l-emerald-500 border-emerald-500/20"
    titleColor = "text-emerald-400"
    bodyColor = "text-emerald-200/90"
  }

  return (
    <div
      className={`my-3 p-3 rounded-sm bg-[#08090b] border border-l-4 ${accentBorder} font-mono select-text`}
      role="region"
    >
      <div className="flex items-center justify-between gap-2 border-b border-[#1f2024] pb-1.5 mb-2">
        <div className="flex items-center gap-2 text-[10px] tracking-wider uppercase font-semibold">
          <span className="text-xs font-bold leading-none">{badgeIcon}</span>
          <span className={titleColor}>{badgeTitle}</span>
          <span className="text-[9px] text-[#666] font-normal lowercase tracking-normal">
            (&lt;{type}&gt;)
          </span>
        </div>
      </div>
      {content && (
        <div className={`text-xs ${bodyColor} leading-relaxed pl-1 whitespace-pre-wrap font-sans`}>
          {content}
        </div>
      )}
    </div>
  )
}
