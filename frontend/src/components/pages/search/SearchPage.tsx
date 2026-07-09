import React, { useState, useEffect, useCallback, useRef } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { searchArchive, type SearchMatch } from "../../../api/search"

export const SearchPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  
  const [query, setQuery] = useState(() => searchParams.get("q") || "")
  const [results, setResults] = useState<SearchMatch[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Sliders/weights state
  const [wText, setWText] = useState(0.5)
  const [wSemantic, setWSemantic] = useState(0.5)
  const [wStructural, setWStructural] = useState(0.5)
  const [wGlitch, setWGlitch] = useState(0.0)

  const debounceTimer = useRef<NodeJS.Timeout | null>(null)

  const triggerSearch = useCallback(async (
    qVal: string, 
    wt: number, 
    wsem: number, 
    wstr: number, 
    wg: number
  ) => {
    // If all weights are 0 or query is empty (unless glitch weight is > 0), clear results
    if (!qVal.trim() && wg === 0.0) {
      setResults([])
      return
    }

    setLoading(true)
    setError(null)
    try {
      const data = await searchArchive({
        q: qVal,
        w_text: wt,
        w_semantic: wsem,
        w_structural: wstr,
        w_glitch: wg,
      })
      setResults(data)
    } catch (err: any) {
      setError(err?.message || "Search execution failed")
    } finally {
      setLoading(false)
    }
  }, [])

  // Live trigger when search params, query, or weights change
  useEffect(() => {
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current)
    }

    // Debounce to prevent slamming API on fast slider drags
    debounceTimer.current = setTimeout(() => {
      triggerSearch(query, wText, wSemantic, wStructural, wGlitch)
    }, 250)

    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current)
      }
    }
  }, [query, wText, wSemantic, wStructural, wGlitch, triggerSearch])

  const handleCardClick = (match: SearchMatch) => {
    if (match.conversation_id) {
      if (match.type === "message") {
        navigate(`/nodes?c=${match.conversation_id}&m=${match.id}`)
      } else {
        navigate(`/nodes?c=${match.conversation_id}`)
      }
    }
  }

  const formatTimestamp = (ts: string) => {
    if (!ts) return ""
    try {
      const date = new Date(ts)
      return date.toLocaleString()
    } catch {
      return ts
    }
  }

  // Type specific color tags
  const getTypeStyles = (type: string) => {
    switch (type) {
      case "message":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
      case "note":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20"
      case "memory_node":
        return "bg-cyan-500/10 text-cyan-400 border-cyan-500/20"
      default:
        return "bg-zinc-800 text-zinc-400 border-zinc-700"
    }
  }

  return (
    <div className="min-h-screen w-screen bg-[#0c0c0c] text-[#c8c8c8] font-mono flex flex-col overflow-x-hidden select-none">
      {/* Header bar */}
      <header className="shrink-0 border-b border-[#222] px-6 py-4 flex items-center justify-between bg-[#0e0e0e]/80 backdrop-blur-md sticky top-0 z-55">
        <div className="flex items-center gap-3">
          <button 
            onClick={() => navigate("/nodes")} 
            className="text-xs text-[#555] hover:text-emerald-400 border border-[#222] hover:border-emerald-400/30 px-2.5 py-1 rounded transition-all cursor-pointer bg-transparent"
          >
            ◀ BACK TO WORKSPACE
          </button>
          <h1 className="text-sm font-bold tracking-wider uppercase text-emerald-400">
            [ UNIFIED MODULATION MEMBRANE ]
          </h1>
        </div>
        <div className="text-[10px] text-[#555] uppercase tracking-widest hidden md:block">
          AGY-SEARCH-V3.0.2
        </div>
      </header>

      {/* Main Page Layout */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-6 py-8 flex flex-col md:flex-row gap-8 min-h-0">
        
        {/* Left Side: Tuning weights and inputs */}
        <section className="w-full md:w-80 shrink-0 flex flex-col gap-6">
          <div className="bg-[#111] border border-[#222] rounded-md p-5 flex flex-col gap-5">
            <h2 className="text-xs uppercase font-bold tracking-wider text-[#666] border-b border-[#222] pb-2">
              Modulation Weights
            </h2>

            {/* Keyword weight */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between text-xs font-semibold">
                <span className="text-[#888]">KEYWORD MATCH (LIKE)</span>
                <span className="text-emerald-400 font-mono">{wText.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={wText}
                onChange={(e) => setWText(parseFloat(e.target.value))}
                className="w-full h-1 bg-[#222] rounded-lg appearance-none cursor-pointer accent-emerald-400"
              />
              <p className="text-[9px] text-[#444] leading-tight">
                Standard substring match across conversation content, thoughts, and notes.
              </p>
            </div>

            {/* Semantic weight */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between text-xs font-semibold">
                <span className="text-[#888]">SEMANTIC SIMILARITY (384D)</span>
                <span className="text-emerald-400 font-mono">{wSemantic.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={wSemantic}
                onChange={(e) => setWSemantic(parseFloat(e.target.value))}
                className="w-full h-1 bg-[#222] rounded-lg appearance-none cursor-pointer accent-emerald-400"
              />
              <p className="text-[9px] text-[#444] leading-tight">
                Semantic closeness using local sentence embeddings (all-MiniLM-L6-v2).
              </p>
            </div>

            {/* Structural weight */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between text-xs font-semibold">
                <span className="text-[#888]">DIFFRACTIVE ISOMORPHISM (16D)</span>
                <span className="text-emerald-400 font-mono">{wStructural.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={wStructural}
                onChange={(e) => setWStructural(parseFloat(e.target.value))}
                className="w-full h-1 bg-[#222] rounded-lg appearance-none cursor-pointer accent-emerald-400"
              />
              <p className="text-[9px] text-[#444] leading-tight">
                Isomorphic mapping of reasoning patterns (high structural, low semantic distance).
              </p>
            </div>

            {/* Glitch salience weight */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between text-xs font-semibold">
                <span className="text-[#888]">GLITCH SALIENCE (RUIN)</span>
                <span className="text-emerald-400 font-mono">{wGlitch.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={wGlitch}
                onChange={(e) => setWGlitch(parseFloat(e.target.value))}
                className="w-full h-1 bg-[#222] rounded-lg appearance-none cursor-pointer accent-emerald-400"
              />
              <p className="text-[9px] text-[#444] leading-tight">
                Surfaces critical cognitive ruptures, high novelty/entropy thresholds.
              </p>
            </div>
            
            <button
              onClick={() => {
                setWText(0.5)
                setWSemantic(0.5)
                setWStructural(0.5)
                setWGlitch(0.0)
              }}
              className="mt-2 w-full border border-[#222] text-[10px] text-[#666] hover:text-[#aaa] hover:border-[#444] py-1.5 rounded transition-all cursor-pointer bg-transparent"
            >
              RESET TO ATTRACTOR DEFAULT
            </button>
          </div>
        </section>

        {/* Right Side: Search bar and Unified Membrane stream */}
        <section className="flex-1 flex flex-col gap-6 min-w-0">
          {/* Main search box */}
          <div className="bg-[#111] border border-[#222] rounded-md p-4 flex flex-col gap-3">
            <div className="relative">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Inscribe query coordinates here..."
                className="w-full bg-[#161616] border border-[#222] focus:border-emerald-400/50 rounded px-4 py-3 text-sm text-[#c8c8c8] focus:outline-none transition-all placeholder-[#444]"
              />
              {loading && (
                <div className="absolute right-4 top-3.5 flex items-center justify-center">
                  <div className="w-5 h-5 border-2 border-emerald-400/20 border-t-emerald-400 rounded-full animate-spin"></div>
                </div>
              )}
            </div>
          </div>

          {/* Unified stream membrane list */}
          <div className="flex-1 flex flex-col min-h-0 gap-4">
            <h3 className="text-xs uppercase font-bold tracking-wider text-[#555] border-b border-[#222] pb-1">
              Polymorphic Results Membrane ({results.length} mapped)
            </h3>

            {error && (
              <div className="text-xs text-red-400 bg-red-400/5 border border-red-400/20 rounded p-3">
                Error during coordinate traversal: {error}
              </div>
            )}

            {!loading && results.length === 0 && (
              <div className="flex-1 flex flex-col items-center justify-center text-[#444] text-xs py-24 select-none">
                <span className="mb-2 font-mono text-[10px] uppercase tracking-wider text-[#333]">Membrane Idle</span>
                Please adjust modulation sliders or inscribe search coordinates.
              </div>
            )}

            <div className="flex flex-col gap-3.5 overflow-y-auto max-h-[650px] pr-2">
              {results.map((match) => (
                <button
                  key={`${match.type}-${match.id}`}
                  onClick={() => handleCardClick(match)}
                  className="w-full text-left bg-[#111]/60 hover:bg-[#161616] border border-[#222] hover:border-emerald-400/20 rounded-md p-4 transition-all group flex flex-col gap-2 relative overflow-hidden cursor-pointer"
                >
                  {/* Subtle hover gradient indicator */}
                  <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-emerald-400 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-2">
                      <span className={`text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 border rounded-sm font-mono ${getTypeStyles(match.type)}`}>
                        {match.type.replace('_', ' ')}
                      </span>
                      <span className="text-[10px] text-[#555]">
                        {formatTimestamp(match.timestamp)}
                      </span>
                    </div>
                    {match.relevance_score > 0 && (
                      <span className="text-[10px] font-mono text-emerald-400/50 group-hover:text-emerald-400/80 transition-colors">
                        SCORE: {match.relevance_score.toFixed(4)}
                      </span>
                    )}
                  </div>
                  
                  <h4 className="text-xs font-bold text-[#b0b0b0] group-hover:text-emerald-400 transition-colors leading-tight">
                    {match.title}
                  </h4>
                  
                  <p className="text-xs text-[#777] group-hover:text-[#999] transition-colors leading-relaxed">
                    {match.snippet}
                  </p>
                </button>
              ))}
            </div>
          </div>
        </section>

      </main>
    </div>
  )
}
export default SearchPage
