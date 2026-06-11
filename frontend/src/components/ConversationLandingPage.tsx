import { useState, useEffect } from "react"
import type { ConversationInfo } from "../api/client"

interface Props {
  conversations: ConversationInfo[]
  loading: boolean
  loadingMore: boolean
  hasMore: boolean
  totalCount: number
  onLoadMore: () => void
  onSelect: (id: string) => void
  onDelete: (id: string) => void
  onNew: () => void
  onSearchAndFilter: (tag?: string | null, search?: string) => void
  showLogout?: boolean
  onLogout?: () => void
}

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return ""
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false
    })
  } catch {
    return dateStr
  }
}

function renderTags(tags?: any[]) {
  if (!tags || tags.length === 0) return null
  return (
    <div className="flex flex-wrap items-center gap-y-0.5">
      {tags.map((t, i) => {
        let tagStyle = "text-[#888]"
        if (t.tag_type === "structural") {
          if (t.tag === "dreams") {
            tagStyle = "text-[#a892ee]"
          } else if (t.tag === "other agents") {
            tagStyle = "text-[#e09b67]"
          } else {
            tagStyle = "text-[#6bc28c]"
          }
        } else if (t.tag_type === "keyword") {
          tagStyle = "text-[#6fafe2]"
        } else if (t.tag_type === "diffractive") {
          tagStyle = "text-[#4ec9b0]"
        }
        return (
          <span key={t.tag} className={`text-[9px] ${tagStyle} font-mono`}>
            {i > 0 && <span className="text-[#444] select-none">{" // "}</span>}
            {t.tag}
          </span>
        )
      })}
    </div>
  )
}

