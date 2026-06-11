import { useState, useRef } from "react"
import type { ConversationInfo } from "../api/client"

interface Props {
  conversations: ConversationInfo[]
  activeId: string
  loading: boolean
  onSelect: (id: string) => void
  // Delete, New
  onDelete: (id: string) => void
  onNew: () => void
  collapsed: boolean
  onToggle: () => void
  showLogout?: boolean
  onLogout?: () => void
  width?: number
}

export function ConversationList({
  conversations,
  activeId,
  loading,
  onSelect,
  onDelete,
  onNew,
  collapsed,
  onToggle,
  showLogout,
  onLogout,
  width,
}: Props) {
  const [searchQuery, setSearchQuery] = useState("")
  const [activeCategory, setActiveCategory] = useState<"all" | "user" | "dreams" | "agents">("all")
  const [tooltipInfo, setTooltipInfo] = useState<{ conv: ConversationInfo; top: number } | null>(null)
  const outerRef = useRef<HTMLDivElement>(null)

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return ""
    const d = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    if (diffMins < 1) return "just now"
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    const diffDays = Math.floor(diffHours / 24)
    if (diffDays < 7) return `${diffDays}d ago`
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: d.getFullYear() !== now.getFullYear() ? "numeric" : undefined })
  }

  // Filter conversations
  const filteredConversations = conversations.filter((conv) => {
    // 1. Structural category filter
    if (activeCategory !== "all") {
      const structuralTag = conv.tags?.find(t => t.tag_type === "structural")?.tag
      if (activeCategory === "dreams" && structuralTag !== "dreams") return false
      if (activeCategory === "agents" && structuralTag !== "other agents") return false
      if (activeCategory === "user" && structuralTag !== "user conversation") return false
    }

    // 2. Query search
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim()
      const titleMatch = (conv.title || "").toLowerCase().includes(query)
      const tagMatch = conv.tags?.some(t => t.tag.toLowerCase().includes(query))
      return titleMatch || tagMatch
    }

    return true
  })
  return (
    <div
      ref={outerRef}
      className={`
        border-[#222] bg-[#0c0c0c]
        md:border-r md:border-l-0 md:h-full
        border-b
        flex flex-col shrink-0
        relative
        transition-[width] duration-200
        ${collapsed ? "md:w-9 w-full" : "w-full"}
      `}
      style={!collapsed && width ? { width: `${width}px` } : undefined}
    >
      {collapsed && (
        <button
          onClick={onToggle}
          className="
            flex items-center gap-1.5 shrink-0
            text-xs text-[#555] hover:text-[#888]
            transition-colors
            md:flex-col md:justify-start md:gap-2 md:py-3 md:px-0
            md:h-full
            flex-row justify-start py-2 px-3
            select-none
          "
        >
          <span className="text-[10px]">{"\u25B6"}</span>
          <span className="md:[writing-mode:vertical-rl] md:text-[10px] md:tracking-wider text-[11px]">
            conversations
          </span>
        </button>
      )}

      <div
        className={`flex-1 flex flex-col min-h-0 overflow-hidden transition-opacity duration-150 ${
          collapsed ? "hidden opacity-0" : "opacity-100"
        }`}
      >
        <div className="flex items-center shrink-0 px-3 py-2 border-b border-[#222]">
          <button
            onClick={onToggle}
            className="flex items-center gap-1.5 text-[10px] text-[#555] hover:text-[#888] transition-colors"
          >
            <span>{"\u25C0"}</span>
            <span>close</span>
          </button>
        </div>

        <button
          onClick={onNew}
          className="
            w-full flex items-center gap-2 px-3 py-2
            text-[11px] text-[#4ade80] hover:bg-[#1a2a1a]
            border-b border-[#1a1a1a]
            transition-colors cursor-pointer
          "
        >
          <span className="text-[13px] leading-none">+</span>
          <span>new conversation</span>
        </button>

        {/* Search and Category Filters */}
        <div className="px-3 py-2 border-b border-[#222] bg-[#090909] flex flex-col gap-1.5 shrink-0">
          <input
            type="text"
            placeholder="Search title or tag..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full text-[10px] text-[#aaa] bg-[#141414] border border-[#222] px-2 py-1 outline-none focus:border-[#4ade80] placeholder-[#444] rounded-[2px] font-mono"
          />
          <div className="flex gap-1">
            {(["all", "user", "dreams", "agents"] as const).map((cat) => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`
                  flex-1 py-0.5 text-[8px] tracking-wider uppercase border rounded-[2px] transition-colors font-mono cursor-pointer
                  ${activeCategory === cat
                    ? "bg-[#1a2a1a] text-[#4ade80] border-[#4ade80]"
                    : "bg-transparent text-[#555] border-[#222] hover:text-[#888]"
                  }
                `}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading && conversations.length === 0 && (
            <p className="text-[10px] text-[#555] animate-pulse px-3 py-2">
              loading...
            </p>
          )}

          {!loading && conversations.length === 0 && (
            <p className="text-[10px] text-[#444] px-3 py-2">
              no conversations yet
            </p>
          )}

          {!loading && filteredConversations.length === 0 && conversations.length > 0 && (
            <p className="text-[10px] text-[#444] px-3 py-2">
              no matching conversations
            </p>
          )}

          {filteredConversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => onSelect(conv.id)}
              onMouseEnter={(e) => {
                if (outerRef.current) {
                  const outerRect = outerRef.current.getBoundingClientRect()
                  const itemRect = e.currentTarget.getBoundingClientRect()
                  setTooltipInfo({ conv, top: itemRect.top - outerRect.top })
                }
              }}
              onMouseLeave={() => setTooltipInfo(null)}
              className={`
                group flex items-center gap-1.5 px-3 py-2 cursor-pointer
                border-b border-[#1a1a1a] last:border-b-0
                transition-colors
                ${activeId === conv.id
                  ? "bg-[#1a2a1a] border-l-2 border-l-[#4ade80]"
                  : "hover:bg-[#111] border-l-2 border-l-transparent"
                }
              `}
            >
              {(() => {
                const structural = conv.tags?.find(t => t.tag_type === "structural")
                let letterColor = "text-[#6bc28c]"
                let letter = "U"
                if (structural) {
                  if (structural.tag === "dreams") { letterColor = "text-[#a892ee]"; letter = "D" }
                  else if (structural.tag === "other agents") { letterColor = "text-[#e09b67]"; letter = "A" }
                }
                return (
                  <span className={`text-[8px] font-mono font-bold shrink-0 ${letterColor}`}>
                    [{letter}]
                  </span>
                )
              })()}
              <div className="flex-1 min-w-0">
                <p className="text-[11px] text-[#aaa] truncate">
                  {(() => {
                    const title = conv.title || "untitled"
                    const structural = conv.tags?.find(t => t.tag_type === "structural")
                    if (structural?.tag === "dreams") return title.replace(/^Dream Log:\s*/i, "")
                    return title
                  })()}
                </p>
              </div>
              <span className="text-[#444] text-[9px] font-mono select-none shrink-0">{">>"}</span>
              <span className="text-[9px] text-[#555] font-mono shrink-0">{conv.message_count}msg</span>

              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onDelete(conv.id)
                }}
                className="
                  text-[8px] text-[#444] hover:text-[#ef4444]
                  opacity-0 group-hover:opacity-100
                  transition-opacity
                  shrink-0 px-1
                "
                title="Delete conversation"
              >
                {"\u2715"}
              </button>
            </div>
          ))}
        </div>

        {tooltipInfo && (
          <div
            className="absolute z-50 left-full top-0 ml-1 bg-[#0c0c0c] border border-[#222] px-3 py-2 rounded-[2px] shadow-lg min-w-[280px] max-w-[640px] pointer-events-none"
            style={{ top: tooltipInfo.top }}
          >
            <p className="text-[10px] text-[#ccc] font-mono mb-1 leading-relaxed break-words">
              {tooltipInfo.conv.title || "untitled"}
            </p>
            {tooltipInfo.conv.created_at && (
              <p className="text-[8px] text-[#555] font-mono mb-1">
                created {formatDate(tooltipInfo.conv.created_at)}
              </p>
            )}
            {tooltipInfo.conv.tags && tooltipInfo.conv.tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {tooltipInfo.conv.tags.map((t) => {
                  let tagStyle = "text-[#888]"
                  if (t.tag_type === "structural") {
                    if (t.tag === "dreams") tagStyle = "text-[#a892ee]"
                    else if (t.tag === "other agents") tagStyle = "text-[#e09b67]"
                    else tagStyle = "text-[#6bc28c]"
                  } else if (t.tag_type === "diffractive") {
                    tagStyle = "text-[#4ec9b0]"
                  }
                  return (
                    <span key={t.tag} className={`text-[8px] ${tagStyle} font-mono`}>
                      {t.tag}
                    </span>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {showLogout && onLogout && (
          <button
            onClick={onLogout}
            className="
              w-full flex items-center justify-center gap-1.5 px-3 py-2
              text-[10px] text-[#ef4444] hover:bg-[#221212] hover:text-[#ff6666]
              border-t border-[#222]
              transition-colors cursor-pointer mt-auto shrink-0 uppercase tracking-wider font-mono
            "
          >
            <span>logout</span>
          </button>
        )}
      </div>
    </div>
  )
}
