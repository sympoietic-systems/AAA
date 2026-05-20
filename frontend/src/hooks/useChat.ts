import { useCallback, useEffect, useRef, useState } from "react"
import { getHistory, sendMessage } from "../api/client"
import type { ChatMessage } from "../api/client"

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const loaded = useRef(false)

  useEffect(() => {
    if (loaded.current) return
    loaded.current = true
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
      setMessages((prev) => [...prev, response])
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to send message"
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [loading])

  const clearError = useCallback(() => setError(null), [])

  return { messages, loading, error, send, clearError }
}
