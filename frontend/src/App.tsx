import { useChat } from "./hooks/useChat"
import { ChatView } from "./components/ChatView"

export default function App() {
  const { messages, loading, error, send, clearError } = useChat()

  return (
    <ChatView
      messages={messages}
      loading={loading}
      error={error}
      onSend={send}
      onClearError={clearError}
    />
  )
}
