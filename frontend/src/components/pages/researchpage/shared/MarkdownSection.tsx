import { printContent } from "../../../../utils/printContent"
import { memo, useState, useCallback, useRef } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import remarkMath from "remark-math"
import rehypeKatex from "rehype-katex"
import { BracketHeader } from "./BracketHeader"
import { TerminalButton } from "../../../UI"
import { copyToClipboard } from "../../../../utils/clipboard"

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
    const success = await copyToClipboard(content)
    if (success) {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    }
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
    printContent(contentRef.current, baseName)
  }, [baseName])

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
        <ReactMarkdown
          remarkPlugins={[remarkGfm, remarkBreaks, remarkMath]}
          rehypePlugins={[rehypeKatex]}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  )
})
