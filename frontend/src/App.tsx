import { useChat } from "./hooks/useChat"
import { ChatView } from "./components/ChatView"
import { SidePanel } from "./components/SidePanel"

export default function App() {
  const { messages, loading, error, send, clearError, agentName } = useChat()

  return (
    <div className="flex flex-col md:flex-row h-screen bg-[#0c0c0c]">
      <ChatView
        messages={messages}
        loading={loading}
        error={error}
        agentName={agentName}
        onSend={send}
        onClearError={clearError}
        className="flex-1 min-w-0"
      />
      <SidePanel />
    </div>
  )
}
