import { useState, useEffect } from "react"
import {
  getSpectralSuggestions,
  createResonanceLink,
  type SpectralSuggestion,
} from "../api/client"

interface SpectralEchoesProps {
  conversationId: string
  activeMessageId: number | null
  refreshTree: () => void
}

export function SpectralEchoes({
  conversationId,
  activeMessageId,
  refreshTree,
}: SpectralEchoesProps) {
  const [suggestions, setSuggestions] = useState<SpectralSuggestion[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Link justification input state
  const [linkingMsgId, setLinkingMsgId] = useState<number | null>(null)
  const [justification, setJustification] = useState("")
  const [isLinking, setIsLinking] = useState(false)

  const fetchSuggestions = async () => {
    if (!conversationId || !activeMessageId) {
      setSuggestions([])
      return
    }
    setLoading(true)
    setError(null)
    try {
      const data = await getSpectralSuggestions(conversationId, activeMessageId, 0.70)
      setSuggestions(data)
    } catch (err) {
      console.error("Failed to fetch spectral suggestions", err)
      setError("Failed to load spectral suggestions")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSuggestions()
    setLinkingMsgId(null)
    setJustification("")
  }, [conversationId, activeMessageId])

  const handleCreateLink = async (targetId: number) => {
    if (!activeMessageId || isLinking) return
    setIsLinking(true)
    try {
      await createResonanceLink(
        conversationId,
        activeMessageId,
        targetId,
        justification.trim() || "Manual resonance connection",
        "active"
      )
      refreshTree()
      fetchSuggestions()
      setLinkingMsgId(null)
      setJustification("")
    } catch (err) {
      console.error("Failed to create manual link", err)
      alert("Failed to create link")
    } finally {
      setIsLinking(false)
    }
  }

  const handleIgnoreLink = async (targetId: number) => {
    if (!activeMessageId || isLinking) return
    setIsLinking(true)
    try {
      await createResonanceLink(
        conversationId,
        activeMessageId,
        targetId,
        "Ignored by user",
        "ignored"
      )
      refreshTree()
      fetchSuggestions()
    } catch (err) {
      console.error("Failed to ignore suggestion", err)
      alert("Failed to ignore suggestion")
    } finally {
      setIsLinking(false)
    }
  }

  if (!activeMessageId) {
    return (
      <div className="text-[10px] font-mono text-[#4b4b5c] italic p-2 border border-[#14141a] rounded bg-[#07070a] select-none text-center">
        Select a node in the Connection Cloud to detect spectral echoes.
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2 p-2 border border-[#1b1b22] rounded-lg bg-[#07070a] font-mono">
      <div className="flex justify-between items-center border-b border-[#14141a] pb-1">
        <span className="text-[9px] font-bold text-[#a892ee] uppercase tracking-wider">
          Spectral Echoes (Parallel Similarity)
        </span>
        {loading && <span className="text-[9px] text-[#4b4b5c] animate-pulse">Scanning...</span>}
      </div>

      {error && <div className="text-[9px] text-red-400">{error}</div>}

      {!loading && suggestions.length === 0 && (
        <div className="text-[9px] text-[#4b4b5c] italic text-center py-2">
          No parallel echoes detected above 70% similarity.
        </div>
      )}

      <div className="flex flex-col gap-2 max-h-[200px] overflow-y-auto pr-1">
        {suggestions.map((sug) => {
          const isLinkingThis = linkingMsgId === sug.message_id
          const simPercent = (sug.similarity * 100).toFixed(0)

          return (
            <div
              key={sug.message_id}
              className="p-1.5 border border-[#14141a] rounded bg-[#0b0b0e] hover:border-[#1b1b22] transition-colors flex flex-col gap-1 text-[9px]"
            >
              <div className="flex justify-between items-center text-[8px]">
                <span className={sug.speaker === "human" ? "text-[#6bc28c]" : "text-[#a892ee]"}>
                  {sug.speaker === "human" ? "Human" : "Symbia"} (ID: {sug.message_id})
                </span>
                <span className="text-[#4ade80] font-bold">
                  {simPercent}% resonance
                </span>
              </div>

              <div className="text-[#a1a1b5] line-clamp-3 italic">
                "{sug.content}"
              </div>

              {isLinkingThis ? (
                <div className="flex flex-col gap-1 mt-1 border-t border-[#14141a] pt-1.5">
                  <input
                    type="text"
                    value={justification}
                    onChange={(e) => setJustification(e.target.value)}
                    placeholder="justification (optional)..."
                    className="w-full bg-[#07070a] border border-[#1b1b21] rounded p-1 text-[8px] text-white focus:outline-none focus:border-[#a892ee]"
                  />
                  <div className="flex gap-1.5 justify-end">
                    <button
                      onClick={() => setLinkingMsgId(null)}
                      className="px-1.5 py-0.5 rounded text-[8px] bg-[#14141a] text-[#79798c] hover:text-white cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => handleCreateLink(sug.message_id)}
                      disabled={isLinking}
                      className="px-1.5 py-0.5 rounded text-[8px] bg-[#a892ee] hover:bg-[#9079d6] text-black font-bold cursor-pointer"
                    >
                      {isLinking ? "Linking..." : "Confirm Link"}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex gap-1.5 mt-0.5">
                  <button
                    onClick={() => {
                      setLinkingMsgId(sug.message_id)
                      setJustification("")
                    }}
                    className="flex-1 py-0.5 text-center bg-[#14141a] border border-[#1e1e26] hover:border-[#a892ee] hover:text-[#a892ee] text-[#79798c] rounded transition-all cursor-pointer select-none"
                  >
                    Link Node
                  </button>
                  <button
                    onClick={() => handleIgnoreLink(sug.message_id)}
                    disabled={isLinking}
                    className="px-2.5 py-0.5 text-center bg-[#14141a] border border-[#1e1e26] hover:border-[#ef4444] hover:text-[#ef4444] text-[#79798c] rounded transition-all cursor-pointer select-none"
                    title="Ignore this suggestion permanently"
                  >
                    Ignore
                  </button>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
