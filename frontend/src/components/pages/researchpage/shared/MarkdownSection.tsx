import React, { memo, useState, useCallback, useRef } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import { BracketHeader } from "./BracketHeader"
import { TerminalButton } from "../../../UI"

interface MarkdownSectionProps {
  title: string
  content: string
  fullHeight?: boolean
  actions?: boolean
  fileName?: string
}

/** Slugify a title into a short, filesystem-safe base name. */
function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")   // strip non-word chars (keep letters, digits, spaces, hyphens)
    .trim()
    .replace(/\s+/g, "-")        // spaces → hyphens
    .replace(/-+/g, "-")         // collapse repeated hyphens
    .slice(0, 60)                // cap length
    || "research-report"
}

/** Extract the first markdown heading (# or ##) from content. */
function extractReportTitle(markdown: string): string | null {
  const match = markdown.match(/^#{1,2}\s+(.+)$/m)
  return match?.[1]?.trim() ?? null
}

export const MarkdownSection = memo(function MarkdownSection({ title, content, fullHeight, actions, fileName }: MarkdownSectionProps) {
  const [copied, setCopied] = useState(false)
  const contentRef = useRef<HTMLDivElement>(null)

  const baseName = slugify(extractReportTitle(content) ?? fileName ?? title)

  const copyMarkdown = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {}
  }, [content])

  const exportMarkdown = useCallback(() => {
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${baseName}.md`
    a.click()
    URL.revokeObjectURL(url)
  }, [content, baseName])

  const exportPdf = useCallback(() => {
    const html = contentRef.current?.innerHTML ?? ""
    const printWindow = window.open("", "_blank", "width=800,height=900")
    if (!printWindow) return
    printWindow.document.write(`<!DOCTYPE html><html><head><title>${baseName}</title><style>
      body{font-family:-apple-system,Segoe UI,Roboto,monospace;padding:2.5rem;color:#222;max-width:800px;margin:0 auto;line-height:1.7;font-size:13px}
      h1,h2,h3,h4{color:#333;margin-top:1.2em}
      h1{font-size:1.5em}h2{font-size:1.25em}h3{font-size:1.1em}
      table{border-collapse:collapse;width:100%;margin:0.8em 0}
      th,td{border:1px solid #ccc;padding:6px 10px;text-align:left;font-size:12px}
      th{background:#f5f5f5}
      code{background:#f0f0f0;padding:2px 5px;border-radius:3px;font-size:12px}
      pre{background:#f6f6f6;padding:10px;overflow-x:auto;border-radius:4px}
      pre code{background:none;padding:0}
      blockquote{border-left:3px solid #ccc;margin:0;padding-left:1em;color:#666}
      a{color:#0066cc}
      img{max-width:100%}
      ul,ol{padding-left:1.5em}
    </style></head><body>${html}</body></html>`)
    printWindow.document.close()
    printWindow.focus()
    setTimeout(() => printWindow.print(), 300)
  }, [])

  return (
    <div className={fullHeight ? "h-full flex flex-col min-h-0" : ""}>
      {actions ? (
        <div className="flex items-center justify-between mb-1 shrink-0">
          <span className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">[{title}]</span>
          <div className="flex items-center gap-2">
            <TerminalButton onClick={copyMarkdown} intent="neutral">
              {copied ? "copied!" : "copy markdown"}
            </TerminalButton>
            <TerminalButton onClick={exportMarkdown} intent="neutral">export markdown</TerminalButton>
            <TerminalButton onClick={exportPdf} intent="cyan">export pdf</TerminalButton>
          </div>
        </div>
      ) : (
        <BracketHeader text={title} />
      )}
      <div
        ref={contentRef}
        className={`text-[#94a3b8] text-[10px] leading-relaxed prose prose-invert prose-xs max-w-none ${fullHeight ? "flex-1 min-h-0 overflow-y-auto" : "max-h-96 overflow-y-auto"}`}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{content}</ReactMarkdown>
      </div>
    </div>
  )
})
