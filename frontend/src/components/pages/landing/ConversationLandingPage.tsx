import { useState, useEffect } from "react"
import type { ConversationInfo } from "../../../api/client"

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
      hour12: false,
    })
  } catch {
    return dateStr
  }
}

function Tags({ tags }: { tags?: any[] }) {
  if (!tags || tags.length === 0) return null
  return (
    <span>
      {tags.map((t, i) => {
        let color = "text-[#555]"
        if (t.tag_type === "structural") {
          if (t.tag === "dreams") color = "text-[#a892ee]"
          else if (t.tag === "other agents") color = "text-[#e09b67]"
          else color = "text-[#6bc28c]"
        } else if (t.tag_type === "keyword") color = "text-[#6fafe2]"
        else if (t.tag_type === "diffractive") color = "text-[#4ec9b0]"
        return (
          <span key={t.tag} className={`font-mono text-[10px] ${color}`}>
            {i > 0 && <span className="text-[#333]"> // </span>}
            {t.tag}
          </span>
        )
      })}
    </span>
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

  const getTagForCategory = (cat: typeof activeCategory): string | undefined => {
    if (cat === "dreams") return "dreams"
    if (cat === "agents") return "other agents"
    if (cat === "user") return "user conversation"
    return undefined
  }

  useEffect(() => {
    const handler = setTimeout(() => {
      onSearchAndFilter(getTagForCategory(activeCategory) ?? null, searchQuery)
    }, 250)
    return () => clearTimeout(handler)
  }, [searchQuery, activeCategory])

  const toggleExpand = (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    setExpandedIds(prev => ({ ...prev, [id]: !prev[id] }))
  }

  return (
    <div className="flex flex-col h-screen w-full bg-[#0c0c0c] font-mono text-[#666] selection:bg-[#4ade80]/20">

      {/* Header — single line */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-[#1a1a1a] shrink-0">
        <span className="text-[11px] text-[#444] tracking-widest uppercase select-none">
          <span className="text-[#4ade80]">■</span>
          <button
            onClick={() => window.open('/agent', '_blank')}
            className="ml-2 hover:text-[#a892ee] transition-colors cursor-pointer"
            title="Open agent page"
          >
            symbia
          </button>
          <span className="text-[#333] mx-2">//</span>
          <span>{totalCount} conversations</span>
        </span>
        <div className="flex items-center gap-4">
          <button
            onClick={onNew}
            className="text-[11px] text-[#4ade80] hover:text-white transition-colors cursor-pointer select-none"
          >
            [+ new]
          </button>
          {showLogout && onLogout && (
            <button
              onClick={onLogout}
              className="text-[11px] text-[#444] hover:text-red-500 transition-colors cursor-pointer select-none"
            >
              [logout]
            </button>
          )}
        </div>
      </div>

      {/* Filter bar — inline, no boxes */}
      <div className="flex items-center gap-4 px-6 py-2 border-b border-[#1a1a1a] shrink-0">
        <span className="text-[10px] text-[#333] select-none">filter:</span>
        {(["all", "user", "dreams", "agents"] as const).map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`text-[10px] transition-colors cursor-pointer select-none ${
              activeCategory === cat ? "text-[#ccc]" : "text-[#444] hover:text-[#888]"
            }`}
          >
            {activeCategory === cat ? `[${cat}]` : cat}
          </button>
        ))}
        <span className="text-[#333] select-none mx-1">//</span>
        <input
          type="text"
          placeholder="search..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1 max-w-xs text-[10px] bg-transparent text-[#aaa] outline-none placeholder-[#333] border-b border-[#222] focus:border-[#444] pb-px transition-colors"
        />
      </div>

      {/* Log list */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {loading && conversations.length === 0 ? (
          <p className="text-[10px] text-[#444] animate-pulse mt-4">loading...</p>
        ) : conversations.length === 0 ? (
          <p className="text-[10px] text-[#333] mt-4">no results</p>
        ) : (
          <div className="flex flex-col">
            {conversations.map((conv) => {
              const isExpanded = !!expandedIds[conv.id]
              const structural = conv.tags?.find(t => t.tag_type === "structural")

              let letter = "U"
              let letterColor = "text-[#6bc28c]"
              if (structural?.tag === "dreams") { letter = "D"; letterColor = "text-[#a892ee]" }
              else if (structural?.tag === "other agents") { letter = "A"; letterColor = "text-[#e09b67]" }

              const title = (() => {
                const t = conv.title || "untitled"
                if (structural?.tag === "dreams") return t.replace(/^Dream Log:\s*/i, "")
                return t
              })()

              return (
                <div key={conv.id} className="group py-2 border-b border-[#111] last:border-0">
                  {/* Main row */}
                  <div
                    className="flex items-baseline gap-2 cursor-pointer select-none"
                    onClick={() => onSelect(conv.id)}
                  >
                    {/* Date */}
                    <span className="text-[10px] text-[#444] shrink-0 w-28">
                      {formatDate(conv.updated_at || conv.created_at)}
                    </span>

                    {/* Type letter */}
                    <span className={`text-[10px] font-bold shrink-0 ${letterColor}`}>[{letter}]</span>

                    {/* Separator */}
                    <span className="text-[#333] shrink-0">&gt;&gt;</span>

                    {/* Title */}
                    <span className="text-[11px] text-[#bbb] group-hover:text-white transition-colors truncate flex-1 min-w-0">
                      {title}
                    </span>

                    {/* Node count */}
                    <span className="text-[10px] text-[#333] shrink-0">[{conv.message_count}]</span>

                    {/* Actions — only visible on hover */}
                    <span className="hidden group-hover:inline-flex items-center gap-2 shrink-0">
                      <button
                        onClick={(e) => toggleExpand(e, conv.id)}
                        className="text-[10px] text-[#555] hover:text-[#888] transition-colors"
                      >
                        {isExpanded ? "[-]" : "[+]"}
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          if (confirm("Delete?")) onDelete(conv.id)
                        }}
                        className="text-[10px] text-[#444] hover:text-red-500 transition-colors"
                      >
                        [x]
                      </button>
                    </span>
                  </div>

                  {/* Tags row */}
                  {conv.tags && conv.tags.length > 0 && (
                    <div className="pl-32 mt-0.5">
                      <Tags tags={conv.tags} />
                    </div>
                  )}

                  {/* Expanded summary */}
                  {isExpanded && (
                    <div
                      className="pl-32 mt-2 flex flex-col gap-1.5 pb-1"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {conv.summary && (
                        <p className="text-[10px] text-[#555] leading-relaxed whitespace-pre-line">
                          {conv.summary}
                        </p>
                      )}
                      {conv.human_summary && (
                        <p className="text-[10px] text-[#6bc28c] leading-relaxed whitespace-pre-line">
                          &gt; {conv.human_summary}
                        </p>
                      )}
                      {!conv.summary && !conv.human_summary && (
                        <p className="text-[10px] text-[#333]">no summary available</p>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}

        {/* Load more */}
        {hasMore && (
          <button
            onClick={onLoadMore}
            disabled={loadingMore}
            className="mt-4 text-[10px] text-[#444] hover:text-[#888] transition-colors cursor-pointer disabled:text-[#2a2a2a]"
          >
            {loadingMore ? "loading..." : "// load more"}
          </button>
        )}
      </div>
    </div>
  )
}
