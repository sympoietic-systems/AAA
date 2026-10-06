import { useEffect, useRef, useState } from "react"
import { approveBranchProposal, declineBranchProposal, getBranchProposal, type BranchProposal, type BranchScope } from "../../../api/research"

const fieldStyle = "w-full border border-white/40 bg-black p-2 text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"

interface Props { taskId: string; status: string; onResolved: () => void }

export function BranchProposalReview(props: Props) {
  return <OwnedBranchProposalReview key={`${props.taskId}:${props.status}`} {...props} />
}

function OwnedBranchProposalReview({ taskId, status, onResolved }: Props) {
  const [proposal, setProposal] = useState<BranchProposal | null>(null)
  const [scopes, setScopes] = useState<BranchScope[]>([])
  const [vocabulary, setVocabulary] = useState<Record<string, string>>({})
  const [acknowledged, setAcknowledged] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const controller = useRef<AbortController | null>(null)
  useEffect(() => {
    const owned = new AbortController()
    controller.current = owned
    getBranchProposal(taskId, owned.signal).then(value => {
      if (owned.signal.aborted) return
      setProposal(value)
      setScopes(value?.approved_scopes || value?.draft.scopes || [])
    }).catch(failure => {
      if (!owned.signal.aborted) setError(failure instanceof Error ? failure.message : "Could not load branch proposal")
    })
    return () => owned.abort()
  }, [taskId, status])
  const update = (index: number, change: Partial<BranchScope>) => setScopes(previous => previous.map((scope, i) => i === index ? { ...scope, ...change } : scope))
  const resolve = async (approve: boolean) => {
    const owned = controller.current
    if (!proposal || !owned || owned.signal.aborted || busy || proposal.status !== "pending" || status !== "waiting_for_branch_approval" || approve && !acknowledged) return
    setBusy(true)
    setError("")
    try {
      const resolved = approve
        ? await approveBranchProposal(taskId, proposal.proposal_id, scopes.map(scope => ({ ...scope, retrieval_vocabulary: (vocabulary[scope.scope_id] ?? scope.retrieval_vocabulary.join(", ")).split(",").map(value => value.trim()).filter(Boolean) })), owned.signal)
        : await declineBranchProposal(taskId, proposal.proposal_id, owned.signal)
      if (owned.signal.aborted) return
      setProposal(previous => previous ? { ...previous, ...resolved } : previous)
      onResolved()
    } catch (failure) {
      if (!owned.signal.aborted) setError(failure instanceof Error ? failure.message : "Could not resolve branch proposal")
    } finally {
      if (!owned.signal.aborted) setBusy(false)
    }
  }
  if (!proposal) return error ? <p role="alert" className="p-3 text-white">{error}</p> : null
  const pending = proposal.status === "pending" && status === "waiting_for_branch_approval"
  return <section aria-label="Branch proposal review" className="my-3 max-h-[65vh] overflow-y-auto border border-white/40 bg-black p-4 font-mono text-xs leading-relaxed text-white">
    <h2 className="text-sm font-bold">Branch proposal · {proposal.status}</h2>
    <p className="mt-2">Parent objective: {proposal.parent_objective}</p>
    <p className="mt-2">{proposal.draft.question}</p>
    <p className="mt-2">{proposal.draft.rationale}</p>
    <p className="mt-2">Review expires: {new Date(proposal.expires_at).toLocaleString()}</p>
    <p>Overlap: {proposal.draft.overlap}</p>
    <p>Risk: {proposal.draft.risk}</p>
    <p>Parent reserve: {proposal.draft.parent_attempt_reserve} provider attempts; ${proposal.draft.parent_budget_reserve_usd.toFixed(2)}.</p>
    <p>Proposed child work has not started. Source disagreement remains part of the parent review.</p>
    <details className="my-3">
      <summary className="cursor-pointer focus-visible:outline">Evidence for the proposed cut</summary>
      {proposal.witnesses.map(witness => <div key={witness.segment_id} className="my-2 border-l border-white/40 pl-3">
        <p className="break-all">{witness.source_url || "Authorized document"} · {witness.source_version}</p>
        <p className="break-all">{witness.segment_id} · {witness.representation}</p>
        <blockquote className="my-2 whitespace-pre-wrap">{witness.text}</blockquote>
        {witness.warnings.length > 0 && <p>Extraction notes: {witness.warnings.join("; ")}</p>}
      </div>)}
    </details>
    <form onSubmit={event => { event.preventDefault(); void resolve(true) }}>
      <fieldset disabled={!pending || busy} className="space-y-3">
        {scopes.map((scope, index) => <fieldset key={scope.scope_id} className="space-y-2 border border-white/40 p-3">
          <legend className="px-1">Scope {index + 1}</legend>
          <label className="block">Question<textarea required maxLength={1000} className={fieldStyle} value={scope.question} onChange={event => update(index, { question: event.target.value })} /></label>
          <label className="block">Retrieval vocabulary (comma separated)<input required maxLength={4000} className={fieldStyle} value={vocabulary[scope.scope_id] ?? scope.retrieval_vocabulary.join(", ")} onChange={event => setVocabulary(previous => ({ ...previous, [scope.scope_id]: event.target.value }))} /></label>
          <label className="block">Validation requirements<textarea required maxLength={1000} className={fieldStyle} value={scope.validation_norm} onChange={event => update(index, { validation_norm: event.target.value })} /></label>
          <div className="grid grid-cols-2 gap-3">
            <label>Provider attempts<input required type="number" min={1} max={16} step={1} className={fieldStyle} value={Number.isNaN(scope.attempt_allocation) ? "" : scope.attempt_allocation} onChange={event => update(index, { attempt_allocation: event.target.valueAsNumber })} /></label>
            <label>Budget ceiling (USD)<input required type="number" min={0} max={50} step={0.01} className={fieldStyle} value={Number.isNaN(scope.budget_allocation_usd) ? "" : scope.budget_allocation_usd} onChange={event => update(index, { budget_allocation_usd: event.target.valueAsNumber })} /></label>
          </div>
        </fieldset>)}
        <label className="flex items-start gap-2"><input type="checkbox" checked={acknowledged} onChange={event => setAcknowledged(event.target.checked)} />I reviewed the source witnesses and both scopes remain within the parent objective.</label>
        <div className="flex gap-3">
          <button type="submit" disabled={!acknowledged} className="border border-white px-3 py-2 disabled:opacity-50 focus-visible:outline">Approve edited scopes</button>
          <button type="button" onClick={() => void resolve(false)} className="border border-white px-3 py-2 focus-visible:outline">Decline and continue one line</button>
        </div>
      </fieldset>
    </form>
    {busy && <p role="status">Saving review…</p>}
    {error && <p role="alert" className="mt-2">{error}</p>}
  </section>
}
