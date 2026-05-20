import { useState, useRef } from "react"
import { useChat } from "./hooks/useChat"
import { useConversations } from "./hooks/useConversations"
import { ChatView } from "./components/ChatView"
import { ConversationList } from "./components/ConversationList"
import { SidePanel } from "./components/SidePanel"

export default function App() {
  const {
    conversations,
    activeId,
    setActiveId,
    loading: convLoading,
    refresh,
    deleteConversation,
    addConversation,
    refreshTitle,
  } = useConversations()

  const { messages, loading, error, send, clearError, agentName } = useChat(activeId)
  const [convCollapsed, setConvCollapsed] = useState(true)
  const activeIdRef = useRef(activeId)
  activeIdRef.current = activeId

  const handleSend = async (content: string) => {
    const currentActiveId = activeIdRef.current
    const response = await send(content)

    if (response && response.conversation_id) {
      if (!currentActiveId) {
        setActiveId(response.conversation_id)
        addConversation({
          id: response.conversation_id,
          title: "",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          message_count: 2,
        })
        setTimeout(() => refreshTitle(response.conversation_id!), 2000)
      } else {
        refresh()
      }
    }
  }

  return (
    <div className="flex flex-col md:flex-row h-screen bg-[#0c0c0c]">
      <ConversationList
        conversations={conversations}
        activeId={activeId}
        loading={convLoading}
        onSelect={(id) => setActiveId(id)}
        onDelete={deleteConversation}
        collapsed={convCollapsed}
        onToggle={() => setConvCollapsed(!convCollapsed)}
      />
      <ChatView
        messages={messages}
        loading={loading}
        error={error}
        agentName={agentName}
        onSend={handleSend}
        onClearError={clearError}
        className="flex-1 min-w-0"
      />
      <SidePanel />
    </div>
  )
}
