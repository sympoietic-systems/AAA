import React, { memo, useMemo, useState } from "react"

export type JsonBlockVariant = "json" | "dim" | "prompt" | "raw"

export interface JsonBlockProps {
  data: any
  variant?: JsonBlockVariant
  maxHeight?: string
  className?: string
  collapsible?: boolean
  defaultCollapsed?: boolean
  label?: string
}

const VARIANT_STYLES: Record<JsonBlockVariant, string> = {
  json:   "text-[#4ade80] text-[8px] bg-[#0c0c0c]",
  dim:    "text-[#555] text-[7px] bg-[#080808]",
  prompt: "text-[#888] text-[8px] bg-[#0c0c0c]",
  raw:    "text-[#666] text-[8px] bg-[#0c0c0c]",
}

export const JsonBlock = memo(function JsonBlock({
  data, variant = "json", maxHeight = "max-h-48", className = "",
  collapsible = false, defaultCollapsed = false, label,
}: JsonBlockProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed)

  const content = useMemo(() => {
    if (data === null || data === undefined) return ""
    if (typeof data === "string") return data
    return JSON.stringify(data, null, 2)
  }, [data])

  if (collapsible) {
    return (
      <div className="border border-[#1a1a1a] rounded-sm bg-[#080808] overflow-hidden">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-between px-2 py-1.5 text-[8px] uppercase text-[#555] hover:text-[#bbb] hover:bg-[#111] select-none cursor-pointer font-mono border-none outline-none"
        >
          <span className="flex items-center gap-1.5">
            <span className="text-[#333] text-[7px]">{collapsed ? "▶" : "▼"}</span>
            <span>{label || variant}</span>
          </span>
          <span className="text-[7.5px] font-semibold text-[#4ade80]/70">{collapsed ? "show" : "hide"}</span>
        </button>
        {!collapsed && (
          <pre className={`${VARIANT_STYLES[variant]} border-t border-[#1a1a1a] p-2 ${maxHeight} overflow-y-auto whitespace-pre-wrap break-all ${className}`}>
            {content}
          </pre>
        )}
      </div>
    )
  }

  return (
    <pre className={`${VARIANT_STYLES[variant]} border border-[#1a1a1a] p-2 rounded-sm ${maxHeight} overflow-y-auto whitespace-pre-wrap break-all ${className}`}>
      {content}
    </pre>
  )
})
