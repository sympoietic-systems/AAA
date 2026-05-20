import { useCallback, useEffect, useRef, useState } from "react"
import { getAgent, getHistory, sendMessage } from "../api/client"
import type { ChatMessage } from "../api/client"

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [agentName, setAgentName] = useState("...")
  const loaded = useRef(false)

  useEffect(() => {
    if (loaded.current) return
    loaded.current = true
    getAgent()
      .then((info) => setAgentName(info.name))
      .catch(() => setAgentName("agent"))
    getHistory()
      .then((data) => setMessages(data.messages))
      .catch(() => {})
  }, [])

  const send = useCallback(async (content: string) => {
    if (!content.trim() || loading) return
    setError(null)
    setLoading(true)

    const userMsg: ChatMessage = {
      id: Date.now(),
      timestamp: new Date().toISOString(),
      speaker: "human",
      content,
    }
    setMessages((prev) => [...prev, userMsg])

    try {
      const response = await sendMessage(content)
      setMessages((prev) => {
        const updated = [...prev]
        if (response.metrics) {
          for (let i = updated.length - 1; i >= 0; i--) {
            if (updated[i].speaker === "human") {
              updated[i] = { ...updated[i], metrics: response.metrics }
              break
            }
          }
        }
        updated.push(response)
        return updated
      })
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to send message"
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [loading])

  const clearError = useCallback(() => setError(null), [])

  return { messages, loading, error, send, clearError, agentName }
}
