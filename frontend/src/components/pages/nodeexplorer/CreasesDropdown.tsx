import { useState, useRef, useEffect, useMemo, memo } from "react"
import type { ConversationInfo, SedimentNotification } from "../../../api/client"
import { formatTime, formatTimeShort } from "../../../utils/dateFormat"
import {
  useNotifications,
  dismissNotification,
  clearNotificationsByType,
} from "../../../stores/notificationStore"

interface Props {
  conversations: ConversationInfo[]
  onNavigateToNotification?: (convId: string, msgId: number) => void
}

export const CreasesDropdown = memo(function CreasesDropdown({ conversations, onNavigateToNotification }: Props) {
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
        className={`relative text-[10px] font-mono transition-colors cursor-pointer select-none ${
          enrichedSediment.length > 0
            ? "text-[#e09b67] hover:text-[#f0b080]"
            : "text-[#666] hover:text-[#888]"
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
        <div         className="absolute right-0 top-full mt-1 z-50 w-85 max-h-96 overflow-hidden flex flex-col bg-[#0c0c0e]/95 backdrop-blur-md">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2 select-none shrink-0">
            <span className="text-[9px] font-mono uppercase tracking-widest text-[#6c6c8a]">
              [ Crease Folds ]
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

          {/* Tabs Nav — terminal style */}
          <div className="flex gap-x-3 px-3 py-1.5 text-[9px] font-mono shrink-0 select-none">
            <button onClick={() => setActiveTab('sediment')}
              className={`cursor-pointer transition-colors ${activeTab === 'sediment' ? 'text-[#e09b67]' : 'text-[#555] hover:text-[#888]'}`}>
              arrivals ({enrichedSediment.length})
            </button>
            <span className="text-[#333]">•</span>
            <button onClick={() => setActiveTab('glitch')}
              className={`cursor-pointer transition-colors relative ${activeTab === 'glitch' ? 'text-[#f43f5e]' : 'text-[#555] hover:text-[#888]'}`}>
              glitches ({glitches.length})
              {unreadGlitchesCount > 0 && <span className="ml-1 text-[#f43f5e] animate-pulse">●</span>}
            </button>
            <span className="text-[#333]">•</span>
            <button onClick={() => setActiveTab('trace')}
              className={`cursor-pointer transition-colors relative ${activeTab === 'trace' ? 'text-[#60a5fa]' : 'text-[#555] hover:text-[#888]'}`}>
              traces ({traces.length})
              {unreadTracesCount > 0 && <span className="ml-1 text-[#60a5fa] animate-pulse">●</span>}
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
                    className="group/notif px-3 py-2 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[9px] font-mono text-[#666] truncate max-w-[180px]" title={notif.conversationTitle}>
                        {notif.conversationTitle}
                      </span>
                      <span className="text-[8px] font-mono text-[#3c3c44]">
                        {formatTimeShort(notif.timestamp)}
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
                        <button onClick={() => handleJump(notif)}
                          className="text-[9px] text-[#666] hover:text-[#4ade80] font-mono cursor-pointer select-none">
                          [jump]
                        </button>
                      )}
                      <button onClick={() => dismissNotification(notif.id)}
                        className="text-[9px] text-[#666] hover:text-[#888] font-mono cursor-pointer select-none">
                        [read]
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
                    className="px-3 py-2.5 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[9px] font-mono text-[#f87171] uppercase tracking-wider truncate max-w-[200px]" title={notif.source}>
                        {notif.source || "system glitch"}
                      </span>
                      <span className="text-[8px] font-mono text-[#884444]">
                        {formatTime(notif.timestamp)}
                      </span>
                    </div>
                    <p className="text-[10px] text-[#fca5a5]/90 font-mono leading-normal break-words whitespace-pre-wrap select-text">
                      {notif.snippet}
                    </p>
                    <div className="flex justify-end gap-2 mt-1.5">
                      {(notif.sourceType === "belief" || notif.sourceType === "skill" || notif.sourceType === "conversation" || !!notif.conversationId) && (
                        <button
                          onClick={() => handleJump(notif)}
                          className="text-[9px] text-[#666] hover:text-[#f87171] font-mono cursor-pointer select-none mr-auto">
                          [jump]
                        </button>
                      )}
                      <button onClick={() => dismissNotification(notif.id)}
                        className="text-[9px] text-[#666] hover:text-[#888] font-mono cursor-pointer select-none">
                        [read]
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
                    className="px-3 py-2.5 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[9px] font-mono text-[#60a5fa] uppercase tracking-wider truncate max-w-[200px]" title={notif.source}>
                        {notif.source || "system trace"}
                      </span>
                      <span className="text-[8px] font-mono text-[#3b82f6]">
                        {formatTime(notif.timestamp)}
                      </span>
                    </div>
                    <p className="text-[10px] text-[#93c5fd]/90 font-mono leading-normal break-words select-text">
                      {notif.snippet}
                    </p>
                    <div className="flex justify-end gap-2 mt-1.5">
                      {(notif.sourceType === "belief" || notif.sourceType === "skill" || notif.sourceType === "conversation" || !!notif.conversationId) && (
                        <button
                          onClick={() => handleJump(notif)}
                          className="text-[9px] text-[#666] hover:text-[#60a5fa] font-mono cursor-pointer select-none mr-auto">
                          [jump]
                        </button>
                      )}
                      <button onClick={() => dismissNotification(notif.id)}
                        className="text-[9px] text-[#666] hover:text-[#888] font-mono cursor-pointer select-none">
                        [read]
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
})

