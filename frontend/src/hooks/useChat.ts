import { useCallback, useEffect, useRef, useState } from "react"
import { getAgent, getHistory, sendMessage } from "../api/client"
import type { ChatMessage } from "../api/client"

export function useChat(conversationId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [agentName, setAgentName] = useState("...")
  const loadedRef = useRef<string>("")

  useEffect(() => {
    if (loadedRef.current === conversationId) return
    loadedRef.current = conversationId

    getAgent()
      .then((info) => setAgentName(info.name))
      .catch(() => setAgentName("agent"))

    if (conversationId) {
      getHistory(50, conversationId)
        .then((data) => setMessages(data.messages))
        .catch(() => setMessages([]))
    } else {
      setMessages([])
    }
  }, [conversationId])

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
      const response = await sendMessage(content, conversationId || undefined)
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
      return response
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to send message"
      setError(msg)
      return null
    } finally {
      setLoading(false)
    }
  }, [loading, conversationId])

  const clearError = useCallback(() => setError(null), [])

  return { messages, loading, error, send, clearError, agentName }
}
