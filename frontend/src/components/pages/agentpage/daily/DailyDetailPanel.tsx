import { useState, memo } from "react"
import { NotableMarkdown } from "../../../shared/NotableMarkdown"


export type MemoryNodeDetail = {
  id: string
  conversation_id: string
  node_type: string
  intensity: number
  scar: string
  intra_active_text: string
  surface_fragment: string
  agential_symmetry: string
  source_type: string
  source_id: string
  created_at: string | null
}

export type EvolutionEvent = {
  id: string
  label?: string
  name?: string
  statement?: string
  event_type: string
  rationale?: string
  lifecycle_stage?: string
  timestamp?: string
  created_at?: string
}

export type DailyDetail = {
  date: string
  metrics: {
    conversation_count: number
    message_count: number
    memory_node_count: number
    research_task_count: number
    evolution_count: number
  }
  memory_nodes: MemoryNodeDetail[]
  evolution: {
    beliefs: EvolutionEvent[]
    skills: EvolutionEvent[]
    commitments: EvolutionEvent[]
  }
  conversations: { id: string; title: string; message_count: number }[]
  research_tasks: { id: string; title: string; objective: string; status: string; result_summary?: string }[]
  summary: string | null
}


interface DailyDetailPanelProps {
  detail: DailyDetail | null
  activeSubTab: string
  onSubTabChange: (sub: string) => void
  onGenerateSummary: () => void
  isGeneratingSummary?: boolean
  isLoading?: boolean
}

