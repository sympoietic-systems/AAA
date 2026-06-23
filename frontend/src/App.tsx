import { useState, useRef, useEffect, useCallback } from "react"
import { useChat } from "./hooks/useChat"
import { useConversations } from "./hooks/useConversations"
import { useNotes } from "./hooks/useNotes"
import { dismissByMatch } from "./stores/notificationStore"
import { NodeExplorer } from "./components/pages/nodeexplorer/NodeExplorer"
import { SidePanel } from "./components/panels/sidepanel/SidePanel"
import { ConversationLandingPage } from "./components/pages/landing/ConversationLandingPage"
import { AgentPage } from "./components/pages/agentpage/AgentPage"
import { ResearchPage } from "./components/pages/researchpage/ResearchPage"
import { ResearchTaskPage } from "./components/pages/researchpage/ResearchTaskPage"
import ConnectionCloud from "./components/panels/leftpanel/ConnectionCloud"
import { SpectralEchoes } from "./components/panels/leftpanel/SpectralEchoes"
import { checkAuthStatus, verifyPassword, logout, addConversationTag, getAgent, deleteMessage, downloadExport } from "./api/client"
import { TeaserPreview } from "./components/TeaserPreview"
import { LoginPage } from "./components/pages/login/LoginPage"
import { HeaderContainer, HeaderIndicator, HeaderLogo, HeaderSeparator, HeaderLabel, HeaderActionButton, CreasesDropdown, UnifiedFooter } from "./components/UI"

const EMPTY_STRING_ARRAY: string[] = []

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null)
  const [isAuthEnabled, setIsAuthEnabled] = useState<boolean>(false)
  const [authError, setAuthError] = useState<string | null>(null)
  const [agentFlux, setAgentFlux] = useState<boolean>(false)

  useEffect(() => {
    checkAuthStatus().then((status) => {
      setIsAuthenticated(status.authenticated)
      setIsAuthEnabled(status.authEnabled)
      // Only fetch agent info if authenticated (skip 401 on locked page)
      if (status.authenticated || !status.authEnabled) {
        getAgent().then(info => setAgentFlux(!!info.agent_flux)).catch(() => setAgentFlux(false))
      }
    })
  }, [])

  const handlePasswordSubmit = async (password: string) => {
    setAuthError(null)
    const success = await verifyPassword(password)
    if (success) {
      localStorage.setItem("aaa_password", password)
      setIsAuthenticated(true)
      window.location.href = "/nodes"
    } else {
      setAuthError("Incorrect password")
    }
  }

  const handleLogout = () => {
    logout()
    setIsAuthenticated(false)
    window.location.href = "/"
  }

  const path = window.location.pathname
  const params = new URLSearchParams(window.location.search)

  // 1. Initializing state
  if (isAuthenticated === null) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#0c0c0c] text-sm font-mono text-[#555] select-none">
        <span className="animate-pulse">initializing system...</span>
      </div>
    )
  }

  // 2. Intercept query parameters on root page / and redirect to /nodes
  if (path === "/" && params.has("c")) {
    window.location.replace(`/nodes${window.location.search}`)
    return null
  }

  // 3. Routing and Authentication guards
  if (path === "/login") {
    // If auth is not enabled, or user is already authenticated, redirect to /nodes
    if (!isAuthEnabled || isAuthenticated) {
      window.location.replace("/nodes")
      return null
    }
  } else if (path === "/nodes" || path === "/agent" || path === "/research") {
    // If auth is enabled and user is not authenticated, redirect to /login
    if (isAuthEnabled && !isAuthenticated) {
      window.location.replace("/login")
      return null
    }
  } else if (path !== "/") {
    // Fallback/wildcard: if they visit a page we don't know, redirect to /
    window.location.replace("/")
    return null
  }

  // --- Router switch ---

  // / (landing page artwork)
  if (path === "/") {
    return (
      <div className="h-screen w-screen overflow-hidden">
        <TeaserPreview />
      </div>
    )
  }

  // /login (authentication page)
  if (path === "/login") {
    return (
      <LoginPage
        onPasswordSubmit={handlePasswordSubmit}
        authError={authError}
        onClearError={() => setAuthError(null)}
      />
    )
  }

  // /agent (agent page console)
  if (path === "/agent") {
    return (
      <AgentPage
        onGoHome={() => window.location.href = "/nodes"}
      />
    )
  }

  // /research (research pages)
  if (path === "/research") {
    const taskId = params.get("id")
    const isNew = params.get("id") === "new"
    if (taskId && !isNew) {
      return <ResearchTaskPage taskId={taskId} />
    }
    if (isNew) {
      return <ResearchTaskPage taskId="" isNew />
    }
    return <ResearchPage />
  }

  // /nodes (conversations workspace page)
  if (path === "/nodes") {
    return (
      <NodesPage
        isAuthEnabled={isAuthEnabled}
        handleLogout={handleLogout}
        agentFlux={agentFlux}
      />
    )
  }

  return null
}

