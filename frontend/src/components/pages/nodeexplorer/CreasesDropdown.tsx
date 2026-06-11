import { useState, useRef, useEffect, useMemo } from "react"
import type { ConversationInfo } from "../../../api/client"
import { useNotifications, dismissNotification, clearAllNotifications } from "../../../stores/notificationStore"

interface Props {
  conversations: ConversationInfo[]
  onNavigateToNotification?: (convId: string, msgId: number) => void
}

export function CreasesDropdown({ conversations, onNavigateToNotification }: Props) {
  const notifications = useNotifications()
  const [creasesOpen, setCreasesOpen] = useState(false)
  const creasesRef = useRef<HTMLDivElement>(null)

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

  // Enrich notifications with conversation titles for display
  const enrichedNotifications = useMemo(() => {
    return notifications.map((n) => {
      const conv = conversations.find((c) => c.id === n.conversationId)
      return {
        ...n,
        conversationTitle: conv?.title || "Untitled Entanglement",
      }
    })
  }, [notifications, conversations])

  return (
    <div className="relative shrink-0" ref={creasesRef}>
      <button
        onClick={() => setCreasesOpen((p) => !p)}
        className={`text-[10px] font-mono px-2 py-1 rounded-sm border transition-all duration-200 cursor-pointer ${
          enrichedNotifications.length > 0
            ? "text-[#e09b67] border-[#e09b67]/40 bg-[#1a1410] hover:border-[#e09b67]/70 hover:text-[#f0b080]"
            : "text-[#444] border-[#222] bg-[#0c0c0e] hover:text-[#666]"
        }`}
        title={enrichedNotifications.length > 0 ? `${enrichedNotifications.length} sediment arrival(s)` : "No pending creases"}
      >
        {enrichedNotifications.length > 0 ? (
          <>
            <span className="animate-pulse mr-1">◆</span>
            creases: {enrichedNotifications.length}
          </>
        ) : (
          "creases"
        )}
      </button>

      {/* Creases Dropdown */}
      {creasesOpen && (
        <div className="absolute right-0 top-full mt-1 z-50 w-80 max-h-72 overflow-y-auto border border-[#2a2a35] bg-[#0c0c0e]/95 backdrop-blur-md rounded-sm shadow-2xl">
          <div className="flex items-center justify-between px-3 py-2 border-b border-[#1b1b20] select-none">
            <span className="text-[9px] font-mono uppercase tracking-widest text-[#666]">
              Sediment Arrivals
            </span>
            {enrichedNotifications.length > 0 && (
              <button
                onClick={() => {
                  clearAllNotifications()
                  setCreasesOpen(false)
                }}
                className="text-[8px] text-[#555] hover:text-[#888] font-mono cursor-pointer transition-colors"
              >
                dismiss all
              </button>
            )}
          </div>
          {enrichedNotifications.length === 0 ? (
            <div className="px-3 py-4 text-[10px] text-[#444] font-mono italic text-center select-none">
              No pending folds. The field is still.
            </div>
          ) : (
            enrichedNotifications.map((notif) => (
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
                  {onNavigateToNotification && (
                    <button
                      onClick={() => {
                        onNavigateToNotification(notif.conversationId, notif.messageId)
                        setCreasesOpen(false)
                      }}
                      className="text-[9px] text-[#888] hover:text-[#4ade80] font-mono border border-[#222] hover:border-[#4ade80]/50 px-1.5 py-0.5 rounded-sm bg-[#0c0c0e] transition-all cursor-pointer"
                    >
                      [↳ Jump]
                    </button>
                  )}
                  <button
                    onClick={() => dismissNotification(notif.id)}
                    className="text-[9px] text-[#555] hover:text-[#888] font-mono cursor-pointer transition-colors"
                  >
                    dismiss
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
