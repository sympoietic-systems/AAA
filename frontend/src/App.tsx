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
    newConversation,
    refreshTitle,
    renameConversation,
    generateTitle,
  } = useConversations()

  const { messages, loading, error, send, clearError, agentName, uploadedFiles } = useChat(activeId)
  const [convCollapsed, setConvCollapsed] = useState(true)
  const activeIdRef = useRef(activeId)
  activeIdRef.current = activeId

  const activeConv = conversations.find((c) => c.id === activeId)
  const conversationTitle = activeConv?.title || ""
  const conversationId = activeId

  const handleRenameTitle = (title: string) => {
    if (activeId) renameConversation(activeId, title)
  }

  const handleGenerateTitle = async () => {
    if (activeId) await generateTitle(activeId)
  }

  const handleSend = async (content: string, files?: File[]) => {
    const currentActiveId = activeIdRef.current
    const response = await send(content, files)

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
        // Auto-generate title when conversation reaches 3+ messages if still untitled
        const conv = conversations.find((c) => c.id === currentActiveId)
        if (conv && !conv.title.trim() && conv.message_count >= 2) {
          setTimeout(() => generateTitle(currentActiveId), 3000)
        }
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
        onNew={newConversation}
        collapsed={convCollapsed}
        onToggle={() => setConvCollapsed(!convCollapsed)}
      />
      <ChatView
        messages={messages}
        loading={loading}
        error={error}
        agentName={agentName}
        conversationId={conversationId}
        conversationTitle={conversationTitle}
        uploadedFiles={uploadedFiles}
        onSend={handleSend}
        onClearError={clearError}
        onRenameTitle={handleRenameTitle}
        onGenerateTitle={handleGenerateTitle}
        className="flex-1 min-w-0"
      />
      <SidePanel uploadedFiles={uploadedFiles} conversationId={conversationId} />
    </div>
  )
}
