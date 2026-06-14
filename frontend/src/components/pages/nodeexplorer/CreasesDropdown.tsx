import { useState, useRef, useEffect, useMemo } from "react"
import type { ConversationInfo, SedimentNotification } from "../../../api/client"
import {
  useNotifications,
  dismissNotification,
  clearNotificationsByType,
} from "../../../stores/notificationStore"

interface Props {
  conversations: ConversationInfo[]
  onNavigateToNotification?: (convId: string, msgId: number) => void
}

export function CreasesDropdown({ conversations, onNavigateToNotification }: Props) {
  const notifications = useNotifications()
  const [creasesOpen, setCreasesOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<'sediment' | 'glitch' | 'trace'>('sediment')
  const creasesRef = useRef<HTMLDivElement>(null)

  // Poll of notifications is handled centrally by the notificationStore

  // Close creases dropdown on click outside
  useEffect(() => {
    if (!creasesOpen) return
    const handleClickOutside = (e: MouseEvent) => {
      if (creasesRef.current && !creasesRef.current.contains(e.target as Node)) {
        setCreasesOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [creasesOpen])

  const handleJump = (n: SedimentNotification) => {
    dismissNotification(n.id)
    setCreasesOpen(false)

    if (n.sourceType === "belief" || n.sourceType === "skill") {
      window.open(`/agent?tab=${n.sourceType}s&id=${n.sourceId || ""}`, "_blank")
    } else if (n.sourceType === "conversation" || n.conversationId) {
      const convId = n.sourceId || n.conversationId
      if (convId) {
        if (onNavigateToNotification && n.messageId) {
          onNavigateToNotification(convId, n.messageId)
        } else {
          window.open(`/?c=${convId}${n.messageId ? `&m=${n.messageId}` : ""}`, "_blank")
        }
      }
    }
  }

  // Filter and enrich sediment notifications with conversation titles for display
  const enrichedSediment = useMemo(() => {
    const sedimentNotifs = notifications.filter((n) => n.type === 'sediment' || !n.type)
    return sedimentNotifs.map((n) => {
      const conv = conversations.find((c) => c.id === n.conversationId)
      return {
        ...n,
        conversationTitle: conv?.title || "Untitled Entanglement",
      }
    })
  }, [notifications, conversations])

  const glitches = useMemo(() => {
    return notifications.filter((n) => n.type === 'glitch')
  }, [notifications])

  const traces = useMemo(() => {
    return notifications.filter((n) => n.type === 'trace')
  }, [notifications])

  const unreadGlitchesCount = useMemo(() => {
    return glitches.filter((n) => !n.read).length
  }, [glitches])

  const unreadTracesCount = useMemo(() => {
    return traces.filter((n) => !n.read).length
  }, [traces])

  return (
    <div className="relative shrink-0" ref={creasesRef}>
      <button
        onClick={() => setCreasesOpen((p) => !p)}
        className={`relative text-[10px] font-mono px-2 py-1 rounded-sm border transition-all duration-200 cursor-pointer ${
          enrichedSediment.length > 0
            ? "text-[#e09b67] border-[#e09b67]/40 bg-[#1a1410] hover:border-[#e09b67]/70 hover:text-[#f0b080]"
            : "text-[#444] border-[#222] bg-[#0c0c0e] hover:text-[#666]"
        }`}
        title={
          unreadGlitchesCount > 0
            ? `${unreadGlitchesCount} unread glitch(es) present`
            : enrichedSediment.length > 0
            ? `${enrichedSediment.length} sediment arrival(s)`
            : "No pending creases"
        }
      >
        {enrichedSediment.length > 0 ? (
          <>
            <span className="animate-pulse mr-1">◆</span>
            creases: {enrichedSediment.length}
          </>
        ) : (
          "creases"
        )}

        {/* Unread glitches pulse marker */}
        {unreadGlitchesCount > 0 && (
          <span className="w-1.5 h-1.5 rounded-full bg-[#f43f5e] animate-pulse absolute -top-0.5 -right-0.5" />
        )}
      </button>

      {/* Creases Dropdown */}
      {creasesOpen && (
        <div className="absolute right-0 top-full mt-1 z-50 w-85 max-h-96 overflow-hidden flex flex-col border border-[#2a2a35] bg-[#0c0c0e]/95 backdrop-blur-md rounded-sm shadow-2xl">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2 border-b border-[#1b1b20] select-none shrink-0">
            <span className="text-[9px] font-mono uppercase tracking-widest text-[#666]">
              Crease Folds
            </span>
            {notifications.filter((n) => n.type === activeTab || (activeTab === 'sediment' && (!n.type || n.type === 'sediment'))).length > 0 && (
              <button
                onClick={() => {
                  clearNotificationsByType(activeTab)
                }}
                className="text-[8px] text-[#555] hover:text-[#888] font-mono cursor-pointer transition-colors"
              >
                clear all
              </button>
            )}
          </div>

          {/* Tabs Nav */}
          <div className="flex border-b border-[#1b1b20] text-[9px] font-mono shrink-0">
            <button
              onClick={() => setActiveTab('sediment')}
              className={`flex-1 py-1.5 text-center border-b transition-colors cursor-pointer ${
                activeTab === 'sediment'
                  ? 'text-[#e09b67] border-[#e09b67] bg-[#15120f]'
                  : 'text-[#555] border-transparent hover:text-[#888]'
              }`}
            >
              arrivals ({enrichedSediment.length})
            </button>
            <button
              onClick={() => setActiveTab('glitch')}
              className={`flex-1 py-1.5 text-center border-b transition-colors cursor-pointer relative ${
                activeTab === 'glitch'
                  ? 'text-[#f43f5e] border-[#f43f5e] bg-[#1a0e0e]'
                  : 'text-[#555] border-transparent hover:text-[#888]'
              }`}
            >
              glitches ({glitches.length})
              {unreadGlitchesCount > 0 && (
                <span className="w-1 h-1 rounded-full bg-[#f43f5e] absolute top-1.5 right-2 animate-pulse" />
              )}
            </button>
            <button
              onClick={() => setActiveTab('trace')}
              className={`flex-1 py-1.5 text-center border-b transition-colors cursor-pointer relative ${
                activeTab === 'trace'
                  ? 'text-[#60a5fa] border-[#60a5fa] bg-[#0c131c]'
                  : 'text-[#555] border-transparent hover:text-[#888]'
              }`}
            >
              traces ({traces.length})
              {unreadTracesCount > 0 && (
                <span className="w-1 h-1 rounded-full bg-[#60a5fa] absolute top-1.5 right-2 animate-pulse" />
              )}
            </button>
          </div>

          {/* Tab Content List */}
          <div className="flex-1 overflow-y-auto max-h-72">
            {activeTab === 'sediment' && (
              enrichedSediment.length === 0 ? (
                <div className="px-3 py-4 text-[10px] text-[#444] font-mono italic text-center select-none">
                  No pending arrivals. The field is still.
                </div>
              ) : (
                enrichedSediment.map((notif) => (
                  <div
                    key={notif.id}
                    className="group/notif px-3 py-2 border-b border-[#151518] hover:bg-[#121216] transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[9px] font-mono text-[#666] truncate max-w-[180px]" title={notif.conversationTitle}>
                        {notif.conversationTitle}
                      </span>
                      <span className="text-[8px] font-mono text-[#3c3c44]">
                        {new Date(notif.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })}
                      </span>
                    </div>
                    <div className="flex items-start gap-2">
                      <span className={`text-[8px] font-mono uppercase tracking-wider mt-0.5 shrink-0 ${
                        notif.speaker === "human" ? "text-[#6bc28c]" : "text-[#a892ee]"
                      }`}>
                        {notif.speaker === "human" ? "H" : "A"}
                      </span>
                      <p className="text-[10px] text-[#888] font-mono truncate flex-1 min-w-0">
                        {(notif.snippet || "").replace(/<[^>]*>/g, "").substring(0, 80).trim() || "[empty]"}
                        {(notif.snippet || "").length > 80 ? "..." : ""}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 mt-1.5">
                      {(notif.sourceType === "belief" || notif.sourceType === "skill" || notif.sourceType === "conversation" || !!notif.conversationId) && (
                        <button
                          onClick={() => handleJump(notif)}
                          className="text-[9px] text-[#888] hover:text-[#4ade80] font-mono border border-[#222] hover:border-[#4ade80]/50 px-1.5 py-0.5 rounded-sm bg-[#0c0c0e] transition-all cursor-pointer"
                        >
                          [↳ Jump]
                        </button>
                      )}
                      <button
                        onClick={() => dismissNotification(notif.id)}
                        className="text-[9px] text-[#555] hover:text-[#888] font-mono cursor-pointer transition-colors"
                      >
                        fold
                      </button>
                    </div>
                  </div>
                ))
              )
            )}

            {activeTab === 'glitch' && (
              glitches.length === 0 ? (
                <div className="px-3 py-4 text-[10px] text-[#444] font-mono italic text-center select-none">
                  No material resistance detected.
                </div>
              ) : (
                glitches.map((notif) => (
                  <div
                    key={notif.id}
                    className="px-3 py-2.5 border-b border-[#2a1313] bg-[#120707]/60 hover:bg-[#1a0c0c]/70 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[9px] font-mono text-[#f87171] uppercase tracking-wider truncate max-w-[200px]" title={notif.source}>
                        {notif.source || "system glitch"}
                      </span>
                      <span className="text-[8px] font-mono text-[#884444]">
                        {new Date(notif.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
                      </span>
                    </div>
                    <p className="text-[10px] text-[#fca5a5]/90 font-mono leading-normal break-words whitespace-pre-wrap select-text">
                      {notif.snippet}
                    </p>
                    <div className="flex justify-end gap-2 mt-1.5">
                      {(notif.sourceType === "belief" || notif.sourceType === "skill" || notif.sourceType === "conversation" || !!notif.conversationId) && (
                        <button
                          onClick={() => handleJump(notif)}
                          className="text-[9px] text-[#884444] hover:text-[#f87171] font-mono border border-[#2a1313] hover:border-[#f87171]/50 px-1.5 py-0.5 rounded-sm bg-[#0c0c0e] transition-all cursor-pointer mr-auto"
                        >
                          [↳ Jump]
                        </button>
                      )}
                      <button
                        onClick={() => dismissNotification(notif.id)}
                        className="text-[9px] text-[#884444] hover:text-[#f87171] font-mono cursor-pointer transition-colors"
                      >
                        fold
                      </button>
                    </div>
                  </div>
                ))
              )
            )}

            {activeTab === 'trace' && (
              traces.length === 0 ? (
                <div className="px-3 py-4 text-[10px] text-[#444] font-mono italic text-center select-none">
                  No system trace logs available.
                </div>
              ) : (
                traces.map((notif) => (
                  <div
                    key={notif.id}
                    className="px-3 py-2.5 border-b border-[#0f172a] bg-[#090d16]/60 hover:bg-[#0f172a]/70 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[9px] font-mono text-[#60a5fa] uppercase tracking-wider truncate max-w-[200px]" title={notif.source}>
                        {notif.source || "system trace"}
                      </span>
                      <span className="text-[8px] font-mono text-[#3b82f6]">
                        {new Date(notif.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
                      </span>
                    </div>
                    <p className="text-[10px] text-[#93c5fd]/90 font-mono leading-normal break-words select-text">
                      {notif.snippet}
                    </p>
                    <div className="flex justify-end gap-2 mt-1.5">
                      {(notif.sourceType === "belief" || notif.sourceType === "skill" || notif.sourceType === "conversation" || !!notif.conversationId) && (
                        <button
                          onClick={() => handleJump(notif)}
                          className="text-[9px] text-[#3b82f6] hover:text-[#60a5fa] font-mono border border-[#0f172a] hover:border-[#60a5fa]/50 px-1.5 py-0.5 rounded-sm bg-[#0c0c0e] transition-all cursor-pointer mr-auto"
                        >
                          [↳ Jump]
                        </button>
                      )}
                      <button
                        onClick={() => dismissNotification(notif.id)}
                        className="text-[9px] text-[#3b82f6] hover:text-[#60a5fa] font-mono cursor-pointer transition-colors"
                      >
                        fold
                      </button>
                    </div>
                  </div>
                ))
              )
            )}
          </div>
        </div>
      )}
    </div>
  )
}

