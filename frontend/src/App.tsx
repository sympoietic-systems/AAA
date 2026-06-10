import { useState, useRef, useEffect } from "react"
import { useChat } from "./hooks/useChat"
import { useConversations } from "./hooks/useConversations"
import { useNotes } from "./hooks/useNotes"
import { ChatView } from "./components/ChatView"
import { ConversationList } from "./components/ConversationList"
import { SidePanel } from "./components/SidePanel"
import { checkAuthStatus, verifyPassword, logout, addConversationTag, removeConversationTag } from "./api/client"

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null)
  const [isAuthEnabled, setIsAuthEnabled] = useState<boolean>(false)
  const [authError, setAuthError] = useState<string | null>(null)

  useEffect(() => {
    checkAuthStatus().then((status) => {
      setIsAuthenticated(status.authenticated)
      setIsAuthEnabled(status.authEnabled)
    })
  }, [])

  const handlePasswordSubmit = async (password: string) => {
    setAuthError(null)
    const success = await verifyPassword(password)
    if (success) {
      localStorage.setItem("aaa_password", password)
      setIsAuthenticated(true)
      window.location.reload()
    } else {
      setAuthError("Incorrect password")
    }
  }

  const handleLogout = () => {
    logout()
    setIsAuthenticated(false)
    window.location.reload()
  }

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

  const {
    messages,
    fullTreeMessages,
    links,
    activeMessageId,
    setActiveMessageId,
    activePathIds,
    commitProposedBranch,
    loading,
    error,
    send,
    clearError,
    agentName,
    uploadedFiles,
    isIndexing,
    upload,
    deleteFile,
    reprocess,
    hasMore,
    loadingMore,
    loadMoreMessages,
    refreshMessages,
  } = useChat(activeId)

  const {
    notes,
    addNote,
    editNote,
    removeNote,
  } = useNotes(activeId || "")

  const handleAddNote = async (
    messageId: number,
    selectedText: string,
    comment: string,
    visibility: "personal" | "shared",
    startOffset?: number
  ) => {
    const res = await addNote(messageId, selectedText, comment, visibility, startOffset)
    if (res) {
      refreshMessages()
    }
  }

  const handleDeleteNote = async (noteId: string) => {
    await removeNote(noteId)
    refreshMessages()
  }

  const handleUpdateNote = async (noteId: string, comment?: string, visibility?: "personal" | "shared") => {
    await editNote(noteId, comment, visibility)
    refreshMessages()
  }

  const [convCollapsed, setConvCollapsed] = useState(true)

  const [leftPanelWidth, setLeftPanelWidth] = useState(() => {
    const saved = localStorage.getItem("aaa_leftPanelWidth")
    return saved ? parseInt(saved, 10) : 288
  })
  const widthRef = useRef(leftPanelWidth)
  widthRef.current = leftPanelWidth

  const handleResizeStart = (e: React.MouseEvent) => {
    e.preventDefault()
    const startX = e.clientX
    const startWidth = leftPanelWidth
    document.body.style.cursor = "col-resize"
    document.body.style.userSelect = "none"

    const onMove = (ev: MouseEvent) => {
      const w = Math.max(200, Math.min(500, startWidth + ev.clientX - startX))
      widthRef.current = w
      setLeftPanelWidth(w)
    }
    const onUp = () => {
      localStorage.setItem("aaa_leftPanelWidth", String(widthRef.current))
      document.removeEventListener("mousemove", onMove)
      document.removeEventListener("mouseup", onUp)
      document.body.style.cursor = ""
      document.body.style.userSelect = ""
    }
    document.addEventListener("mousemove", onMove)
    document.addEventListener("mouseup", onUp)
  }

  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(true)

  const [rightPanelWidth, setRightPanelWidth] = useState(() => {
    const saved = localStorage.getItem("aaa_rightPanelWidth")
    return saved ? parseInt(saved, 10) : 320
  })
  const rightWidthRef = useRef(rightPanelWidth)
  rightWidthRef.current = rightPanelWidth

  const handleRightResizeStart = (e: React.MouseEvent) => {
    e.preventDefault()
    const startX = e.clientX
    const startWidth = rightPanelWidth
    document.body.style.cursor = "col-resize"
    document.body.style.userSelect = "none"

    const onMove = (ev: MouseEvent) => {
      const maxW = Math.floor(window.innerWidth * 0.5)
      const w = Math.max(200, Math.min(maxW, startWidth - (ev.clientX - startX)))
      rightWidthRef.current = w
      setRightPanelWidth(w)
    }
    const onUp = () => {
      localStorage.setItem("aaa_rightPanelWidth", String(rightWidthRef.current))
      document.removeEventListener("mousemove", onMove)
      document.removeEventListener("mouseup", onUp)
      document.body.style.cursor = ""
      document.body.style.userSelect = ""
    }
    document.addEventListener("mousemove", onMove)
    document.addEventListener("mouseup", onUp)
  }

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

  const handleAddTag = async (tag: string) => {
    if (activeId) {
      try {
        await addConversationTag(activeId, tag)
        refresh()
      } catch (err) {
        console.error("Failed to add tag:", err)
      }
    }
  }

  const handleRemoveTag = async (tag: string) => {
    if (activeId) {
      try {
        await removeConversationTag(activeId, tag)
        refresh()
      } catch (err) {
        console.error("Failed to remove tag:", err)
      }
    }
  }

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
        // Auto-generate title when conversation reaches 3+ messages if still untitled
        const conv = conversations.find((c) => c.id === currentActiveId)
        if (conv && !conv.title.trim() && conv.message_count >= 2) {
          setTimeout(() => generateTitle(currentActiveId), 3000)
        }
      }
    }
  }

  const handleUploadFiles = async (files: File[]) => {
    const currentActiveId = activeIdRef.current
    const newId = await upload(files)
    if (newId && !currentActiveId) {
      setActiveId(newId)
      const firstFilename = files[0].name
      const titleBase = firstFilename.substring(0, firstFilename.lastIndexOf('.')) || firstFilename
      addConversation({
        id: newId,
        title: `File trace: ${titleBase.substring(0, 50)}`,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        message_count: 0,
      })
      setTimeout(() => refreshTitle(newId), 3000)
    } else {
      refresh()
    }
  }

  if (isAuthenticated === null) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#0c0c0c] text-sm font-mono text-[#555] select-none">
        <span className="animate-pulse">initializing system...</span>
      </div>
    )
  }

  if (isAuthEnabled && !isAuthenticated) {
    return (
      <div className="flex flex-col md:flex-row h-screen bg-[#0c0c0c]">
        <ConversationList
          conversations={[]}
          activeId=""
          loading={false}
          onSelect={() => {}}
          onDelete={() => {}}
          onNew={() => {}}
          collapsed={convCollapsed}
          onToggle={() => setConvCollapsed(!convCollapsed)}
          showLogout={false}
          width={leftPanelWidth}
        />
        <ChatView
          messages={[]}
          loading={false}
          error={authError}
          agentName="..."
          conversationId=""
          conversationTitle=""
          uploadedFiles={[]}
          onSend={handlePasswordSubmit}
          onUploadFiles={() => {}}
          isIndexing={false}
          onClearError={() => setAuthError(null)}
          onRenameTitle={() => {}}
          onGenerateTitle={async () => {}}
          isPassword={true}
          className="flex-1 min-w-0"
        />
      </div>
    )
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
        showLogout={isAuthEnabled}
        onLogout={handleLogout}
        width={leftPanelWidth}
      />
      {!convCollapsed && (
        <div
          onMouseDown={handleResizeStart}
          className="w-1 cursor-col-resize hover:bg-[#4ade80]/30 active:bg-[#4ade80]/50 transition-colors shrink-0 hidden md:block"
        />
      )}
      <ChatView
        messages={messages}
        loading={loading}
        error={error}
        agentName={agentName}
        conversationId={conversationId}
        conversationTitle={conversationTitle}
        uploadedFiles={uploadedFiles}
        onSend={handleSend}
        onUploadFiles={handleUploadFiles}
        isIndexing={isIndexing}
        onClearError={clearError}
        onRenameTitle={handleRenameTitle}
        onGenerateTitle={handleGenerateTitle}
        hasMore={hasMore}
        loadingMore={loadingMore}
        onLoadMore={loadMoreMessages}
        notes={notes}
        onAddNote={handleAddNote}
        onDeleteNote={handleDeleteNote}
        onUpdateNote={handleUpdateNote}
        tags={activeConv?.tags || []}
        onAddTag={handleAddTag}
        onRemoveTag={handleRemoveTag}
        onBranch={setActiveMessageId}
        className="flex-1 min-w-0"
      />
      {!rightPanelCollapsed && (
        <div
          onMouseDown={handleRightResizeStart}
          className="w-1 cursor-col-resize hover:bg-[#4ade80]/30 active:bg-[#4ade80]/50 transition-colors shrink-0 hidden md:block"
        />
      )}
      <SidePanel
        uploadedFiles={uploadedFiles}
        conversationId={conversationId}
        onDeleteFile={deleteFile}
        onReprocessFile={reprocess}
        messageCount={messages.length}
        notes={notes}
        onDeleteNote={handleDeleteNote}
        onUpdateNote={handleUpdateNote}
        summary={activeConv?.summary}
        humanSummary={activeConv?.human_summary}
        width={rightPanelWidth}
        panelCollapsed={rightPanelCollapsed}
        onPanelToggle={() => setRightPanelCollapsed(p => !p)}
        fullTreeMessages={fullTreeMessages}
        links={links}
        activeMessageId={activeMessageId}
        activePathIds={activePathIds}
        setActiveMessageId={setActiveMessageId}
        commitProposedBranch={commitProposedBranch}
      />
    </div>
  )
}
