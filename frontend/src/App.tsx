import { useState, useRef, useEffect } from "react"
import { useChat } from "./hooks/useChat"
import { useConversations } from "./hooks/useConversations"
import { useNotes } from "./hooks/useNotes"
import { ChatView } from "./components/ChatView"
import { SidePanel } from "./components/SidePanel"
import { ConversationLandingPage } from "./components/ConversationLandingPage"
import { AgentPage } from "./components/AgentPage"
import ConnectionCloud from "./components/ConnectionCloud"
import { SpectralEchoes } from "./components/SpectralEchoes"
import { checkAuthStatus, verifyPassword, logout, addConversationTag, removeConversationTag } from "./api/client"

export default function App() {
  // Render agent page standalone if navigated to /agent
  if (window.location.pathname === "/agent") {
    return <AgentPage onGoHome={() => window.close()} />
  }

  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null)
  const [isAuthEnabled, setIsAuthEnabled] = useState<boolean>(false)
  const [authError, setAuthError] = useState<string | null>(null)

  // Track if we are in clean/new chat creation workspace mode
  const [isNewChatMode, setIsNewChatMode] = useState(false)

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
    loadingMore: convLoadingMore,
    hasMore: convHasMore,
    totalCount: convTotalCount,
    loadMore: loadMoreConvs,
    refresh: refreshConvs,
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
    activeMessageId,
    setActiveMessageId,
    activePathIds,
    commitProposedBranch,
    navigateToMessage,
    loading,
    error,
    send,
    regenerate,
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
    refreshTree,
  } = useChat(activeId)

  const {
    notes,
    addNote,
    editNote,
    removeNote,
    refreshNotes,
  } = useNotes(activeId || "")

  const handleAddNote = async (
    messageId: number,
    selectedText: string,
    comment: string,
    visibility: "personal" | "shared" | "agent",
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

  const handleUpdateNote = async (noteId: string, comment?: string, visibility?: "personal" | "shared" | "agent") => {
    await editNote(noteId, comment, visibility)
    refreshMessages()
  }

  // Collapsible and resizable left panel state (for Connection Cloud DAG)
  const [leftPanelCollapsed, setLeftPanelCollapsed] = useState(false)
  const [leftPanelWidth, setLeftPanelWidth] = useState(() => {
    const saved = localStorage.getItem("aaa_leftPanelWidth")
    return saved ? parseInt(saved, 10) : 320
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
      const maxLeft = Math.floor(window.innerWidth * 0.5)
      const w = Math.max(200, Math.min(maxLeft, startWidth + ev.clientX - startX))
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

  // Collapsible and resizable right panel state (for SidePanel information)
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
      const maxRight = Math.floor(window.innerWidth * 0.3)
      const minChat = Math.floor(window.innerWidth * 0.3)
      // Right panel can't push chat below its minimum
      const maxAllowed = Math.min(maxRight, window.innerWidth - leftPanelWidth - minChat)
      const w = Math.max(200, Math.min(maxAllowed, startWidth - (ev.clientX - startX)))
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
        refreshConvs()
      } catch (err) {
        console.error("Failed to add tag:", err)
      }
    }
  }

  const handleRemoveTag = async (tag: string) => {
    if (activeId) {
      try {
        await removeConversationTag(activeId, tag)
        refreshConvs()
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
        setIsNewChatMode(false)
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
        refreshConvs()
        refreshNotes()
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
      setIsNewChatMode(false)
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
      refreshConvs()
    }
  }

  const handleSelectConversation = (id: string) => {
    setIsNewChatMode(false)
    setActiveId(id)
  }

  const handleNewConversation = () => {
    setIsNewChatMode(true)
    newConversation()
  }

  const handleGoHome = () => {
    setIsNewChatMode(false)
    setActiveId("")
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

  // Landing page
  if (!activeId && !isNewChatMode) {
    return (
      <ConversationLandingPage
        conversations={conversations}
        loading={convLoading}
        loadingMore={convLoadingMore}
        hasMore={convHasMore}
        totalCount={convTotalCount}
        onLoadMore={loadMoreConvs}
        onSelect={handleSelectConversation}
        onDelete={deleteConversation}
        onNew={handleNewConversation}
        onSearchAndFilter={refreshConvs}
        showLogout={isAuthEnabled}
        onLogout={handleLogout}
      />
    )
  }

  // Active chat workspace layout
  return (
    <div className="flex flex-col md:flex-row h-screen bg-[#0c0c0c]">
      {/* Sleek, collapsible Left Panel for Connection Cloud DAG */}
      <div
        className={`
          border-[#222] bg-[#0c0c0c]
          md:border-r md:border-b-0 md:h-full
          border-b
          flex flex-col shrink-0
          overflow-hidden
          transition-all duration-200
          ${leftPanelCollapsed ? "md:w-9 w-full" : "w-full"}
        `}
        style={!leftPanelCollapsed ? { width: `${leftPanelWidth}px` } : undefined}
      >
        {leftPanelCollapsed ? (
          <button
            onClick={() => setLeftPanelCollapsed(false)}
            className="
              flex items-center gap-1.5 shrink-0
              text-xs text-[#555] hover:text-[#888]
              transition-colors
              md:flex-col md:justify-start md:gap-2 md:py-3 md:px-0
              md:h-full
              flex-row justify-start py-2 px-3
              select-none cursor-pointer
            "
          >
            <span className="text-[10px]">▶</span>
            <span className="md:[writing-mode:vertical-rl] md:text-[10px] md:tracking-wider text-[11px] font-mono">
              CONNECTION CLOUD
            </span>
          </button>
        ) : (
          <>
            <div className="flex items-center justify-between shrink-0 px-3 py-2 border-b border-[#222]">
              <span className="text-[10px] font-mono uppercase text-[#666]">Connection Cloud</span>
              <button
                onClick={() => setLeftPanelCollapsed(true)}
                className="flex items-center gap-1 text-[10px] text-[#555] hover:text-[#888] transition-colors cursor-pointer"
              >
                <span>◀</span>
                <span>collapse</span>
              </button>
            </div>

            {/* DAG — 2/3 height */}
            <div className="overflow-hidden relative" style={{ flex: 2 }}>
              {activeId ? (
                <ConnectionCloud
                  activeLoadedMessages={fullTreeMessages}
                  notes={notes}
                  activeMessageId={activeMessageId}
                  activePathIds={activePathIds}
                  setActiveMessageId={setActiveMessageId}
                  commitProposedBranch={commitProposedBranch}
                  refreshTree={refreshTree}
                  conversationId={activeId}
                  onNavigateToMessage={navigateToMessage}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-[#444] text-[10px] font-mono px-4 text-center select-none">
                  DAG will initialize upon first message inscription
                </div>
              )}
            </div>

            {/* Spectral Echoes — 1/3 height, always open */}
            <div className="flex flex-col shrink-0 border-t border-[#222] overflow-y-auto" style={{ flex: 1 }}>
              <div className="px-3 py-1.5 shrink-0">
                <span className="text-[9px] font-mono uppercase tracking-wider text-[#555]">Spectral Echoes</span>
              </div>
              <div className="flex-1 overflow-y-auto px-2 pb-2">
                {activeId ? (
                  <SpectralEchoes
                    conversationId={activeId}
                    activeMessageId={activeMessageId}
                    refreshTree={refreshTree}
                  />
                ) : (
                  <div className="text-[10px] font-mono text-[#333] px-2 select-none">
                    no active node
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>

      {!leftPanelCollapsed && (
        <div
          onMouseDown={handleResizeStart}
          className="w-1 cursor-col-resize hover:bg-[#4ade80]/30 active:bg-[#4ade80]/50 transition-colors shrink-0 hidden md:block"
        />
      )}

      {/* Main chat interface */}
      <ChatView
        messages={messages}
        fullTreeMessages={fullTreeMessages}
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
        onRegenerate={regenerate}
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
        onGoHome={handleGoHome}
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
      />
    </div>
  )
}
