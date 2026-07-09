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
      </div>

      {/* Results Container */}
      <div className="flex-1 overflow-y-auto p-2 min-h-0">
        {error && (
          <div className="text-[10px] text-red-400 p-2 bg-red-400/5 border border-red-400/20 rounded">
            Error: {error}
          </div>
        )}

        {!loading && results.length === 0 && (
          <div className="flex flex-col items-center justify-center h-32 text-center text-[#444] text-[10px] select-none p-4">
            {mode === "glitch" ? "No salience metrics detected above thresholds." : "No nodes mapped to query."}
          </div>
        )}

        <div className="flex flex-col gap-2">
          {results.map((match) => (
            <button
              key={`${match.type}-${match.id}`}
              onClick={() => handleResultClick(match)}
              className="w-full text-left bg-[#111] hover:bg-[#161616] border border-[#222] hover:border-emerald-400/20 rounded p-2.5 transition-all group flex flex-col gap-1 cursor-pointer"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-[9px] uppercase font-bold tracking-wider px-1 py-0.5 rounded bg-[#1c1c1c] text-[#777] group-hover:text-emerald-400/80 transition-colors">
                  {match.type.replace('_', ' ')}
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
          ))}
        </div>
      </div>
    </div>
  )
}
export default SearchTab
