import React, { memo, useMemo } from "react"

export type JsonBlockVariant = "json" | "dim" | "prompt" | "raw"

interface JsonBlockProps {
  data: any
  variant?: JsonBlockVariant
  maxHeight?: string
  className?: string
}

const VARIANT_STYLES: Record<JsonBlockVariant, string> = {
  json:   "text-[#4ade80] text-[8px] bg-[#0c0c0c]",
  dim:    "text-[#555] text-[7px] bg-[#080808]",
  prompt: "text-[#888] text-[8px] bg-[#0c0c0c]",
  raw:    "text-[#666] text-[8px] bg-[#0c0c0c]",
}

export const JsonBlock = memo(function JsonBlock({
  data, variant = "json", maxHeight = "max-h-48", className = "",
}: JsonBlockProps) {
  const content = useMemo(() => {
    if (data === null || data === undefined) return ""
    if (typeof data === "string") return data
    return JSON.stringify(data, null, 2)
  }, [data])

  return (
    <pre className={`${VARIANT_STYLES[variant]} border border-[#1a1a1a] p-2 rounded-sm ${maxHeight} overflow-y-auto whitespace-pre-wrap break-all ${className}`}>
      {content}
    </pre>
  )
})