/* --- Subcomponent for /nodes workspace to respect React rules of Hooks --- */

interface NodesPageProps {
  isAuthEnabled: boolean
  handleLogout: () => void
  agentFlux: boolean
}

function NodesPage({ isAuthEnabled, handleLogout, agentFlux }: NodesPageProps) {
  const [isNewChatMode, setIsNewChatMode] = useState(false)

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
    refreshMessages,
    refreshTree,
    selectedNode,
    parentNode,
    siblingNodes,
    childNodes,
    treeNodes,
    history,
  } = useChat(activeId)

  const handleNavigateToNotification = useCallback((convId: string, msgId: number) => {
    dismissByMatch(convId, msgId)
    if (convId === activeId) {
      navigateToMessage(msgId)
    } else {
      setIsNewChatMode(false)
      setActiveId(convId, msgId)
    }
  }, [activeId, navigateToMessage, setActiveId])

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

  const handleDeleteNote = useCallback(async (noteId: string) => {
    await removeNote(noteId)
    refreshMessages()
  }, [removeNote, refreshMessages])

  const handleUpdateNote = useCallback(async (noteId: string, comment?: string, visibility?: "personal" | "shared" | "agent") => {
    await editNote(noteId, comment, visibility)
    refreshMessages()
  }, [editNote, refreshMessages])

  const handleDeleteFile = useCallback((fileName: string) => {
    deleteFile(fileName)
  }, [deleteFile])

  const handleDeleteMessage = useCallback(async (messageId: number) => {
    if (!activeId) return
    if (!confirm("Delete this node permanently?")) return
    try {
      await deleteMessage(activeId, messageId)
      refreshMessages()
      refreshTree()
    } catch (err: any) {
      console.error("Failed to delete message:", err)
    }
  }, [activeId, refreshMessages, refreshTree])

  const handleReprocessFile = useCallback((fileName: string) => {
    reprocess(fileName)
  }, [reprocess])

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

  const [editingTitle, setEditingTitle] = useState(false)
  const [titleVal, setTitleVal] = useState("")

  useEffect(() => {
    setTitleVal(conversationTitle)
  }, [conversationTitle])

  const handleRenameTitle = (title: string) => {
    if (activeId) renameConversation(activeId, title)
  }

  const handleTitleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    setEditingTitle(false)
    if (titleVal.trim() && titleVal !== conversationTitle) {
      handleRenameTitle(titleVal)
    }
  }

  const handleGenerateTitle = async () => {
    if (activeId) await generateTitle(activeId)
  }

  const handleExportConversation = async () => {
    if (activeId) {
      try {
        await downloadExport(activeId)
      } catch (err) {
        console.error("Failed to export conversation:", err)
      }
    }
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

  // Inside /nodes: If no active conversation and not in new chat mode, show the Landing Page (conversation list)
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
        agentFlux={agentFlux}
      />
    )
  }

  // Active chat workspace layout (inside /nodes)
  return (
    <div className="flex flex-col h-screen bg-[#0c0c0c]">
      <HeaderContainer>
        <span className="text-[11px] text-semantic-header tracking-widest uppercase select-none flex items-center gap-1.5 min-w-0">
          <HeaderIndicator intent="green" />
          <HeaderLogo onClick={handleGoHome} />
          <HeaderSeparator />
          <HeaderLabel intent="green">entanglement</HeaderLabel>
          <HeaderSeparator className="hidden sm:inline" />
          
          <div className="min-w-0 flex-1 sm:flex-initial hidden sm:block">
            {editingTitle ? (
              <form onSubmit={handleTitleSubmit} className="inline-block">
                <input
                  type="text"
                  value={titleVal}
                  onChange={(e) => setTitleVal(e.target.value)}
                  onBlur={() => handleTitleSubmit()}
                  className="bg-transparent border-b border-[#222]/40 px-1 py-0.5 text-xs text-[#ddd] font-mono outline-none focus:border-action-hover/50 w-32 sm:w-48 md:w-64"
                  autoFocus
                />
              </form>
            ) : (
              <div className="flex items-center gap-2">
                <h1
                  onClick={() => setEditingTitle(true)}
                  className="text-xs font-mono font-bold tracking-wider text-semantic-header hover:text-[#aaa] cursor-pointer truncate max-w-[120px] md:max-w-xs uppercase"
                  title={conversationTitle || "Untitled Entanglement"}
                >
                  {conversationTitle || "Untitled Entanglement"}
                </h1>
                <HeaderActionButton
                  onClick={handleGenerateTitle}
                  title="Auto-generate title"
                >
                  #generate_title
                </HeaderActionButton>
              </div>
            )}
          </div>
        </span>

        <div className="flex items-center gap-3 sm:gap-4 shrink-0">
          {conversationId && (
            <HeaderActionButton
              onClick={handleExportConversation}
              title="Export conversation as Markdown"
              className="hidden md:inline"
            >
              #export
            </HeaderActionButton>
          )}

          <HeaderActionButton
            onClick={() => setLeftPanelCollapsed(prev => !prev)}
            title="Toggle Connection Cloud (DAG)"
            className="md:hidden"
          >
            {leftPanelCollapsed ? "show cloud" : "hide cloud"}
          </HeaderActionButton>

          <HeaderActionButton
            onClick={() => setRightPanelCollapsed(prev => !prev)}
            title="Toggle Metadata Pipeline"
            className="md:hidden"
          >
            {rightPanelCollapsed ? "show pipeline" : "hide pipeline"}
          </HeaderActionButton>

          <CreasesDropdown
            conversations={conversations}
            onNavigateToNotification={handleNavigateToNotification}
          />
          
          <HeaderActionButton onClick={() => window.location.href = '/agent'}>
            agent
          </HeaderActionButton>

          <HeaderActionButton onClick={() => window.location.href = '/research'}>
            research
          </HeaderActionButton>

          <HeaderActionButton onClick={handleNewConversation}>
            + new
          </HeaderActionButton>

          {isAuthEnabled && (
            <HeaderActionButton
              onClick={handleLogout}
              className="hover:text-red-500! hidden sm:inline"
            >
              logout
            </HeaderActionButton>
          )}
        </div>
      </HeaderContainer>

      {/* For mobile screens: show title bar beneath header if screen is small */}
      <div className="sm:hidden flex items-center justify-between px-4 py-2 border-b border-[#1a1a1a] shrink-0 font-mono text-[11px] bg-[#0d0d0d]">
        <div className="min-w-0 flex-1">
          {editingTitle ? (
            <form onSubmit={handleTitleSubmit} className="w-full">
              <input
                type="text"
                value={titleVal}
                onChange={(e) => setTitleVal(e.target.value)}
                onBlur={() => handleTitleSubmit()}
                className="bg-transparent border-b border-[#222]/40 px-1 py-0.5 text-xs text-[#ddd] font-mono outline-none focus:border-action-hover/50 w-full"
                autoFocus
              />
            </form>
          ) : (
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-[#444]">title:</span>
              <h1
                onClick={() => setEditingTitle(true)}
                className="text-xs font-mono font-bold tracking-wider text-semantic-header hover:text-[#aaa] cursor-pointer truncate flex-1 uppercase"
                title={conversationTitle || "Untitled Entanglement"}
              >
                {conversationTitle || "Untitled Entanglement"}
              </h1>
              <HeaderActionButton
                onClick={handleGenerateTitle}
                title="Auto-generate title"
                className="shrink-0"
              >
                #gen
              </HeaderActionButton>
            </div>
          )}
        </div>
        {conversationId && (
          <HeaderActionButton
            onClick={handleExportConversation}
            title="Export conversation as Markdown"
            className="shrink-0 ml-2"
          >
            #export
          </HeaderActionButton>
        )}
      </div>

      {/* Workspace Area: Left Panel, NodeExplorer, SidePanel */}
      <div className="flex-1 flex flex-row min-h-0 overflow-hidden relative">
        {/* Backdrop for Left Panel overlay on mobile */}
        {!leftPanelCollapsed && (
          <div
            onClick={() => setLeftPanelCollapsed(true)}
            className="md:hidden fixed inset-0 z-20 bg-black/60 backdrop-blur-xs"
          />
        )}

        {/* Sleek, collapsible Left Panel for Connection Cloud DAG */}
        <div
          className={`
            border-[#222] bg-[#0c0c0c]
            md:border-r md:border-b-0 md:h-full
            flex flex-col shrink-0
            overflow-hidden
            transition-all duration-200
            ${leftPanelCollapsed 
              ? "hidden md:flex md:w-9 md:h-full" 
              : "absolute md:relative z-30 left-0 top-0 bottom-0 w-[85vw] max-w-[340px] md:w-auto md:h-full md:flex md:z-auto border-r md:border-r-0 bg-[#0c0c0e]/95"
            }
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
                    agentFlux={agentFlux}
                    onDeleteMessage={handleDeleteMessage}
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
            className="w-1 cursor-col-resize hover:bg-action-hover/20 active:bg-action-hover/40 transition-colors shrink-0 hidden md:block"
          />
        )}

        {/* Main node explorer interface */}
        <NodeExplorer
          selectedNode={selectedNode}
          parentNode={parentNode}
          siblingNodes={siblingNodes}
          childNodes={childNodes}
          treeNodes={treeNodes}
          loading={loading}
          error={error}
          agentName={agentName}
          conversationId={conversationId}
          uploadedFiles={uploadedFiles}
          onSend={handleSend}
          onUploadFiles={handleUploadFiles}
          isIndexing={isIndexing}
          onClearError={clearError}
          onRegenerate={regenerate}
          notes={notes}
          onAddNote={handleAddNote}
          onDeleteNote={handleDeleteNote}
          onUpdateNote={handleUpdateNote}
          tags={(activeConv?.tags ?? EMPTY_STRING_ARRAY) as any}
          onAddTag={handleAddTag}
          onNavigateToMessage={navigateToMessage}
          className="flex-1 min-w-0"
          history={history}
          onDeleteMessage={agentFlux ? handleDeleteMessage : undefined}
        />

        {/* Backdrop for Right Panel overlay on mobile */}
        {!rightPanelCollapsed && (
          <div
            onClick={() => setRightPanelCollapsed(true)}
            className="md:hidden fixed inset-0 z-20 bg-black/60 backdrop-blur-xs"
          />
        )}

        {!rightPanelCollapsed && (
          <div
            onMouseDown={handleRightResizeStart}
            className="w-1 cursor-col-resize hover:bg-action-hover/20 active:bg-action-hover/40 transition-colors shrink-0 hidden md:block"
          />
        )}

        <SidePanel
          uploadedFiles={uploadedFiles}
          conversationId={conversationId}
          onDeleteFile={handleDeleteFile}
          onReprocessFile={handleReprocessFile}
          messageCount={messages.length}
          notes={notes}
          onDeleteNote={handleDeleteNote}
          onUpdateNote={handleUpdateNote}
          summary={activeConv?.summary}
          humanSummary={activeConv?.human_summary}
          width={rightPanelWidth}
          panelCollapsed={rightPanelCollapsed}
          onPanelToggle={() => setRightPanelCollapsed(p => !p)}
          onNavigateNode={navigateToMessage}
        />
      </div>
      <UnifiedFooter />
    </div>
  )
}
