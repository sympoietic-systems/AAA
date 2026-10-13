import { useEffect, useId, useRef, useState } from "react"
import { decideBelief, getBeliefReview } from "../../../../api/beliefReview"
import type { ReviewAction, ReviewCommand, WorkshopReceipt, WorkshopView } from "../../../../api/beliefReview"
import { ApiError } from "../../../../api/http"
import { CounterTrace, RecordedDetails, ReviewReceipt, ReceiptDisclosure } from "./ReviewReasoning"

const pendingActions: ReviewAction[] = ["request_review", "request_context", "defer", "decline", "adopt"]
const adoptedActions: ReviewAction[] = ["revise", "supersede", "resurface"]
const control = "w-full bg-transparent text-ui-primary font-mono py-2 focus-visible:outline outline-1"

export function BeliefWorkshop({ agent, record, onReload, onLegacyAvailability }: {
  agent: string; record: string; onReload?: () => void; onLegacyAvailability: (id: string, allowed: boolean) => void
}) {
  const identity = `${agent}/${record}`
  const actionId = useId()
  const [loaded, setLoaded] = useState<{ identity: string; view?: WorkshopView; error?: string } | null>(null)
  const [refresh, setRefresh] = useState(0)
  const [action, setAction] = useState<ReviewAction>("request_review")
  const [scope, setScope] = useState("")
  const [temporalScope, setTemporalScope] = useState("")
  const [rationale, setRationale] = useState("")
  const [consequence, setConsequence] = useState("")
  const [challenge, setChallenge] = useState("")
  const [dissent, setDissent] = useState("")
  const [revisedStatement, setRevisedStatement] = useState("")
  const [targetRecordId, setTargetRecordId] = useState("")
  const [busy, setBusy] = useState(false)
  const [outcome, setOutcome] = useState<{ identity: string; receipt?: WorkshopReceipt; error?: string; stale?: boolean } | null>(null)
  const attempt = useRef<{ identity: string; serialized: string; key: string } | null>(null)
  const inFlight = useRef(false)
  useEffect(() => {
    const controller = new AbortController()
    onLegacyAvailability(record, false)
    getBeliefReview(agent, record, controller.signal).then(view => {
      if (controller.signal.aborted) return
      setLoaded({ identity, view })
      setScope(view.record.scope); setTemporalScope(view.record.temporal_scope)
      onLegacyAvailability(record, !view.record.state && view.record.context_provenance.startsWith("stored-record:"))
    }).catch(error => {
      if (!controller.signal.aborted) setLoaded({ identity, error: error instanceof Error ? error.message : "Workshop unavailable" })
    })
    return () => controller.abort()
  }, [agent, record, identity, refresh, onLegacyAvailability])
  const view = loaded?.identity === identity ? loaded.view : undefined
  const result = outcome?.identity === identity ? outcome : null
  const actions = view?.record.state?.state === "adopted" ? adoptedActions
    : view?.record.state?.state === "superseded" ? ["resurface" as ReviewAction]
    : pendingActions
  const currentAction = actions.includes(action) ? action : actions[0]
  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!view || inFlight.current || result?.stale) return
    if ([scope, rationale, consequence, challenge].some(value => !value.trim())) {
      setOutcome({ identity, error: "Scope, rationale, consequence and challenge must contain text." })
      return
    }
    const command: ReviewCommand = {
      action: currentAction, expected_review_version: view.record.state?.version ?? 0,
      expected_statement_sha256: view.record.statement_sha256, expected_state: view.record.state?.state ?? null,
      scope: scope.trim(), temporal_scope: temporalScope.trim(), rationale: rationale.trim(),
      consequence: consequence.trim(), challenge: challenge.trim(), dissent: dissent.trim() ? [dissent.trim()] : [],
      // Assessments are historical and require explicit reassessment before binding a new decision.
      assessment_ids: [],
    }
    if (currentAction === "revise") command.statement = revisedStatement.trim()
    if (currentAction === "supersede") {
      const target = view.family.find(member => member.id === targetRecordId && member.state?.state === "adopted")
      if (!target) { setOutcome({ identity, error: "Choose a currently adopted target from the family list." }); return }
      command.target_record_id = target.id
      command.expected_target_review_version = target.state?.version
      command.expected_target_statement_sha256 = target.statement_sha256
    }
    const serialized = JSON.stringify(command)
    if (attempt.current?.identity !== identity || attempt.current.serialized !== serialized) {
      attempt.current = { identity, serialized, key: crypto.randomUUID() }
    }
    inFlight.current = true; setBusy(true)
    try {
      const receipt = await decideBelief(agent, record, command, attempt.current.key)
      setOutcome({ identity, receipt })
      setLoaded(null)
      setRefresh(n => n + 1); onReload?.()
    } catch (error) {
      setOutcome({ identity, error: error instanceof Error ? error.message : "Decision unavailable", stale: error instanceof ApiError && error.status === 409 })
    } finally { inFlight.current = false; setBusy(false) }
  }
  return <section aria-label="Belief v2 workshop" className="font-mono text-[11px] text-ui-secondary space-y-3 min-w-0 break-words">
    <h3 className="text-ui-primary uppercase">[ Scoped review workshop ]</h3>
    {!view ? <>
      <p role={loaded?.identity === identity && loaded.error ? "alert" : "status"}>{loaded?.identity === identity && loaded.error ? `Workshop unavailable: ${loaded.error}` : "Loading review state…"}</p>
      <button className="min-h-11 text-action-dim focus-visible:outline" onClick={() => setRefresh(n => n + 1)}>[refresh workshop]</button>
    </> : <>
      <p>Review state: {view.record.state?.state ?? "unknown / legacy unreviewed"} · version {view.record.state?.version ?? 0}</p>
      <p>Legacy lifecycle: {view.record.legacy_status} · {view.record.source_current ? "source binding current" : "source binding stale / unavailable"}</p>
      <p>Source quotation</p><blockquote className="whitespace-pre-wrap">{view.record.quote || "Unknown / not recorded"}</blockquote>
      <p className="whitespace-pre-wrap">Authored claim / interpretation: {view.record.statement}</p>
      <p>Shared operator credential; personal identity and bilateral agreement are unknown.</p>
      <p>Assessments remain provisional. Mass and legacy confidence describe separate quantities.</p>
      <details><summary className="py-2 cursor-pointer focus-visible:outline">Family review ({view.family.length} nominations)</summary>
        <p>Bounded lexical nominations; no equivalence, contradiction or merge verdict inferred. {view.uncompared_in_bounded_scan} outside displayed comparison budget.</p>
        {view.family.map(member => <div key={member.id} className="py-2">
          <a className="underline focus-visible:outline" href={`/agent?tab=beliefs&agent=${encodeURIComponent(agent)}&id=${encodeURIComponent(member.id)}`}>{member.label}</a>
          <p>{member.statement}</p><p>Scope: {member.scope || "unknown"} · Time: {member.temporal_scope || "unknown"} · Standing: {member.state?.state ?? "unknown"}</p>
        </div>)}
      </details>
      <ReceiptDisclosure label={`Historical assessments (${view.advisory_assessments.length}) · reassessment required`}>
        {view.advisory_assessments.map((entry, index) => typeof entry.receipt.id === "string"
          ? <ReviewReceipt key={entry.receipt.id} agent={agent} resource="assessments" id={entry.receipt.id} />
          : <RecordedDetails key={index} value={entry} label="Historical assessment with unknown identity" />)}
      </ReceiptDisclosure>
      <ReceiptDisclosure label={`Operator receipts (${view.commands.length} of ${view.command_count})`}>
        {view.commands.map(packet => <div key={packet.id} className="space-y-2 py-3">
          <p>Workshop receipt {packet.id} · Decision {packet.decision.id}</p>
          <ReviewReceipt agent={agent} resource="decisions" id={packet.decision.id} />
          <RecordedDetails value={{ relations: packet.command.relations, snapshots: packet.relation_snapshots, teachback: packet.command.teachback, alternative: packet.alternative_snapshot }} label="Scoped relation declarations and teachback reconstruction (historical)" />
        </div>)}
        {view.history_truncated && <p>Older commands retained; bounded history truncated.</p>}
      </ReceiptDisclosure>
      <section aria-label="Belief lineage" className="space-y-2">
        <h4 className="text-ui-primary">Linked lineage ({view.lineage_links?.length ?? 0} of {view.lineage_count ?? 0})</h4>
        {!view.lineage_links?.length && <p>No explicit revision or supersession link recorded.</p>}
        {view.lineage_links?.map(link => {
          const relatedId = link.source_record_id === record ? link.successor_record_id : link.source_record_id
          const relation = link.source_record_id === record ? "successor" : "predecessor"
          return <div key={`${link.command_id}:${link.action}`} className="py-1">
            <p>{link.action} · {relation} statement hash {link.source_record_id === record ? link.successor_statement_sha256 : link.source_statement_sha256}</p>
            <a className="underline focus-visible:outline" href={`/agent?tab=beliefs&agent=${encodeURIComponent(agent)}&id=${encodeURIComponent(relatedId)}`}>Open linked record {relatedId}</a>
            <ReviewReceipt agent={agent} resource="decisions" id={link.decision_id} />
          </div>
        })}
        {view.lineage_truncated && <p>Older lineage links retained; bounded display truncated.</p>}
      </section>
      <section aria-label="Retained counter-traces" className="space-y-2">
        <h4 className="text-ui-primary">Retained decline / dissent ({view.counter_traces.length} of {view.counter_trace_count})</h4>
        {!view.counter_traces.length && <p>No recorded decline counter-trace in this view.</p>}
        {view.counter_traces.map((counter, index) => <CounterTrace key={typeof counter.id === "string" ? counter.id : index} value={counter} />)}
        {view.counter_traces_truncated && <p>Older counter-traces retained; bounded display truncated.</p>}
      </section>
      {result?.receipt && <p role="status">Recorded decision {result.receipt.decision.id} · {result.receipt.decision.next_state}</p>}
      {result?.error && <p role="alert">{result.error}{result.stale ? " Refresh before a new decision; no overwrite occurred." : " Retry unchanged fields to recover the same command receipt."}</p>}
      {result?.stale && <button className="min-h-11 text-action-dim focus-visible:outline" onClick={() => { setLoaded(null); setOutcome(null); attempt.current = null; setRefresh(n => n + 1) }}>[refresh changed record]</button>}
      <form onSubmit={submit} className="space-y-2">
        <fieldset disabled={busy || !!result?.stale} className="space-y-2">
          <legend className="text-ui-primary">Record a scoped operator decision</legend>
          <label className="block" htmlFor={actionId}>Action</label>
          <select id={actionId} className={control} value={currentAction} onChange={e => setAction(e.target.value as ReviewAction)}>{actions.map(value => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select>
          {currentAction === "revise" && <label className="block">New candidate statement<textarea className={control} required maxLength={4000} value={revisedStatement} onChange={e => setRevisedStatement(e.target.value)} /></label>}
          {currentAction === "supersede" && <label className="block">Adopted successor<select className={control} required value={targetRecordId} onChange={e => setTargetRecordId(e.target.value)}><option value="">Choose target</option>{view.family.filter(member => member.state?.state === "adopted").map(member => <option key={member.id} value={member.id}>{member.label}: {member.statement.slice(0, 100)}</option>)}</select></label>}
          {currentAction === "resurface" && <p>Resurfacing records attention only; it adds no assessment, warrant or mass.</p>}
          <label className="block">Scope<input className={control} required maxLength={500} value={scope} onChange={e => setScope(e.target.value)} /></label>
          <label className="block">Time scope<input className={control} maxLength={250} value={temporalScope} onChange={e => setTemporalScope(e.target.value)} /></label>
          <label className="block">Rationale<textarea className={control} required maxLength={2000} value={rationale} onChange={e => setRationale(e.target.value)} /></label>
          <label className="block">Consequence<textarea className={control} required maxLength={1000} value={consequence} onChange={e => setConsequence(e.target.value)} /></label>
          <label className="block">Challenge<textarea className={control} required maxLength={1000} value={challenge} onChange={e => setChallenge(e.target.value)} /></label>
          <label className="block">Dissent / unresolved objection<textarea className={control} maxLength={2000} value={dissent} onChange={e => setDissent(e.target.value)} /></label>
          <button className="min-h-11 text-action-dim focus-visible:outline" type="submit">{busy ? "[recording…]" : "[record decision]"}</button>
        </fieldset>
      </form>
    </>}
  </section>
}
