import type { AdmissionReceipt } from "../api/types"

const receiptMarker = "\n\nAdmission receipt:\n"

export function traceSummary(snippet: string): string {
  return snippet.split(receiptMarker)[0]
}

export function traceReceipt(snippet: string): AdmissionReceipt | null {
  const start = snippet.indexOf(receiptMarker)
  if (start < 0) return null
  try {
    const value = JSON.parse(snippet.slice(start + receiptMarker.length)) as Partial<AdmissionReceipt>
    return typeof value.id === "string" && typeof value.decision === "string" && typeof value.reason === "string"
      && typeof value.created_at === "string" && typeof value.source?.conversation_id === "string"
      && typeof value.source?.message_id === "number" ? value as AdmissionReceipt : null
  } catch { return null }
}
