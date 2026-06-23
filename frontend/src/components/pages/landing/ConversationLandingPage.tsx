import { useState, useEffect, memo, useCallback, useRef } from "react"
import type { ConversationInfo, NoteInfo } from "../../../api/client"
import { getConversation } from "../../../api/conversations"
import { getNotes, deleteNote, updateNote } from "../../../api/notes"
import { generateHumanSummary } from "../../../api/conversations"
import { formatDateTime } from "../../../utils/dateFormat"
import { NotesSection } from "../../shared/NotesSection"
import { MemoryNodesSection } from "../../shared/MemoryNodesSection"
import { HeaderContainer, HeaderIndicator, HeaderActionButton, HeaderLogo, HeaderSeparator, CreasesDropdown, UnifiedFooter } from "../../UI"

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
  agentFlux?: boolean
}

type DetailTab = "summary" | "notes" | "memory_nodes"

function Tags({ tags }: { tags?: any[] }) {
  if (!tags || tags.length === 0) return null
  return (
    <span>
      {tags.map((t, i) => {
        let color = "text-[#555]"
        if (t.tag_type === "structural") {
          if (t.tag === "dreams") color = "text-semantic-purple"
          else if (t.tag === "other agents") color = "text-semantic-sand"
          else color = "text-semantic-green"
        } else if (t.tag_type === "keyword") color = "text-semantic-blue"
        else if (t.tag_type === "diffractive") color = "text-semantic-slate"
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

export const ConversationLandingPage = memo(function ConversationLandingPage({
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
  agentFlux,
}: Props) {
  const [searchQuery, setSearchQuery] = useState("")
  const [activeCategory, setActiveCategory] = useState<"all" | "user" | "dreams" | "agents">("all")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detailConv, setDetailConv] = useState<ConversationInfo | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const detailRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const updatedConvIds = useRef<Set<string>>(new Set())

  // Tab state
  const [activeTab, setActiveTab] = useState<DetailTab>("summary")
  const [notes, setNotes] = useState<NoteInfo[] | null>(null)
  const [notesLoading, setNotesLoading] = useState(false)
  const [generatingSummary, setGeneratingSummary] = useState(false)
  const visitedTabs = useRef<Set<string>>(new Set())

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

  // Fetch detail when a conversation is selected
  useEffect(() => {
    if (!selectedId) {
      setDetailConv(null)
      return
    }
    // Reset tab data on selection change
    setActiveTab("summary")
    setNotes(null)
    visitedTabs.current = new Set()

    // Skip cache for conversations we've locally updated (e.g. generated human summary)
    if (!updatedConvIds.current.has(selectedId)) {
      const cached = conversations.find(c => c.id === selectedId)
      if (cached && cached.summary !== undefined) {
        setDetailConv(cached)
        return
      }
    }
    setDetailLoading(true)
    getConversation(selectedId)
      .then(c => setDetailConv(c))
      .catch(() => setDetailConv(null))
      .finally(() => setDetailLoading(false))
  }, [selectedId, conversations])

  // Lazy load tab content (notes — memory nodes are self-fetching via MemoryNodesSection)
  const ensureTab = useCallback((tab: DetailTab, convId: string) => {
    const key = `${convId}:${tab}`
    if (visitedTabs.current.has(key)) return
    visitedTabs.current.add(key)

    if (tab === "notes") {
      setNotesLoading(true)
      getNotes(convId)
        .then(n => setNotes(n))
        .catch(() => setNotes([]))
        .finally(() => setNotesLoading(false))
    }
  }, [])

  const handleTabClick = useCallback((tab: DetailTab) => {
    setActiveTab(tab)
    if (selectedId) ensureTab(tab, selectedId)
  }, [selectedId, ensureTab])

  const handleGenerateHumanSummary = useCallback(async () => {
    if (!selectedId || generatingSummary) return
    setGeneratingSummary(true)
    try {
      const updated = await generateHumanSummary(selectedId)
      setDetailConv(updated)
      updatedConvIds.current.add(selectedId)
    } catch (e) {
      console.error("Failed to generate human summary:", e)
    } finally {
      setGeneratingSummary(false)
    }
  }, [selectedId, generatingSummary])

  // Scroll into view on mobile
  useEffect(() => {
    if (window.matchMedia("(min-width: 768px)").matches) return
    if (selectedId && detailRef.current) {
      detailRef.current.scrollIntoView({ behavior: "smooth", block: "start" })
    } else if (!selectedId && listRef.current) {
      listRef.current.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }, [selectedId])

  // Event delegation: click anywhere in the list container
  const handleListClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-conv-id]") as HTMLElement | null
    if (!el) return
    const id = el.getAttribute("data-conv-id")
    if (id) {
      setSelectedId(prev => prev === id ? null : id)
    }
  }, [])

  // Double-click to enter conversation
  const handleListDoubleClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-conv-id]") as HTMLElement | null
    if (!el) return
    const id = el.getAttribute("data-conv-id")
    if (id) onSelect(id)
  }, [onSelect])

  const selectedConv = selectedId ? conversations.find(c => c.id === selectedId) : null
  const displayConv = detailConv || selectedConv || null

  const structural = displayConv?.tags?.find(t => t.tag_type === "structural")
  let letter = "U"
  let letterColor = "text-semantic-green"
  if (structural?.tag === "dreams") { letter = "D"; letterColor = "text-semantic-purple" }
  else if (structural?.tag === "other agents") { letter = "A"; letterColor = "text-semantic-sand" }

  return (
    <div className="flex flex-col h-screen w-full bg-[#0c0c0c] font-mono text-[#666] selection:bg-action-hover/10">

      {/* Header — single line */}
      <HeaderContainer>
        <span className="text-[11px] text-semantic-header tracking-widest uppercase select-none flex items-center gap-1.5">
          <HeaderIndicator intent="green" />
          <HeaderLogo onClick={() => window.location.href = '/nodes'} />
          <HeaderSeparator />
          <HeaderLogo
            onClick={() => window.location.href = '/research'}
            title="Research console"
          >
            research
          </HeaderLogo>
          <HeaderSeparator />
          <span className="text-[#555] normal-case">{totalCount} conversations</span>
        </span>
        <div className="flex items-center gap-4">
          <CreasesDropdown conversations={conversations} />
          <HeaderActionButton onClick={() => window.location.href = '/agent'}>
            agent
          </HeaderActionButton>
          <HeaderActionButton onClick={onNew}>
            + new
          </HeaderActionButton>
          {showLogout && onLogout && (
            <HeaderActionButton
              onClick={onLogout}
              className="hover:text-red-500!"
            >
              logout
            </HeaderActionButton>
          )}
        </div>
      </HeaderContainer>

      {/* Two-panel body */}
      <div className="flex-1 flex flex-col md:flex-row min-h-0 md:overflow-hidden overflow-auto">

        {/* LEFT: Conversation list */}
        <div className="md:w-[450px] shrink-0 w-full flex flex-col min-h-0 md:overflow-hidden border-r border-[#1a1a1a] max-h-[45vh] md:max-h-none">
          {/* Filter bar */}
          <div className="flex items-center gap-4 px-5 py-2 border-b border-[#1a1a1a] shrink-0">
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

          {/* List */}
          <div
            ref={listRef}
            onClick={handleListClick}
            onDoubleClick={handleListDoubleClick}
            className="flex-1 overflow-y-auto py-2 select-none"
          >
            {loading && conversations.length === 0 ? (
              <p className="text-[10px] text-[#444] animate-pulse px-5">loading...</p>
            ) : conversations.length === 0 ? (
              <p className="text-[10px] text-[#333] px-5">no results</p>
            ) : (
              <div className="flex flex-col">
                {conversations.map((conv) => {
                  const s = conv.tags?.find(t => t.tag_type === "structural")

                  let l = "U"
                  let lc = "text-semantic-green"
                  if (s?.tag === "dreams") { l = "D"; lc = "text-semantic-purple" }
                  else if (s?.tag === "other agents") { l = "A"; lc = "text-semantic-sand" }

                  const title = (() => {
                    const t = conv.title || "untitled"
                    if (s?.tag === "dreams") return t.replace(/^Dream Log:\s*/i, "")
                    return t
                  })()

                  return (
                    <div
                      key={conv.id}
                      data-conv-id={conv.id}
                      data-selected={selectedId === conv.id ? "true" : undefined}
                      className={`
                        flex items-baseline gap-1.5 px-5 py-1.5 cursor-pointer
                        border-l-2 transition-colors
                        ${selectedId === conv.id ? "border-action-hover bg-action-hover/5" : "border-transparent hover:bg-[#111]"}
                      `}
                    >
                      <span className="text-[10px] text-[#444] shrink-0 w-24">
                        {formatDateTime(conv.updated_at || conv.created_at)}
                      </span>
                      <span className={`text-[10px] font-bold shrink-0 ${lc}`}>[{l}]</span>
                      <span className="text-[#333] shrink-0">&gt;&gt;</span>
                      <span className="flex items-baseline gap-2 truncate min-w-0 flex-1">
                        <span className="text-[11px] text-[#bbb] truncate">
                          {title}
                        </span>
                        <span className="text-[10px] text-[#333] shrink-0">[{conv.message_count}]</span>
                      </span>
                    </div>
                  )
                })}
              </div>
            )}

            {hasMore && (
              <button
                onClick={onLoadMore}
                disabled={loadingMore}
                className="mt-3 px-5 text-[10px] text-[#444] hover:text-[#888] transition-colors cursor-pointer disabled:text-[#2a2a2a]"
              >
                {loadingMore ? "loading..." : "// load more"}
              </button>
            )}
          </div>
        </div>

        {/* RIGHT: Detail panel */}
        <div ref={detailRef} className="flex-1 md:min-h-0 min-w-0 w-full md:overflow-hidden md:flex md:flex-col">
          {!displayConv ? (
            <div className="flex-1 flex items-center justify-center select-none">
              <span className="text-[10px] text-[#444] italic font-mono">
                [ select a conversation to inspect ]
              </span>
            </div>
          ) : detailLoading ? (
            <div className="flex-1 flex items-center justify-center select-none">
              <span className="text-[10px] text-[#444] animate-pulse font-mono">loading...</span>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto flex flex-col min-h-0">
              {/* Header row */}
              <div className="flex items-center justify-between px-6 pt-5 pb-3 border-b border-[#1a1a1a] shrink-0">
                <div className="flex items-center gap-3 min-w-0">
                  <button
                    onClick={() => {
                      setSelectedId(null)
                      listRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
                    }}
                    className="md:hidden text-[10px] text-[#555] hover:text-[#aaa] transition-colors cursor-pointer shrink-0"
                  >
                    [◀ list]
                  </button>
                  <span className={`text-[14px] font-bold shrink-0 ${letterColor}`}>[{letter}]</span>
                  <h2 className="text-[13px] text-[#ccc] font-mono font-bold tracking-wide truncate uppercase">
                    {displayConv.title || "untitled"}
                  </h2>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <button
                    onClick={() => onSelect(displayConv.id)}
                    className="text-[11px] text-action-dim hover:text-action-hover transition-colors cursor-pointer"
                  >
                    [enter]
                  </button>
                  {agentFlux && (
                    <button
                      onClick={() => {
                        if (confirm("Delete?")) onDelete(displayConv.id)
                      }}
                      className="text-[11px] text-[#666] hover:text-[#ef4444] transition-colors cursor-pointer"
                    >
                      [delete]
                    </button>
                  )}
                </div>
              </div>

              {/* Meta */}
              <div className="flex flex-wrap gap-x-4 gap-y-0.5 px-6 py-2 text-[10px] font-mono shrink-0">
                <span>
                  <span className="text-[#555]">created: </span>
                  <span className="text-[#94a3b8]">{formatDateTime(displayConv.created_at)}</span>
                </span>
                <span>
                  <span className="text-[#555]">updated: </span>
                  <span className="text-[#94a3b8]">{formatDateTime(displayConv.updated_at)}</span>
                </span>
                <span>
                  <span className="text-[#555]">messages: </span>
                  <span className="text-[#94a3b8]">{displayConv.message_count}</span>
                </span>
                {displayConv.tags && displayConv.tags.length > 0 && (
                  <span className="w-full">
                    <span className="text-[#555]">tags: </span>
                    <Tags tags={displayConv.tags} />
                  </span>
                )}
              </div>

              {/* Tab bar */}
              <div className="flex items-center gap-2 px-6 py-2 border-b border-[#1a1a1a] text-[10px] font-mono select-none shrink-0">
                {(["summary", "notes", "memory_nodes"] as const).map((tab, i) => {
                  let label = tab === "memory_nodes" ? "memory nodes" : tab
                  let countStr = ""
                  if (tab === "notes" && notes !== null) countStr = ` (${notes.length})`
                  return (
                    <span key={tab} className="flex items-center gap-2">
                      {i > 0 && <span className="text-[#333]">•</span>}
                      <button
                        onClick={() => handleTabClick(tab)}
                        className={`transition-colors cursor-pointer ${
                          activeTab === tab ? "text-[#94a3b8]" : "text-[#444] hover:text-[#777]"
                        }`}
                      >
                        {label}{countStr}
                      </button>
                    </span>
                  )
                })}
              </div>

              {/* Tab content */}
              <div className="flex-1 overflow-y-auto px-6 py-4">
                {/* Summary tab */}
                {activeTab === "summary" && (
                  <div>
                    <div className="text-[9px] text-semantic-header uppercase tracking-wider mb-2">
                      [ Summary ]
                    </div>
                    {displayConv.human_summary ? (
                      <p className="text-[11px] text-[#aaa] leading-relaxed whitespace-pre-line font-mono">
                        {displayConv.human_summary}
                      </p>
                    ) : (
                      <div>
                        <p className="text-[10px] text-[#444] italic font-mono mb-2">
                          {displayConv.summary
                            ? "no human-readable summary yet"
                            : "no summary available yet"}
                        </p>
                        <button
                          onClick={handleGenerateHumanSummary}
                          disabled={generatingSummary}
                          className="text-[10px] text-action-dim hover:text-action-hover transition-colors cursor-pointer disabled:text-[#2a2a2a] font-mono"
                        >
                          {generatingSummary ? "[ generating summary... ]" : "[ generate summary ]"}
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {/* Notes tab */}
                {activeTab === "notes" && (
                  <div>
                    <div className="text-[9px] text-semantic-header uppercase tracking-wider mb-2">
                      [ Notes ]
                    </div>
                    {notesLoading ? (
                      <p className="text-[10px] text-[#444] animate-pulse font-mono">loading notes...</p>
                    ) : (
                      <NotesSection
                        notes={notes || []}
                        onNavigate={(_messageId) => window.open(`/nodes?c=${displayConv.id}&m=${_messageId}`, '_blank')}
                        onDeleteNote={(noteId) => {
                          deleteNote(displayConv.id, noteId).then(() => {
                            setNotes(prev => (prev || []).filter(n => n.id !== noteId))
                          }).catch(() => {})
                        }}
                        onUpdateNote={(noteId, comment, visibility) => {
                          updateNote(displayConv.id, noteId, comment, visibility).then((updated) => {
                            setNotes(prev => (prev || []).map(n => n.id === noteId ? updated : n))
                          }).catch(() => {})
                        }}
                      />
                    )}
                  </div>
                )}

                {/* Memory Nodes tab */}
                {activeTab === "memory_nodes" && (
                  <div>
                    <div className="text-[9px] text-semantic-header uppercase tracking-wider mb-2">
                      [ Memory Nodes ]
                    </div>
                    <MemoryNodesSection
                      conversationId={displayConv.id}
                      enabled={activeTab === "memory_nodes"}
                      className="grid gap-3"
                      style={{ gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 420px), 1fr))" }}
                    />
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
      <UnifiedFooter />
    </div>
  )
})
