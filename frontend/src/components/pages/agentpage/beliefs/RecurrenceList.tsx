import type { ReactNode } from "react"
import type { BeliefNodeInfo } from "../../../../api/types"

export function RecurrenceList({ entries, selectedId, renderItem }: {
  entries: BeliefNodeInfo[][]; selectedId: string | null; renderItem: (item: BeliefNodeInfo) => ReactNode
}) {
  return entries.map(members => members.length === 1 ? renderItem(members[0]) : (
    <details key={members[0].id} open={members.some(item => item.id === selectedId) || undefined}
      className="border border-white/30 text-white bg-black font-mono text-[11px]">
      <summary className="cursor-pointer p-2 focus-visible:outline focus-visible:outline-white">
        Repeated fragment · {members.length} entries · context incomplete
      </summary>
      <p className="px-2 pb-2">Occurrences add no independent support. Scope and equivalence remain unknown.</p>
      {members[0].recurrence_group?.scan_truncated && <p className="px-2">Grouping covers a limited part of the queue.</p>}
      {members.map(item => <div key={item.id}>
        {renderItem(item)}
        <button type="button" data-belief-id={item.id} className="px-2 underline cursor-pointer focus-visible:outline focus-visible:outline-white">
          Open entry {item.label}
        </button>
        <p className="px-2 pb-1 text-[10px]">
          {item.admission_history?.[0]?.created_at || "Time unavailable"}
        </p>
      </div>)}
    </details>
  ))
}
