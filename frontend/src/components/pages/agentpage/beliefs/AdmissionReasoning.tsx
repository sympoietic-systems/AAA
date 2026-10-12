import type { AdmissionReceipt } from "../../../../api/types"
import { formatDateTimeFull } from "../../../../utils/dateFormat"
import { ReviewReceipt } from "./ReviewReasoning"

import { EvaluationDiagnostics } from "./EvaluationDiagnostics"

export function AdmissionReasoning({ receipts, statement, agent }: { receipts: AdmissionReceipt[]; statement?: string; agent?: string }) {
  if (!receipts.length) return <p className="text-[10px] text-[#888]">Admission reasoning unavailable for this historical record.</p>
  return <section aria-label="Belief admission reasoning" className="space-y-3 text-[10px] font-mono text-[#bbb]">
    <div className="text-[#ddd] uppercase tracking-wider">[ Admission reasoning ]</div>
    {receipts.map(receipt => <article key={receipt.id} className="space-y-1.5 border-l border-[#555] pl-2">
      {receipt.encounter_id && (agent || receipt.agent_id || receipt.source_accounting?.agent_id) ? <ReviewReceipt
        agent={agent || receipt.agent_id || receipt.source_accounting!.agent_id!} resource={receipt.assessment_id ? "assessments" : "encounters"} id={receipt.assessment_id || receipt.encounter_id} /> : <>
      <p>Receipt {receipt.id} · Historical advisory reasoning; operator adoption unknown.</p>
      <div className="flex flex-wrap gap-2">
        <strong className="text-[#eee]">{receipt.decision.replaceAll("_", " ")}</strong>
        <time dateTime={receipt.assessed_at || receipt.created_at}>{formatDateTimeFull(receipt.assessed_at || receipt.created_at)}</time>
      </div>
      <p>{receipt.reason}</p>
      {statement && statement !== receipt.statement && <p className="text-[#ddd]">Statement changed after assessment. This receipt describes the original candidate.</p>}
      <p>Proposed consequence: {receipt.consequence || "Not supplied"}</p>
      <p>Scope: {receipt.scope || "Unknown"} · Time scope: {receipt.temporal_scope || "Unknown"}</p>
      <p>Trigger: {receipt.trigger || "Unknown"} · Recommendation: {receipt.recommendation?.replaceAll("_", " ") || "Not assessed"}</p>
      <p>Mode: {receipt.mode} · Policy: {receipt.policy_version}</p>
      <p>Evaluator: {receipt.evaluation?.model || "Not called"} · {receipt.evaluation?.status || "Not assessed"}
        {receipt.evaluation?.reason && ` (${receipt.evaluation.reason})`}</p>
      {!!receipt.context_issues?.length && <p>Context gaps: {receipt.context_issues.join(", ").replaceAll("_", " ")}</p>}
      {receipt.source.conversation_id && receipt.source.message_id != null ? <a className="underline text-[#ddd]" href={`/nodes?c=${encodeURIComponent(receipt.source.conversation_id)}&m=${receipt.source.message_id}`}>
        Source message {receipt.source.message_id}
      </a> : <p>Source message unavailable / unknown.</p>}
      <p>1. Encounter / source: {receipt.encounter_id || "Unknown / not recorded"}</p>
      <p>2. Claim / tension: {receipt.statement || "Unknown / not recorded"}</p>
      <p>3. Comparison: {receipt.comparisons ? `${receipt.comparisons.length} recorded snapshots` : "Unknown / not recorded"}</p>
      <p>4. Consequence / challenge: {receipt.consequence || "Unknown / not recorded"} · {receipt.challenge || "Challenge unknown / not recorded"}</p>
      <EvaluationDiagnostics diagnostics={receipt.evaluation?.diagnostics} />
      <p>5. Decision / uncertainty: advisory {receipt.decision}; operator decision unknown.</p>
      <p>Source quotation (separate from authored claim)</p>
      {receipt.evidence_quote && <blockquote className="border-l border-[#444] pl-2 whitespace-pre-wrap">{receipt.evidence_quote}</blockquote>}
      {!!receipt.comparisons?.length && <details>
        <summary className="cursor-pointer">Compared with {receipt.comparisons.length} items · {receipt.uncompared_count || 0} outside comparison budget</summary>
        <div className="space-y-2 mt-1">
          {receipt.comparisons.map((comparison, index) => <div key={comparison.id}>
            <a className="underline" href={`/agent?tab=beliefs&id=${encodeURIComponent(comparison.id)}`}>{comparison.label}</a>
            <p>{comparison.statement}</p>
            <p>Relation: {receipt.evaluation?.answers?.[`relation_${index}`]?.choice || "Not assessed"}
              {receipt.evaluation?.answers?.[`relation_${index}`]?.confidence != null && ` · confidence ${Math.round(receipt.evaluation.answers[`relation_${index}`].confidence! * 100)}%`}</p>
          </div>)}
        </div>
      </details>}
      {receipt.evaluation?.answers && <details>
        <summary className="cursor-pointer">Assessment answers</summary>
        {Object.entries(receipt.evaluation.answers).filter(([key]) => !key.startsWith("relation_")).map(([key, answer]) => <p key={key}>
          {key}: {answer.choice || "Uncertain"} {answer.confidence != null && `(${Math.round(answer.confidence * 100)}% confidence)`}
        </p>)}
      </details>}
      <details><summary className="cursor-pointer">Provenance</summary>
        <pre className="whitespace-pre-wrap break-all text-[9px]">{JSON.stringify({ receipt_id: receipt.id, source: receipt.source, source_accounting: receipt.source_accounting ?? null, warrant_dimensions: receipt.warrant_dimensions ?? null, input_sha256: receipt.evaluation?.input_sha256 }, null, 2)}</pre>
      </details>
      </>}
    </article>)}
  </section>
}
