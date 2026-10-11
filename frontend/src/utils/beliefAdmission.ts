import type { AdmissionReceipt } from "../api/types"
import type { WorkshopReceipt } from "../api/beliefReview"

const receiptMarker = "\n\nAdmission receipt:\n"

export function traceSummary(snippet: string): string {
  const packet = traceWorkshopReceipt(snippet)
  if (packet) return `Scoped review: ${packet.decision.next_state}\n${packet.decision.rationale}`
  return snippet.split(receiptMarker)[0]
}

export function traceReceipt(snippet: string): AdmissionReceipt | null {
  const start = snippet.indexOf(receiptMarker)
  if (start < 0) return null
  try {
    const value = JSON.parse(snippet.slice(start + receiptMarker.length)) as Partial<AdmissionReceipt>
    return typeof value.id === "string" && typeof value.decision === "string" && typeof value.reason === "string"
      && typeof value.created_at === "string" && !!value.source
      && (typeof value.source.conversation_id === "string" || value.source.conversation_id === null)
      && (typeof value.source.message_id === "number" || value.source.message_id === null) ? value as AdmissionReceipt : null
  } catch { return null }
}

export function traceWorkshopReceipt(snippet: string): WorkshopReceipt | null {
  if (snippet.length > 256000) return null
  try {
    const value = JSON.parse(snippet) as Partial<WorkshopReceipt> | null
    return value && typeof value.id === "string" && typeof value.agent_id === "string"
      && typeof value.record_id === "string" && typeof value.decision?.id === "string"
      && typeof value.decision.timestamp === "string" && typeof value.decision.rationale === "string"
      && typeof value.decision.next_state === "string" && !!value.record_snapshot
      ? value as WorkshopReceipt : null
  } catch { return null }
}
