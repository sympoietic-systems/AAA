import type { EvaluationDiagnostic } from "../api/types"

export function evaluationDiagnostics(value: unknown): EvaluationDiagnostic[] {
  if (!Array.isArray(value)) return []
  return value.slice(0, 14).filter((item): item is EvaluationDiagnostic => {
    if (!item || typeof item !== "object") return false
    const row = item as Record<string, unknown>
    return row.is_semantic_verdict === false
      && typeof row.question_id === "string" && /^(consequence|factual_grounding|artistic_grounding|tension|relation_[0-9])$/.test(row.question_id)
      && (row.choice === null || typeof row.choice === "string" && row.choice.length <= 64)
      && (row.confidence === null || typeof row.confidence === "number" && Number.isFinite(row.confidence) && row.confidence >= 0 && row.confidence <= 1)
      && typeof row.threshold === "number" && Number.isFinite(row.threshold) && row.threshold >= 0 && row.threshold <= 1
      && ["within_threshold", "below_threshold", "missing", "invalid_choice", "invalid_confidence"].includes(String(row.status))
      && (row.comparison_id == null || typeof row.comparison_id === "string" && row.comparison_id.length <= 200)
      && (row.comparison_statement_sha256 == null || typeof row.comparison_statement_sha256 === "string"
        && /^[a-f0-9]{64}$/.test(row.comparison_statement_sha256))
  })
}
