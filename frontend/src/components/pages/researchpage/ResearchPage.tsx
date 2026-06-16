// ResearchPage — Autonomous Research Console.
// Self-supporting: fetches its own data via useResearch hook.

import React, { memo, useState } from "react"
import { useResearch } from "../../../hooks/useResearch"
import { NewResearchForm } from "./NewResearchForm"
import { TaskCard } from "./TaskCard"

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-2">
        [{label}]
      </div>
      <div className="space-y-2">{children}</div>
    </div>
  )
}

export const ResearchPage = memo(function ResearchPage() {
  const { tasks, summary, loading, error, dispatch, approve, reject, cancel } = useResearch()
  const [showForm, setShowForm] = useState(false)

  const active = tasks.filter(t => t.status === "active")
  const queued = tasks.filter(t => t.status === "queued")
  const proposed = tasks.filter(t => t.status === "proposed")
  const completed = tasks.filter(t => t.status === "completed")
  const failed = tasks.filter(t => t.status === "failed")

  return (
    <div className="flex flex-col h-full px-4 py-4 overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <span className="text-[#ddd] text-sm font-mono">symbia // research console</span>
          <span className="text-[#555] text-[10px] ml-2">
            {summary.active_count} active · {summary.queued_count} queued · {summary.pending_proposals} proposals
          </span>
        </div>
        <div className="flex items-center gap-2">
          {loading && <span className="text-[#555] text-[10px] animate-pulse">polling...</span>}
          <button
            onClick={() => setShowForm(!showForm)}
            className="text-[#666] hover:text-[#4ade80] text-xs font-mono transition-colors"
          >
            [{showForm ? "− collapse" : "+ new research"}]
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="text-[#ef4444] text-[10px] font-mono mb-3">[{error}]</div>
      )}

      {/* New Research Form */}
      {showForm && (
        <NewResearchForm onDispatch={dispatch} onClose={() => setShowForm(false)} />
      )}

      {/* Proposals */}
      {proposed.length > 0 && (
        <Section label={`Pending Proposals (${proposed.length})`}>
          {proposed.map(t => (
            <TaskCard key={t.id} task={t} onApprove={approve} onReject={reject} onCancel={cancel} />
          ))}
        </Section>
      )}

      {/* Active */}
      {active.length > 0 && (
        <Section label={`Active (${active.length})`}>
          {active.map(t => <TaskCard key={t.id} task={t} onCancel={cancel} />)}
        </Section>
      )}

      {/* Queued */}
      {queued.length > 0 && (
        <Section label={`Queued (${queued.length})`}>
          {queued.map(t => <TaskCard key={t.id} task={t} onCancel={cancel} />)}
        </Section>
      )}

      {/* Completed */}
      {completed.length > 0 && (
        <Section label={`Completed (${completed.length})`}>
          {completed.map(t => <TaskCard key={t.id} task={t} />)}
        </Section>
      )}

      {/* Failed */}
      {failed.length > 0 && (
        <Section label={`Failed (${failed.length})`}>
          {failed.map(t => <TaskCard key={t.id} task={t} onCancel={cancel} />)}
        </Section>
      )}

      {/* Empty state */}
      {tasks.length === 0 && !loading && (
        <div className="text-[#444] italic font-mono text-xs mt-8 text-center">
          [ no research tasks yet — dispatch one above ]
        </div>
      )}
    </div>
  )
})
