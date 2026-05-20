import { useChat } from "./hooks/useChat"
import { ChatView } from "./components/ChatView"

export default function App() {
  const { messages, loading, error, send, clearError, agentName } = useChat()

  return (
    <ChatView
      messages={messages}
      loading={loading}
      error={error}
      agentName={agentName}
      onSend={send}
      onClearError={clearError}
    />
  )
}
