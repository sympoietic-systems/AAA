import React, { memo } from "react"
import type { ResearchTask } from "../../../../api/research"
import { STATUS_COLORS } from "../constants/taskConstants"
import { EmptyState } from "../shared/EmptyState"
import { TwoPanelLayout } from "../shared/TwoPanelLayout"

export const BranchesTab = memo(function BranchesTab({ task }: { task: ResearchTask }) {
  const branches = task.branches ?? []
  if (branches.length === 0) return <EmptyState message=" no branches — orchestrator uses Steps instead " />

  return (
    <TwoPanelLayout
      left={
        <div className="flex-1 space-y-0.5 overflow-y-auto pr-1">
          {branches.map((b: any) => {
            const sc = STATUS_COLORS[b.status] ?? "#666"
            return (
              <div key={b.id} className="flex items-center gap-1.5 px-1.5 py-1 text-[10px]">
                <span style={{ color: sc }} className="text-[8px]">●</span>
                <span className="text-[#bbb] font-mono truncate">{b.query || b.id?.slice(0, 12)}</span>
                <span style={{ color: sc }} className="text-[8px] ml-auto">{b.status}</span>
              </div>
            )
          })}
        </div>
      }
      right={
        <div className="flex items-center justify-center h-full text-[#444] italic text-xs select-none">[ select a branch ]</div>
      }
    />
  )
})
