import { useState } from "react"
import { apiFetch, BASE } from "../../../api/http"
import type { ResponseQuality } from "../../../api/types"
import { syncNotifications } from "../../../stores/notificationStore"

export function ResponseQualityBadge({ messageId, quality }: { messageId: number; quality: ResponseQuality }) {
  const [override, setOverride] = useState<ResponseQuality | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const current = override ?? quality
  async function classify(status: "sound" | "degraded") {
    setBusy(true)
    setError("")
    try {
      const response = await apiFetch(`${BASE}/messages/${messageId}/quality`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status, reason: "Participant reviewed message quality", content_hash: current.content_hash }),
      })
      if (!response.ok) throw new Error("Could not update quality. Reload the message and try again.")
      setOverride(await response.json() as ResponseQuality)
      void syncNotifications()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not update quality")
    } finally { setBusy(false) }
  }
  return <div className="mt-2 border border-[#666] px-3 py-2 text-xs font-mono text-[#ddd]" aria-label="Response quality">
    <div className="flex flex-wrap items-center gap-2">
      <strong>{current.status === "degraded" ? "Degraded response" : current.status === "uncertain" ? "Quality needs review" : "Quality reviewed"}</strong>
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