export function ConversationLandingPage({
  conversations,
  loading,
  loadingMore,
  hasMore,
  totalCount,
  onLoadMore,
  onSelect,
  onDelete,
  onNew,
  onSearchAndFilter,
  showLogout,
  onLogout,
}: Props) {
  const [searchQuery, setSearchQuery] = useState("")
  const [activeCategory, setActiveCategory] = useState<"all" | "user" | "dreams" | "agents">("all")
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({})

  // Map category to structural tag strings compatible with the database
  const getTagForCategory = (cat: typeof activeCategory): string | undefined => {
    if (cat === "dreams") return "dreams"
    if (cat === "agents") return "other agents"
    if (cat === "user") return "user conversation"
    return undefined
  }

  // Trigger search on query change (with a minor debounce)
  useEffect(() => {
    const handler = setTimeout(() => {
      onSearchAndFilter(getTagForCategory(activeCategory) ?? null, searchQuery)
    }, 250)
    return () => clearTimeout(handler)
  }, [searchQuery, activeCategory])

  const toggleExpandSummary = (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    setExpandedIds(prev => ({
      ...prev,
      [id]: !prev[id]
    }))
  }

  return (
    <div className="flex flex-col h-screen w-full bg-[#0c0c0c] text-[#aaa] font-sans selection:bg-[#4ade80]/20">
      {/* Top Navigation / Dashboard Bar */}
      <header className="flex items-center justify-between border-b border-[#222] px-6 py-4 bg-[#090909] shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-[#4ade80] animate-pulse" />
          <span className="text-xs font-mono tracking-widest text-white uppercase font-bold">
            AUTOPOSIETIS APPARATUS // SYMPIESIS
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onNew}
            className="
              px-3 py-1.5 rounded-[3px] text-xs font-mono font-bold
              bg-[#1a2a1a] text-[#4ade80] border border-[#4ade80]/30 hover:border-[#4ade80]
              transition-all duration-150 cursor-pointer shadow-[0_0_10px_rgba(74,222,128,0.05)]
            "
          >
            + NEW CONVERSATION
          </button>
          {showLogout && onLogout && (
            <button
              onClick={onLogout}
              className="
                px-3 py-1.5 rounded-[3px] text-xs font-mono border border-[#333] hover:border-red-500/50 hover:bg-[#221212] hover:text-[#ff6666]
                transition-all duration-150 cursor-pointer
              "
            >
              LOGOUT
            </button>
          )}
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 overflow-y-auto px-6 py-8 max-w-4xl w-full mx-auto flex flex-col gap-6">
        
        {/* Search & Category Filter Section */}
        <div className="bg-[#090909] border border-[#222] rounded-[4px] p-4 flex flex-col md:flex-row gap-4 shadow-lg shrink-0">
          <div className="flex-1 flex flex-col gap-1.5">
            <label className="text-[10px] font-mono uppercase tracking-wider text-[#555]">
              Search Title or Tag keyword
            </label>
            <input
              type="text"
              placeholder="Search details..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="
                w-full text-xs text-[#ccc] bg-[#141414] border border-[#222] px-3 py-2 outline-none
                focus:border-[#4ade80] focus:shadow-[0_0_10px_rgba(74,222,128,0.08)] placeholder-[#444] rounded-[3px] font-mono transition-all
              "
            />
          </div>
          <div className="flex flex-col gap-1.5 md:w-64">
            <label className="text-[10px] font-mono uppercase tracking-wider text-[#555]">
              Structural Type
            </label>
            <div className="flex border border-[#222] rounded-[3px] overflow-hidden bg-[#141414]">
              {(["all", "user", "dreams", "agents"] as const).map((cat) => (
                <button
                  key={cat}
                  onClick={() => setActiveCategory(cat)}
                  className={`
                    flex-1 py-2 text-[9px] tracking-wider uppercase transition-all font-mono cursor-pointer
                    ${activeCategory === cat
                      ? "bg-[#1a2a1a] text-[#4ade80] font-bold"
                      : "text-[#555] hover:text-[#888] hover:bg-[#181818]"
                    }
                  `}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Results List */}
        <div className="flex flex-col gap-3 flex-1">
          <div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-wider text-[#555] border-b border-[#222] pb-2 px-1">
            <span>Conversations Log ({totalCount})</span>
            <span>Last Activity</span>
          </div>

          {loading && conversations.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <div className="w-6 h-6 border-2 border-[#4ade80] border-t-transparent rounded-full animate-spin" />
              <span className="text-xs font-mono text-[#555]">loading matrix...</span>
            </div>
          ) : conversations.length === 0 ? (
            <div className="text-center py-20 border border-dashed border-[#222] rounded-[4px] bg-[#090909]">
              <p className="text-xs font-mono text-[#555]">no logs discovered matching query</p>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {conversations.map((conv) => {
                const isExpanded = !!expandedIds[conv.id]
                const structural = conv.tags?.find(t => t.tag_type === "structural")
                let letterColor = "text-[#6bc28c] border-[#6bc28c]/20"
                let letter = "U"
                if (structural) {
                  if (structural.tag === "dreams") {
                    letterColor = "text-[#a892ee] border-[#a892ee]/20"
                    letter = "D"
                  } else if (structural.tag === "other agents") {
                    letterColor = "text-[#e09b67] border-[#e09b67]/20"
                    letter = "A"
                  }
                }

                return (
                  <div
                    key={conv.id}
                    onClick={() => onSelect(conv.id)}
                    className="
                      group flex flex-col border border-[#222] hover:border-[#4ade80]/40 rounded-[4px] bg-[#090909]
                      transition-all duration-150 cursor-pointer shadow-sm hover:shadow-[0_4px_20px_rgba(0,0,0,0.4)]
                    "
                  >
                    {/* Header Details */}
                    <div className="flex items-center gap-3 px-4 py-3.5 select-none">
                      <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 border rounded-[3px] shrink-0 ${letterColor}`}>
                        [{letter}]
                      </span>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-xs font-mono font-medium text-[#ccc] group-hover:text-white truncate transition-colors">
                          {(() => {
                            const title = conv.title || "untitled log"
                            if (structural?.tag === "dreams") return title.replace(/^Dream Log:\s*/i, "")
                            return title
                          })()}
                        </h3>
                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                          <span className="text-[9px] text-[#555] font-mono">{conv.message_count} statements</span>
                          {conv.tags && conv.tags.length > 0 && (
                            <>
                              <span className="text-[#444] select-none text-[9px]">|</span>
                              {renderTags(conv.tags)}
                            </>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        <span className="text-[10px] text-[#555] font-mono">
                          {formatDate(conv.updated_at || conv.created_at)}
                        </span>
                        
                        <button
                          onClick={(e) => toggleExpandSummary(e, conv.id)}
                          className="
                            px-2 py-1 text-[9px] font-mono border border-[#222] rounded-[3px]
                            text-[#555] hover:text-[#4ade80] hover:border-[#4ade80]/30 transition-colors
                          "
                        >
                          {isExpanded ? "Hide" : "Summary"}
                        </button>

                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            if (confirm("Delete this conversation permanent?")) {
                              onDelete(conv.id)
                            }
                          }}
                          className="
                            p-1.5 text-xs text-[#444] hover:text-red-500 transition-colors rounded-[3px] hover:bg-red-500/10
                          "
                          title="Delete conversation"
                        >
                          {"\u2715"}
                        </button>
                      </div>
                    </div>

                    {/* Expandable summary tray */}
                    {isExpanded && (
                      <div
                        onClick={(e) => e.stopPropagation()}
                        className="px-4 pb-4 pt-1 border-t border-[#1b1b1b] bg-[#070707] rounded-b-[4px] flex flex-col gap-3"
                      >
                        <div className="flex flex-col gap-1 mt-2">
                          <span className="text-[9px] font-mono uppercase tracking-wider text-[#444]">System Summary</span>
                          <p className="text-xs text-[#888] leading-relaxed font-mono break-words whitespace-pre-line">
                            {conv.summary || "No automated structural summary synthesized yet."}
                          </p>
                        </div>
                        {conv.human_summary && (
                          <div className="flex flex-col gap-1">
                            <span className="text-[9px] font-mono uppercase tracking-wider text-[#444]">Human Inscription Summary</span>
                            <p className="text-xs text-[#888] leading-relaxed font-mono break-words whitespace-pre-line">
                              {conv.human_summary}
                            </p>
                          </div>
                        )}
                        <div className="flex flex-wrap items-center gap-1.5 mt-1 border-t border-[#1b1b1b] pt-2">
                          <span className="text-[9px] text-[#555] uppercase font-mono tracking-wider mr-1">tags:</span>
                          {renderTags(conv.tags)}
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {/* Lazy loading triggers */}
          {hasMore && (
            <div className="flex justify-center mt-4">
              <button
                onClick={onLoadMore}
                disabled={loadingMore}
                className="
                  px-6 py-2 rounded-[3px] text-xs font-mono tracking-wider
                  border border-[#222] bg-[#090909] text-[#888] hover:text-white hover:border-[#444]
                  transition-all cursor-pointer disabled:text-[#333] disabled:border-[#111]
                "
              >
                {loadingMore ? "RETRIEVING NEXT RECORD BLOCK..." : "LOAD MORE CONVERSATIONS"}
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
