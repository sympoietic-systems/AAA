import { useEffect, useState } from "react"
import { getReviewReceipt } from "../../../../api/beliefReview"
import type { Recorded, ReasoningKey, ReviewExportItem } from "../../../../api/beliefReview"

const fields: [ReasoningKey, string][] = [
  ["encounter", "1. Encounter / source"], ["claim_or_tension", "2. Claim / tension"],
  ["comparison", "3. Comparison"], ["consequence_or_challenge", "4. Consequence / challenge"],
  ["decision_or_uncertainty", "5. Decision / uncertainty"],
]

/** Stored data remains inert text, including quotations and historical emission XML. */
export function RecordedDetails({ value, label }: { value: unknown; label: string }) {
  return <details><summary className="cursor-pointer py-2 focus-visible:outline" >{label}</summary>
    <pre className="whitespace-pre-wrap break-words text-[11px] max-h-80 overflow-auto">{JSON.stringify(value, null, 2)}</pre>
  </details>
}

export function ReceiptDisclosure({ label, children }: { label: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return <details onToggle={event => setOpen(event.currentTarget.open)}>
    <summary className="cursor-pointer py-2 focus-visible:outline">{label}</summary>
    {open && children}
  </details>
}

export function CounterTrace({ value }: { value: Recorded }) {
  const actor = value.actor && typeof value.actor === "object" ? value.actor as Recorded : null
  return <article aria-label="Retained scoped dissent" className="space-y-1 text-ui-secondary break-words">
    <p className="text-ui-primary">Counter-trace {String(value.id ?? "unknown")}</p>
    <p>Actor: {String(actor?.principal_id ?? "unknown")} · Scope: {String(value.scope ?? "unknown")} · Time scope: {String(value.temporal_scope ?? "unknown")}</p>
    {typeof value.timestamp === "string" ? <time dateTime={value.timestamp}>{value.timestamp}</time> : <p>Timestamp unknown / not recorded</p>}
    <p className="whitespace-pre-wrap">{String(value.rationale ?? "Unknown / not recorded")}</p>
    <p className="whitespace-pre-wrap">Consequence: {String(value.consequence ?? "unknown")}</p>
    <p className="whitespace-pre-wrap">Challenge: {String(value.challenge ?? "unknown")}</p>
    {Array.isArray(value.dissent) && value.dissent.map((objection, index) => <p key={index} className="whitespace-pre-wrap">Retained objection: {String(objection)}</p>)}
    <RecordedDetails value={value} label="Original counter-trace" />
  </article>
}

function EncounterSource({ value }: { value: Recorded }) {
  const source = value.source && typeof value.source === "object" ? value.source as Recorded : null
  const linked = Array.isArray(value.linked_encounters) ? value.linked_encounters : []
  return <div className="space-y-1">
    {linked.map((entry: Recorded, index: number) => <EncounterSource key={typeof entry.id === "string" ? entry.id : index} value={entry} />)}
    {source && <>
      <p>Source quotation</p><blockquote className="whitespace-pre-wrap break-words">{typeof source.quote === "string" && source.quote ? source.quote : "Unknown / not recorded"}</blockquote>
    </>}
    {typeof value.statement === "string" && <p className="whitespace-pre-wrap">Authored claim / interpretation: {value.statement}</p>}
    <RecordedDetails value={value} label="Recorded source, scope and lineage" />
  </div>
}

export function ReviewReasoning({ item }: { item: ReviewExportItem }) {
  const uncertainty = item.reasoning.decision_or_uncertainty
  const status = uncertainty && !Array.isArray(uncertainty) ? uncertainty.evaluator_status : null
  return <article aria-label="Recorded belief reasoning" className="font-mono text-[11px] text-ui-secondary space-y-2 min-w-0 break-words">
    <p className="text-ui-primary">Receipt {item.id} · {item.kind}</p>
    {item.timestamp ? <time dateTime={item.timestamp}>{item.timestamp}</time> : <p>Timestamp unknown / not recorded</p>}
    {item.kind === "assessment" && <p>Provisional advisory assessment · evaluator {typeof status === "string" ? status : "unknown"}</p>}
    {typeof item.record.abstain_reason === "string" && item.record.abstain_reason && <p>Evaluator uncertainty: {item.record.abstain_reason}</p>}
    {item.kind === "decision" && <p>Scoped operator decision · shared agreement not inferred</p>}
    {item.kind === "decision" && <p>This records a situated commitment; factual verification remains separate.</p>}
    {typeof item.record.rationale === "string" && <p>Recorded rationale: {item.record.rationale}</p>}
    {Array.isArray(item.record.dissent) && item.record.dissent.length > 0 && <p>Recorded dissent: {item.record.dissent.join("; ")}</p>}
    {fields.map(([key, label]) => <section key={key} aria-label={label}>
      <h4 className="text-ui-primary">{label}</h4>
      {item.reasoning[key] == null ? <p>Unknown / not recorded</p> : key === "encounter" && !Array.isArray(item.reasoning[key])
        ? <EncounterSource value={item.reasoning[key] as Recorded} />
        : <RecordedDetails value={item.reasoning[key]} label={`Recorded ${label.slice(3).toLowerCase()}`} />}
    </section>)}
    <p>Warrant dimensions remain separate. Artistic warrant cannot verify embedded factual claims.</p>
    <RecordedDetails value={item.record.warrant_dimensions ?? null} label="Recorded warrant dimensions (unknown when absent)" />
    <RecordedDetails value={item.source_accounting} label="Recorded source accounting / independence uncertainty" />
    {item.comparison_truncated && <p>Comparison or source-accounting projection truncated; original receipt retains its links.</p>}
    {item.content_redacted && <p>Response content redacted; stored receipt identity retained.</p>}
    <RecordedDetails value={{ sources: item.reasoning_sources, record: item.record, tool_authority: item.tool_authority }} label="Original receipt and linked identities" />
  </article>
}

export function ReviewReceipt({ agent, resource, id }: { agent: string; resource: "encounters" | "assessments" | "decisions"; id: string }) {
  // Keyed state prevents an old agent/record response from appearing during navigation.
  const identity = `${agent}/${resource}/${id}`
  const [result, setResult] = useState<{ identity: string; item?: ReviewExportItem; error?: string } | null>(null)
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    getReviewReceipt(agent, resource, id, controller.signal)
      .then(item => { if (!controller.signal.aborted) setResult({ identity, item }) })
      .catch(error => { if (!controller.signal.aborted) setResult({ identity, error: error instanceof Error ? error.message : "Receipt unavailable" }) })
    return () => controller.abort()
  }, [agent, resource, id, identity, retry])
  if (result?.identity !== identity) return <p role="status">Loading recorded receipt {id}…</p>
  if (!result.item) return <div role="alert"><p>Receipt {id} unavailable: {result.error}. Reasoning remains unknown.</p>
    <button className="text-action-dim min-h-11 focus-visible:outline" onClick={() => setRetry(n => n + 1)}>[retry receipt]</button></div>
  return <ReviewReasoning item={result.item} />
}
