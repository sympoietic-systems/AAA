import { traceReceipt, traceWorkshopReceipt } from "../../../../utils/beliefAdmission"
import { AdmissionReasoning } from "./AdmissionReasoning"
import { CounterTrace, RecordedDetails, ReviewReceipt, ReceiptDisclosure } from "./ReviewReasoning"

export function TraceBeliefReasoning({ snippet }: { snippet: string }) {
  const packet = traceWorkshopReceipt(snippet)
  if (packet) return <details className="text-ui-secondary text-[11px] min-w-0 break-words">
    <summary className="cursor-pointer py-2 focus-visible:outline">Scoped decision receipt</summary>
    <p>Workshop receipt {packet.id}</p>
    <a className="underline focus-visible:outline" href={`/agent?tab=beliefs&agent=${encodeURIComponent(packet.agent_id)}&id=${encodeURIComponent(packet.record_id)}`}>Open belief workshop</a>
    <ReceiptDisclosure label="Load recorded decision reasoning"><ReviewReceipt agent={packet.agent_id} resource="decisions" id={packet.decision.id} /></ReceiptDisclosure>
    {packet.counter_trace && <CounterTrace value={packet.counter_trace} />}
    <RecordedDetails value={{ command: packet.command, snapshot: packet.record_snapshot, relations: packet.relation_snapshots, alternative: packet.alternative_snapshot }} label="Original workshop declarations / reconstruction" />
  </details>
  const receipt = traceReceipt(snippet)
  return receipt ? <details className="text-ui-secondary text-[11px] min-w-0 break-words">
    <summary className="cursor-pointer py-2 focus-visible:outline">Admission reasoning</summary>
    <AdmissionReasoning receipts={[receipt]} />
  </details> : null
}