export const DailyDetailPanel = memo(function DailyDetailPanel({
  detail,
  activeSubTab,
  onSubTabChange,
  onGenerateSummary,
  isGeneratingSummary,
  isLoading,
}: DailyDetailPanelProps) {
  const [nodeTypeFilter, setNodeTypeFilter] = useState<string>("all")
  const [evolutionCategoryFilter, setEvolutionCategoryFilter] = useState<string>("all")

  if (isLoading) {
    return (
      <div className="flex-1 min-h-0 flex items-center justify-center font-mono text-[11px] text-[#555] animate-pulse">
        Loading daily details...
      </div>
    )
  }

  if (!detail) {
    return (
      <div className="flex-1 min-h-0 flex items-center justify-center font-mono text-[11px] text-[#444] italic">
        Select a date from the calendar to inspect daily activity and synthesis.
      </div>
    )
  }

  const { date, metrics, summary, memory_nodes = [], evolution = { beliefs: [], skills: [], commitments: [] }, conversations = [], research_tasks = [] } = detail

  // Available node types
  const availableNodeTypes = Array.from(
    new Set(memory_nodes.map((n) => n.node_type).filter(Boolean))
  )

  const filteredNodes = memory_nodes.filter((node) => {
    if (nodeTypeFilter === "all") return true
    return node.node_type === nodeTypeFilter
  })

  // Filter passive decay/atrophy/support events
  const isAtrophy = (evt: EvolutionEvent) => {
    const et = (evt.event_type || "").toLowerCase()
    return et === "atrophy" || et === "decay" || et === "support" || et === "mass_update" || et === "tick"
  }

  const cleanBeliefs = (evolution.beliefs || []).filter((b) => !isAtrophy(b))
  const cleanSkills = (evolution.skills || []).filter((s) => !isAtrophy(s))
  const cleanCommitments = (evolution.commitments || []).filter((c) => !isAtrophy(c))

  const totalEvolutionEvents = cleanBeliefs.length + cleanSkills.length + cleanCommitments.length

  const getEventBadgeClass = (eventType: string) => {
    const et = (eventType || "").toLowerCase()
    if (et.includes("collapse") || et.includes("reject")) {
      return "text-semantic-red border-semantic-red/30 bg-semantic-red/10"
    }
    if (et.includes("crysta") || et.includes("nuclea") || et.includes("create") || et.includes("approve")) {
      return "text-semantic-green border-semantic-green/30 bg-semantic-green/10"
    }
    return "text-semantic-purple border-semantic-purple/30 bg-semantic-purple/10"
  }



  // Format date display
  let formattedDateHeader = date
  try {
    const [y, m, d] = date.split("-").map(Number)
    const dateObj = new Date(y, m - 1, d)
    formattedDateHeader = dateObj.toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    })
  } catch (e) {
    // fallback
  }

  const SUBTABS = [
    { key: "summary", label: "Summary" },
    { key: "nodes", label: `Memory Nodes (${memory_nodes.length})` },
    { key: "evolution", label: `Evolution (${totalEvolutionEvents})` },
    { key: "activity", label: `Activity (${conversations.length + research_tasks.length})` },
  ]

  return (
    <div className="flex-1 min-h-0 flex flex-col font-mono space-y-4 overflow-y-auto pr-2">
      {/* Header & Metrics Bar */}
      <div className="border border-[#222] p-3 space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#1a1a1a] pb-2">
          <div className="flex items-center gap-2">
            <span className="text-[12px] font-bold text-ui-primary">{formattedDateHeader}</span>
            <span className="text-[10px] text-[#555] font-mono">({date})</span>
          </div>

          <div className="flex items-center gap-2">
            {summary ? (
              <span className="text-[9px] text-semantic-green uppercase tracking-wider font-semibold border border-semantic-green/30 px-1.5 py-0.5">
                ★ Summarized
              </span>
            ) : (
              <span className="text-[9px] text-[#555] uppercase tracking-wider border border-[#333] px-1.5 py-0.5">
                Unsummarized
              </span>
            )}
          </div>
        </div>

        {/* Quick Metrics Key Value Grid */}
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10px]">
          <div>
            <span className="text-[#555]">Conversations: </span>
            <span className="text-[#ccc] font-bold">{metrics.conversation_count}</span>
            <span className="text-[#555] text-[9px]"> ({metrics.message_count} msgs)</span>
          </div>
          <div>
            <span className="text-[#555]">Memory Nodes: </span>
            <span className="text-semantic-blue font-bold">{metrics.memory_node_count}</span>
          </div>
          <div>
            <span className="text-[#555]">Research Tasks: </span>
            <span className="text-semantic-gold font-bold">{metrics.research_task_count}</span>
          </div>
          <div>
            <span className="text-[#555]">Evolution Events: </span>
            <span className="text-semantic-green font-bold">{totalEvolutionEvents}</span>
          </div>
        </div>
      </div>


      {/* Subtab Navigation Bar */}
      <div className="flex items-center gap-2 border-b border-[#222] pb-1.5 text-[11px] select-none">
        {SUBTABS.map((tab, idx) => {
          const isActive = activeSubTab === tab.key
          return (
            <div key={tab.key} className="flex items-center gap-2">
              {idx > 0 && <span className="text-[#333]">•</span>}
              <button
                onClick={() => onSubTabChange(tab.key)}
                className={`cursor-pointer transition-colors ${
                  isActive ? "text-[#94a3b8] font-bold" : "text-[#444] hover:text-[#777]"
                }`}
              >
                {tab.label}
              </button>
            </div>
          )
        })}
      </div>

      {/* Subtab Content Panels */}

      {/* 1. Summary Subtab */}
      {activeSubTab === "summary" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-[#8a7d74] uppercase tracking-wider">
              [ Daily Consolidation Summary ]
            </span>

            <button
              onClick={onGenerateSummary}
              disabled={isGeneratingSummary}
              className="text-action-dim hover:text-action-hover disabled:text-[#444] transition-colors cursor-pointer text-[10px] font-mono"
            >
              {isGeneratingSummary ? "[ generating summary... ]" : summary ? "[ re-summarize ]" : "[ generate summary ]"}
            </button>
          </div>

          {isGeneratingSummary ? (
            <div className="p-4 border border-[#222] text-[11px] text-[#555] animate-pulse italic">
              Generating first-person daily consolidation summary via LLM...
            </div>
          ) : summary ? (
            <div className="border border-[#1e1e1e] p-4 text-[#ccc] font-sans">
              <NotableMarkdown
                assetType="daily_summary"
                assetId={date}
                content={summary}
                title={`daily consolidation summary (${date})`}
                contentClassName="text-ui-secondary text-[11px] leading-relaxed markdown-body max-w-none space-y-2"
              />
            </div>
          ) : (

            <div className="border border-[#1a1a1a] p-6 text-center space-y-3">
              <div className="text-[11px] text-[#666] italic">
                No narrative text summary has been generated for this date yet.
              </div>
              <div>
                <button
                  onClick={onGenerateSummary}
                  className="text-action-dim hover:text-action-hover border border-action-dim/40 hover:border-action-hover px-3 py-1 text-[11px] font-mono transition-colors cursor-pointer"
                >
                  [ generate daily summary ]
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 2. Memory Nodes Subtab */}
      {activeSubTab === "nodes" && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 text-[10px]">
            <span className="text-[#8a7d74] uppercase tracking-wider">
              [ Memory Nodes Accreted ({memory_nodes.length}) ]
            </span>

            {/* Type Filter Pills */}
            <div className="flex flex-wrap items-center gap-1 font-mono text-[9px]">
              <button
                onClick={() => setNodeTypeFilter("all")}
                className={`px-1.5 py-0.5 border cursor-pointer transition-colors ${
                  nodeTypeFilter === "all"
                    ? "border-action-hover text-action-hover bg-action-hover/10"
                    : "border-[#222] text-[#666] hover:text-[#ccc]"
                }`}
              >
                All ({memory_nodes.length})
              </button>
              {availableNodeTypes.map((type) => {
                const count = memory_nodes.filter((n) => n.node_type === type).length
                return (
                  <button
                    key={type}
                    onClick={() => setNodeTypeFilter(type)}
                    className={`px-1.5 py-0.5 border cursor-pointer transition-colors ${
                      nodeTypeFilter === type
                        ? "border-semantic-blue text-semantic-blue bg-semantic-blue/10"
                        : "border-[#222] text-[#666] hover:text-[#ccc]"
                    }`}
                  >
                    {type} ({count})
                  </button>
                )
              })}
            </div>
          </div>

          {filteredNodes.length === 0 ? (
            <div className="text-[#444] italic text-[11px] py-4 text-center">
              No memory nodes found for selected filter.
            </div>
          ) : (
            <div className="space-y-2">
              {filteredNodes.map((node) => (
                <div key={node.id} className="border border-[#1f1f1f] p-2.5 space-y-1.5 hover:border-[#333] transition-colors">
                  <div className="flex items-center justify-between text-[10px]">
                    <div className="flex items-center gap-2">
                      <span className="text-semantic-blue font-bold uppercase">[{node.node_type}]</span>
                      <span className="text-[#666] font-mono">intensity: {node.intensity}</span>
                      {node.agential_symmetry && (
                        <span className="text-[#8f7ba8] text-[9px]">({node.agential_symmetry})</span>
                      )}
                    </div>
                    {node.created_at && <span className="text-[#444] text-[9px]">{node.created_at}</span>}
                  </div>

                  <div className="text-[11px] text-[#ccc] font-sans leading-snug">
                    {node.intra_active_text || node.surface_fragment || "No node text payload."}
                  </div>

                  {node.scar && (
                    <div className="text-[9px] text-semantic-red font-mono">
                      scar: {node.scar}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 3. Evolution Subtab */}
      {activeSubTab === "evolution" && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 text-[10px]">
            <span className="text-[#8a7d74] uppercase tracking-wider">
              [ Structural Evolution Events ({totalEvolutionEvents}) ]
            </span>

            {/* Evolution Category Filter Pills */}
            <div className="flex flex-wrap items-center gap-1 font-mono text-[9px]">
              <button
                onClick={() => setEvolutionCategoryFilter("all")}
                className={`px-1.5 py-0.5 border cursor-pointer transition-colors ${
                  evolutionCategoryFilter === "all"
                    ? "border-action-hover text-action-hover bg-action-hover/10"
                    : "border-[#222] text-[#666] hover:text-[#ccc]"
                }`}
              >
                All ({totalEvolutionEvents})
              </button>
              <button
                onClick={() => setEvolutionCategoryFilter("beliefs")}
                className={`px-1.5 py-0.5 border cursor-pointer transition-colors ${
                  evolutionCategoryFilter === "beliefs"
                    ? "border-semantic-green text-semantic-green bg-semantic-green/10"
                    : "border-[#222] text-[#666] hover:text-[#ccc]"
                }`}
              >
                Beliefs ({cleanBeliefs.length})
              </button>
              <button
                onClick={() => setEvolutionCategoryFilter("skills")}
                className={`px-1.5 py-0.5 border cursor-pointer transition-colors ${
                  evolutionCategoryFilter === "skills"
                    ? "border-semantic-purple text-semantic-purple bg-semantic-purple/10"
                    : "border-[#222] text-[#666] hover:text-[#ccc]"
                }`}
              >
                Skills ({cleanSkills.length})
              </button>
              <button
                onClick={() => setEvolutionCategoryFilter("commitments")}
                className={`px-1.5 py-0.5 border cursor-pointer transition-colors ${
                  evolutionCategoryFilter === "commitments"
                    ? "border-semantic-gold text-semantic-gold bg-semantic-gold/10"
                    : "border-[#222] text-[#666] hover:text-[#ccc]"
                }`}
              >
                Commitments ({cleanCommitments.length})
              </button>
            </div>
          </div>

          {/* Belief Transitions */}
          {(evolutionCategoryFilter === "all" || evolutionCategoryFilter === "beliefs") && (
            <div className="space-y-2">
              <div className="text-[10px] text-semantic-green uppercase tracking-wider">
                ● Belief System Events ({cleanBeliefs.length})
              </div>
              {cleanBeliefs.length === 0 ? (
                <div className="text-[#444] text-[10px] italic pl-2">No discrete belief events on this date.</div>
              ) : (
                <div className="space-y-1.5 pl-2 border-l border-[#222]">
                  {cleanBeliefs.map((b) => (
                    <div key={b.id} className="text-[11px] space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className={`font-bold text-[9px] uppercase px-1 py-0.5 border ${getEventBadgeClass(b.event_type)}`}>
                          {b.event_type}
                        </span>
                        <span className="text-[#eee] font-mono">{b.label}</span>
                        {b.lifecycle_stage && <span className="text-[#666] text-[9px]">stage:{b.lifecycle_stage}</span>}
                      </div>
                      {b.statement && <div className="text-[#aaa] text-[10px] font-sans">{b.statement}</div>}
                      {b.rationale && <div className="text-[#666] text-[9px] italic">Rationale: {b.rationale}</div>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Skill System Events */}
          {(evolutionCategoryFilter === "all" || evolutionCategoryFilter === "skills") && (
            <div className="space-y-2">
              <div className="text-[10px] text-semantic-purple uppercase tracking-wider">
                ◆ Skill System Events ({cleanSkills.length})
              </div>
              {cleanSkills.length === 0 ? (
                <div className="text-[#444] text-[10px] italic pl-2">No discrete skill events on this date.</div>
              ) : (
                <div className="space-y-1.5 pl-2 border-l border-[#222]">
                  {cleanSkills.map((s) => (
                    <div key={s.id} className="text-[11px] space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className={`font-bold text-[9px] uppercase px-1 py-0.5 border ${getEventBadgeClass(s.event_type)}`}>
                          {s.event_type}
                        </span>
                        <span className="text-[#eee] font-mono">{s.name}</span>
                        {s.lifecycle_stage && <span className="text-[#666] text-[9px]">stage:{s.lifecycle_stage}</span>}
                      </div>
                      {s.rationale && <div className="text-[#666] text-[9px] italic">Rationale: {s.rationale}</div>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Commitment Events */}
          {(evolutionCategoryFilter === "all" || evolutionCategoryFilter === "commitments") && (
            <div className="space-y-2">
              <div className="text-[10px] text-semantic-gold uppercase tracking-wider">
                ▲ Commitment Events ({cleanCommitments.length})
              </div>
              {cleanCommitments.length === 0 ? (
                <div className="text-[#444] text-[10px] italic pl-2">No discrete commitment events on this date.</div>
              ) : (
                <div className="space-y-1.5 pl-2 border-l border-[#222]">
                  {cleanCommitments.map((c) => (
                    <div key={c.id} className="text-[11px] space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className={`font-bold text-[9px] uppercase px-1 py-0.5 border ${getEventBadgeClass(c.event_type)}`}>
                          {c.event_type}
                        </span>
                        <span className="text-[#eee] font-mono">{c.label}</span>
                      </div>
                      {c.statement && <div className="text-[#aaa] text-[10px] font-sans">{c.statement}</div>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}


      {/* 4. Activity Subtab */}
      {activeSubTab === "activity" && (
        <div className="space-y-4">
          {/* Active Conversations */}
          <div className="space-y-2">
            <div className="text-[10px] text-[#8a7d74] uppercase tracking-wider">
              [ Active Conversations ({conversations.length}) ]
            </div>
            {conversations.length === 0 ? (
              <div className="text-[#444] text-[10px] italic">No active conversations recorded on this date.</div>
            ) : (
              <div className="space-y-1">
                {conversations.map((c) => (
                  <a
                    key={c.id}
                    href={`/chat?c=${c.id}`}
                    className="flex items-center justify-between p-2 border border-[#1f1f1f] hover:border-action-hover transition-colors text-[11px] group"
                  >
                    <span className="text-[#ccc] group-hover:text-action-hover truncate">{c.title}</span>
                    <span className="text-[#555] text-[10px] shrink-0">{c.message_count} msgs</span>
                  </a>
                ))}
              </div>
            )}
          </div>

          {/* Autonomous Research Tasks */}
          <div className="space-y-2">
            <div className="text-[10px] text-semantic-gold uppercase tracking-wider">
              [ Autonomous Research Tasks ({research_tasks.length}) ]
            </div>
            {research_tasks.length === 0 ? (
              <div className="text-[#444] text-[10px] italic">No research tasks executed on this date.</div>
            ) : (
              <div className="space-y-2">
                {research_tasks.map((rt) => (
                  <div key={rt.id} className="border border-[#1f1f1f] p-2 space-y-1 text-[11px]">
                    <div className="flex items-center justify-between">
                      <span className="text-semantic-gold font-bold">{rt.title}</span>
                      <span className="text-[#666] text-[9px] uppercase">[{rt.status}]</span>
                    </div>
                    <div className="text-[#999] text-[10px]">{rt.objective}</div>
                    {rt.result_summary && (
                      <div className="text-[#777] text-[9px] italic border-t border-[#1a1a1a] pt-1">
                        Result: {rt.result_summary}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
})
