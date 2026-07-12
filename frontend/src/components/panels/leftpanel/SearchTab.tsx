import React, { useState, useEffect, useCallback, useRef } from "react"
import { searchArchive, type SearchMatch } from "../../../api/search"

interface SearchTabProps {
  conversationId: string | null
  onNavigateFromSearch: (convId: string, msgId: number) => void
}

export const SearchTab: React.FC<SearchTabProps> = ({
  conversationId,
  onNavigateFromSearch,
}) => {
  const [query, setQuery] = useState("")
  const [scope, setScope] = useState<"current" | "all">("current")
  const [mode, setMode] = useState<"text" | "semantic" | "diffractive" | "glitch">("text")
  const [typeFilter, setTypeFilter] = useState<"all" | "message" | "note" | "memory_node">("all")
  const [results, setResults] = useState<SearchMatch[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const debounceTimer = useRef<NodeJS.Timeout | null>(null)

  const executeSearch = useCallback(async (searchQuery: string, currentScope: "current" | "all", currentMode: "text" | "semantic" | "diffractive" | "glitch") => {
    // If no query and not glitch mode, clear results
    if (currentMode !== "glitch" && !searchQuery.trim()) {
      setResults([])
      return
    }

    setLoading(true)
    setError(null)
    try {
      const scopeConvId = currentScope === "current" && conversationId ? conversationId : undefined
      const data = await searchArchive({
        q: searchQuery,
        conversation_id: scopeConvId,
        mode: currentMode,
      })
      setResults(data)
    } catch (err: any) {
      setError(err?.message || "Search failed")
    } finally {
      setLoading(false)
    }
  }, [conversationId])

  // Debounced search trigger
  useEffect(() => {
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current)
    }
    
    // Trigger instantly for mode changes/glitch mode, debounce for text typing
    if (mode === "glitch" || !query) {
      executeSearch(query, scope, mode)
    } else {
      debounceTimer.current = setTimeout(() => {
        executeSearch(query, scope, mode)
      }, 350)
    }

    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current)
      }
    }
  }, [query, scope, mode, executeSearch])

  const handleResultClick = (match: SearchMatch) => {
    // If it's a message match, parse ID to number
    if (match.type === "message") {
      const msgId = parseInt(match.id, 10)
      if (!isNaN(msgId)) {
        onNavigateFromSearch(match.conversation_id, msgId)
      }
    } else if (match.type === "note" || match.type === "memory_node") {
      // Notes and memory nodes can navigate to conversation if they have a message reference
      // (For now we navigate to the conversation, or if we have msgId we can go there)
      // If we don't have msgId, we just switch to the conversation
      onNavigateFromSearch(match.conversation_id, 0)
    }
  }

  const formatTimestamp = (ts: string) => {
    if (!ts) return ""
    try {
      const date = new Date(ts)
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + " " + date.toLocaleDateString([], { month: 'short', day: 'numeric' })
    } catch {
      return ts
    }
  }

  const TYPE_META: Record<SearchMatch["type"], { label: string; badge: string; bar: string; dot: string }> = {
    message: {
      label: "message",
      badge: "bg-semantic-green/10 text-semantic-green border border-semantic-green/20",
      bar: "bg-semantic-green/60",
      dot: "bg-semantic-green",
    },
    note: {
      label: "note",
      badge: "bg-semantic-gold/10 text-semantic-gold border border-semantic-gold/20",
      bar: "bg-semantic-gold/60",
      dot: "bg-semantic-gold",
    },
    memory_node: {
      label: "memory",
      badge: "bg-semantic-blue/10 text-semantic-blue border border-semantic-blue/20",
      bar: "bg-semantic-blue/60",
      dot: "bg-semantic-blue",
    },
  }

  // Type counts (before filtering) so the filter chips can show totals
  const typeCounts = results.reduce(
    (acc, m) => {
      acc[m.type] = (acc[m.type] || 0) + 1
      return acc
    },
    {} as Record<string, number>,
  )

  // Filter by selected type, then sort messages to the top (preserving
  // the backend relevance/recency order within each group)
  const visibleResults = results
    .filter((m) => typeFilter === "all" || m.type === typeFilter)
    .map((m, i) => ({ m, i }))
    .sort((a, b) => {
      const rank = (t: SearchMatch["type"]) => (t === "message" ? 0 : 1)
      const byType = rank(a.m.type) - rank(b.m.type)
      return byType !== 0 ? byType : a.i - b.i
    })
    .map(({ m }) => m)

  return (
    <div className="flex flex-col h-full bg-[#0c0c0c] text-[#c8c8c8] font-mono">
      {/* Search inputs */}
      <div className="p-3 shrink-0 flex flex-col gap-2.5 border-b border-[#222]">
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={mode === "glitch" ? "Glitch salience mode active..." : "Query rhizomes..."}
            disabled={mode === "glitch"}
            className="w-full bg-[#141414] border border-[#333] rounded px-2.5 py-1.5 text-xs text-[#c8c8c8] placeholder-[#555] focus:outline-none focus:border-emerald-400 transition-colors"
          />
          {loading && (
            <div className="absolute right-2.5 top-2.5 flex items-center justify-center">
              <div className="w-3.5 h-3.5 border-2 border-emerald-400/20 border-t-emerald-400 rounded-full animate-spin"></div>
            </div>
          )}
        </div>

        {/* Search mode toggles */}
        <div className="flex flex-wrap gap-1 text-[10px]">
          {(["text", "semantic", "diffractive", "glitch"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-2 py-0.5 border border-[#333] rounded-sm transition-colors cursor-pointer capitalize ${
                mode === m ? "bg-emerald-400/10 text-emerald-400 border-emerald-400/30" : "bg-transparent text-[#666] hover:text-[#aaa]"
              }`}
            >
              {m === "diffractive" ? "Diffractive" : m === "semantic" ? "Semantic" : m === "glitch" ? "Glitch" : "Keyword"}
            </button>
          ))}
        </div>

        {/* Scope toggles */}
        <div className="flex gap-2 items-center text-[10px]">
          <span className="text-[#555] uppercase tracking-wider text-[9px]">Scope:</span>
          <button
            onClick={() => setScope("current")}
            disabled={!conversationId}
            className={`px-1.5 py-0.5 transition-colors cursor-pointer border border-transparent rounded-sm ${
              !conversationId ? "opacity-30 cursor-not-allowed" : ""
            } ${
              scope === "current" && conversationId ? "text-emerald-400 bg-[#161616]" : "text-[#555] hover:text-[#888]"
            }`}
          >
            [ Current Conversation ]
          </button>
          <button
            onClick={() => setScope("all")}
            className={`px-1.5 py-0.5 transition-colors cursor-pointer border border-transparent rounded-sm ${
              scope === "all" ? "text-emerald-400 bg-[#161616]" : "text-[#555] hover:text-[#888]"
            }`}
          >
            [ Global ]
          </button>
        </div>

        {/* Type filter toggles */}
        <div className="flex flex-wrap gap-1 items-center text-[10px]">
          <span className="text-ui-dim uppercase tracking-wider text-[9px] mr-0.5">Type:</span>
          {(["all", "message", "note", "memory_node"] as const).map((t) => {
            const active = typeFilter === t
            const count = t === "all" ? results.length : (typeCounts[t] || 0)
            const dot = t === "all" ? "" : TYPE_META[t].dot
            return (
              <button
                key={t}
                onClick={() => setTypeFilter(t)}
                className={`flex items-center gap-1 px-1.5 py-0.5 border rounded-sm transition-colors cursor-pointer capitalize ${
                  active ? "bg-[#161616] text-ui-primary border-[#444]" : "bg-transparent text-[#666] border-ui-border hover:text-ui-secondary"
                }`}
              >
                {dot && <span className={`w-1.5 h-1.5 rounded-full ${dot}`}></span>}
                {t === "memory_node" ? "memory" : t}
                <span className="text-ui-dim">{count}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Results Container */}
      <div className="flex-1 overflow-y-auto p-2 min-h-0">
        {error && (
          <div className="text-[10px] text-red-400 p-2 bg-red-400/5 border border-red-400/20 rounded">
            Error: {error}
          </div>
        )}

        {!loading && visibleResults.length === 0 && (
          <div className="flex flex-col items-center justify-center h-32 text-center text-[#444] text-[10px] select-none p-4">
            {results.length > 0
              ? "No results of this type."
              : mode === "glitch" ? "No salience metrics detected above thresholds." : "No nodes mapped to query."}
          </div>
        )}

        <div className="flex flex-col gap-2">
          {visibleResults.map((match) => {
            const meta = TYPE_META[match.type]
            return (
            <button
              key={`${match.type}-${match.id}`}
              onClick={() => handleResultClick(match)}
              className="w-full text-left bg-[#111] hover:bg-[#161616] border border-[#222] hover:border-emerald-400/20 rounded p-2.5 pl-3 transition-all group flex flex-col gap-1 cursor-pointer relative overflow-hidden"
            >
              <span className={`absolute left-0 top-0 bottom-0 w-0.5 ${meta.bar}`}></span>
              <div className="flex items-center justify-between gap-2">
                <span className={`text-[9px] uppercase font-bold tracking-wider px-1 py-0.5 rounded ${meta.badge}`}>
                  {meta.label}
                </span>
                <span className="text-[9px] text-[#555]">
                  {formatTimestamp(match.timestamp)}
                </span>
              </div>
              <div className="text-xs font-semibold text-[#aaa] group-hover:text-[#c8c8c8] transition-colors leading-tight">
                {match.title}
              </div>
              <div className="text-[11px] text-[#666] group-hover:text-[#888] transition-colors leading-normal line-clamp-2">
                {match.snippet}
              </div>
              {match.relevance_score > 0 && (
                <div className="text-[9px] text-emerald-400/50 group-hover:text-emerald-400/70 transition-colors mt-0.5">
                  Relevance: {match.relevance_score.toFixed(3)}
                </div>
              )}
            </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
export default SearchTab
