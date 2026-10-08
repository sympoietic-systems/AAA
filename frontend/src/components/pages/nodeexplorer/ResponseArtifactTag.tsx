import type React from "react"

interface ResponseArtifactTagProps {
  children?: React.ReactNode
  reason?: string
  confidence?: string
  label?: string
  rationale?: string
  trigger?: string
  scope?: string
  temporal_scope?: string
  temporalScope?: string
  consequence?: string
  evidence_quote?: string
  evidenceQuote?: string
}

function Metadata({ label, value }: { label: string; value?: string }) {
  if (!value) return null
  return (
    <div className="flex gap-2 text-[10px] leading-relaxed">
      <span className="shrink-0 uppercase tracking-wider text-[#666]">{label}</span>
      <span className="min-w-0 whitespace-pre-wrap text-[#aaa]">{value}</span>
    </div>
  )
}

export function DreamTriggerTag({ reason }: ResponseArtifactTagProps) {
  if (!reason) return null
  return (
    <aside className="my-3 rounded-sm border border-violet-500/25 border-l-4 border-l-violet-400 bg-[#0a0910] p-3 font-mono" aria-label="Dream trigger">
      <div className="mb-2 flex items-center gap-2 border-b border-[#24212d] pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-violet-300">
        <span aria-hidden="true">◌</span>
        <span>Dream trigger</span>
      </div>
      <p className="m-0 whitespace-pre-wrap pl-1 font-sans text-xs leading-relaxed text-violet-100/90">{reason}</p>
    </aside>
  )
}

export function BeliefNucleateTag({
  children,
  confidence,
  label,
  rationale,
  trigger,
  scope,
  temporal_scope,
  temporalScope,
  consequence,
  evidence_quote,
  evidenceQuote,
}: ResponseArtifactTagProps) {
  return (
    <aside className="my-3 rounded-sm border border-amber-500/25 border-l-4 border-l-amber-400 bg-[#0d0b08] p-3 font-mono" aria-label="Belief candidate">
      <div className="mb-2 flex flex-wrap items-center gap-2 border-b border-[#2b251a] pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-amber-300">
        <span aria-hidden="true">◇</span>
        <span>Belief candidate</span>
        {label && <span className="normal-case tracking-normal text-amber-100">{label}</span>}
        {confidence && <span className="ml-auto text-[#888]">{confidence} confidence</span>}
      </div>
      {children && <div className="mb-2 whitespace-pre-wrap pl-1 font-sans text-sm leading-relaxed text-amber-50">{children}</div>}
      <div className="space-y-1 border-t border-[#2b251a] pt-2">
        <Metadata label="Rationale" value={rationale} />
        <Metadata label="Trigger" value={trigger} />
        <Metadata label="Scope" value={scope} />
        <Metadata label="Time" value={temporal_scope ?? temporalScope} />
        <Metadata label="Consequence" value={consequence} />
        <Metadata label="Evidence" value={evidence_quote ?? evidenceQuote} />
      </div>
    </aside>
  )
}
