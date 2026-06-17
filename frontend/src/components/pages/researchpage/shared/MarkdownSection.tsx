import React, { memo } from "react"
import ReactMarkdown from "react-markdown"
import { BracketHeader } from "./BracketHeader"

interface MarkdownSectionProps {
  title: string
  content: string
}

export const MarkdownSection = memo(function MarkdownSection({ title, content }: MarkdownSectionProps) {
  return (
    <div>
      <BracketHeader text={title} />
      <div className="text-[#94a3b8] text-[10px] leading-relaxed max-h-96 overflow-y-auto prose prose-invert prose-xs max-w-none">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </div>
  )
})
