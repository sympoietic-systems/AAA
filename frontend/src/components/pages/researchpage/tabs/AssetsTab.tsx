import React, { memo, useState } from "react"
import type { ResearchTask } from "../../../../api/research"
import { KeyValueGrid } from "../../../UI"
import { BracketHeader } from "../shared/BracketHeader"
import { EmptyState } from "../shared/EmptyState"
import { TwoPanelLayout } from "../shared/TwoPanelLayout"

export const AssetsTab = memo(function AssetsTab({ task }: { task: ResearchTask }) {
  const assets = task.assets ?? []
  const [selectedId, setSelectedId] = useState<string | null>(null)

  if (assets.length === 0) return <EmptyState message=" no assets harvested " />

  const selected = selectedId ? assets.find(a => a.id === selectedId) : null

  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-aid]") as HTMLElement | null
    if (!el) return
    const id = el.getAttribute("data-aid")
    setSelectedId(prev => prev === id ? null : id)
  }

  return (
    <TwoPanelLayout
      left={
        <div className="flex-1 space-y-0.5 overflow-y-auto pr-1 select-none" onClick={handleClick}>
          {[...assets].reverse().map(a => (
            <div key={a.id} data-aid={a.id}
              className={`flex items-center gap-1.5 px-1.5 py-1 cursor-pointer border-l-2 transition-colors text-[10px]
                ${selectedId === a.id ? "border-[#a78bfa] bg-[#1a1a2e]/50" : "border-transparent hover:bg-[#111]"}`}
            >
              <span className="text-[#4ade80] text-[8px] font-mono shrink-0">{(a.relevance_score ?? 0).toFixed(2)}</span>
              <span className="text-[#bbb] font-mono truncate">{a.url.slice(0, 60)}</span>
            </div>
          ))}
        </div>
      }
      right={
        selected ? (
          <div className="space-y-2 text-[10px]">
            <BracketHeader text=" Asset Detail " />
            <a href={selected.url} target="_blank" rel="noopener noreferrer" className="text-[#4ade80] hover:text-[#6ee7b0] underline break-all">{selected.url}</a>
            <KeyValueGrid items={[
              { key: "relevance", value: (selected.relevance_score ?? 0).toFixed(2), valueColor: "#4ade80" },
              { key: "novelty", value: (selected.novelty_score ?? 0).toFixed(2) },
              { key: "diffractive", value: (selected.diffractive_score ?? 0).toFixed(2) },
            ]} />
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-[#444] italic text-xs select-none">[ select an asset ]</div>
        )
      }
    />
  )
})
