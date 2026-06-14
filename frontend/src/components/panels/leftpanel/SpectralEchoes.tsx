import { useState, useEffect, memo } from "react"
import {
  getSpectralSuggestions,
  createResonanceLink,
  type SpectralSuggestion,
} from "../../../api/client"

interface SpectralEchoesProps {
  conversationId: string
  activeMessageId: number | null
  refreshTree: () => void
}

function SpectralEchoesComponent({
  conversationId,
  activeMessageId,
  refreshTree,
}: SpectralEchoesProps) {
  const [suggestions, setSuggestions] = useState<SpectralSuggestion[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
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
        conversationId, activeMessageId, targetId,
        justification.trim() || "Manual resonance connection", "active"
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
        conversationId, activeMessageId, targetId,
        "Ignored by user", "ignored"
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
      <div className="text-[10px] font-mono text-[#555] italic p-2 select-none text-center">
        Select a node in the Connection Cloud to detect spectral echoes.
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2 p-2 font-mono">
      <div className="flex justify-between items-center">
        <span className="text-[9px] font-bold text-[#6c6c8a] uppercase tracking-wider">
          Spectral Echoes
        </span>
        {loading && <span className="text-[9px] text-[#555] animate-pulse">scanning...</span>}
      </div>

      {error && <div className="text-[9px] text-[#ef4444]">{error}</div>}

      {!loading && suggestions.length === 0 && (
        <div className="text-[9px] text-[#555] italic text-center py-2">
          No parallel echoes detected above 70% similarity.
        </div>
      )}

      <div className="flex flex-col gap-2 max-h-[200px] overflow-y-auto pr-1">
        {suggestions.map((sug) => {
          const isLinkingThis = linkingMsgId === sug.message_id
          const simPercent = (sug.similarity * 100).toFixed(0)

          return (
            <div key={sug.message_id} className="flex flex-col gap-1 text-[9px]">
              <div className="flex justify-between items-center text-[8px]">
                <span className={sug.speaker === "human" ? "text-[#6bc28c]" : "text-[#a892ee]"}>
                  {sug.speaker === "human" ? "Human" : "Symbia"} (ID: {sug.message_id})
                </span>
                <span className="text-[#4ade80] font-bold">{simPercent}%</span>
              </div>

              <div className="text-[#94a3b8] line-clamp-3 italic">
                "{sug.content}"
              </div>

              {isLinkingThis ? (
                <div className="flex flex-col gap-1 pt-1">
                  <input
                    type="text"
                    value={justification}
                    onChange={(e) => setJustification(e.target.value)}
                    placeholder="justification (optional)..."
                    className="w-full bg-transparent border-b border-[#222]/40 text-[#ccc] text-[8px] focus:outline-none focus:border-[#a892ee] font-mono"
                  />
                  <div className="flex gap-2">
                    <button onClick={() => setLinkingMsgId(null)}
                      className="text-[8px] text-[#666] hover:text-[#888] cursor-pointer select-none font-mono">[cancel]</button>
                    <button onClick={() => handleCreateLink(sug.message_id)} disabled={isLinking}
                      className="text-[8px] text-[#a78bfa] hover:text-[#c084fc] disabled:text-[#555] cursor-pointer select-none font-mono">
                      {isLinking ? "[linking...]" : "[confirm link]"}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex gap-2">
                  <button onClick={() => { setLinkingMsgId(sug.message_id); setJustification("") }}
                    className="text-[8px] text-[#666] hover:text-[#a78bfa] cursor-pointer select-none font-mono">[link]</button>
                  <button onClick={() => handleIgnoreLink(sug.message_id)} disabled={isLinking}
                    className="text-[8px] text-[#666] hover:text-[#ef4444] cursor-pointer select-none font-mono">[ignore]</button>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export const SpectralEchoes = memo(SpectralEchoesComponent)
