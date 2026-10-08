import { useState } from "react"
import { apiFetch, BASE } from "../../../api/http"
import type { ResponseQuality } from "../../../api/types"
import { syncNotifications } from "../../../stores/notificationStore"

export function ResponseQualityBadge({ messageId, quality, status }: {
  messageId: number
  quality?: ResponseQuality | null
  status?: ResponseQuality["status"]
}) {
  const [override, setOverride] = useState<ResponseQuality | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const current = override ?? quality
  if (!current) {
    if (status !== "degraded" && status !== "uncertain") return null
    return <div
      role="note"
      aria-label={status === "degraded" ? "Degraded response warning" : "Response quality review warning"}
      className={`mt-2 border-l-2 px-3 py-2 text-xs font-mono ${status === "degraded" ? "border-red-500 bg-red-950/30 text-red-200" : "border-yellow-500 bg-yellow-950/20 text-yellow-100"}`}
    >
      <strong>{status === "degraded" ? "⚠ Degraded response" : "⚠ Response quality needs review"}</strong>
      {status === "degraded" && <span className="ml-2">Excluded from generation context</span>}
    </div>
  }
  const activeQuality = current

  async function classify(status: "sound" | "degraded") {
    setBusy(true)
    setError("")
    try {
      const response = await apiFetch(`${BASE}/messages/${messageId}/quality`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status, reason: "Participant reviewed message quality", content_hash: activeQuality.content_hash }),
      })
      if (!response.ok) throw new Error("Could not update quality. Reload the message and try again.")
      setOverride(await response.json() as ResponseQuality)
      void syncNotifications()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not update quality")
    } finally { setBusy(false) }
  }
  return <div className={`mt-2 border-l-2 px-3 py-2 text-xs font-mono ${current.status === "degraded" ? "border-red-500 bg-red-950/30 text-red-100" : current.status === "uncertain" ? "border-yellow-500 bg-yellow-950/20 text-yellow-100" : "border-[#666] text-[#ddd]"}`} aria-label="Response quality">
    <div className="flex flex-wrap items-center gap-2">
      <strong>{current.status === "degraded" ? "⚠ Degraded response" : current.status === "uncertain" ? "⚠ Quality needs review" : "Quality reviewed"}</strong>
      {current.confidence != null && <span>Jev confidence {Math.round(current.confidence * 100)}%</span>}
      <span>{current.excluded_from_context ? "Excluded from generation context" : "Available to generation context"}</span>
    </div>
    <p className="mt-1 text-[#aaa]">{current.reason === "reasoning_only" ? "No separate final answer was returned." : current.source === "manual" ? "Participant classification" : "Automated assessment; original message preserved."}</p>
    <div className="mt-2 flex gap-3">
      <button disabled={busy} onClick={() => void classify(current.status === "degraded" ? "sound" : "degraded")}
        className="cursor-pointer underline hover:text-white disabled:opacity-50">
        {current.status === "degraded" ? "Mark sound and include" : "Mark degraded and exclude"}
      </button>
      {current.status === "uncertain" && <button disabled={busy} className="cursor-pointer underline hover:text-white disabled:opacity-50" onClick={() => void classify("sound")}>Mark sound</button>}
    </div>
    {error && <p role="alert" className="mt-2">{error}</p>}
  </div>
}
