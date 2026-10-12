import { evaluationDiagnostics } from "../../../../utils/evaluationDiagnostics"

export function EvaluationDiagnostics({ diagnostics }: { diagnostics: unknown }) {
  const rows = evaluationDiagnostics(diagnostics)
  if (!rows.length) return null
  return <section aria-label="Observed classifier choices" className="space-y-2 overflow-x-auto">
    <h4 className="text-ui-primary">Observed classifier choices</h4>
    <p>Diagnostic observations carry no semantic verdict or independent support. Assessment status remains unchanged.</p>
    <p>Confidence is classifier-reported and has not been calibrated as accuracy.</p>
    <table className="w-full text-left text-[11px]">
      <thead><tr><th scope="col">Question</th><th scope="col">Observed choice</th>
        <th scope="col">Confidence / threshold</th><th scope="col">Question check</th></tr></thead>
      <tbody>{rows.map(row => <tr key={row.question_id}>
        <th scope="row" className="pr-2 align-top">{row.question_id.replaceAll("_", " ")}</th>
        <td className="pr-2 align-top">{row.choice ?? "Not retained"}</td>
        <td className="pr-2 align-top">{row.confidence == null ? "Unavailable" : String(row.confidence)} / {String(row.threshold)}</td>
        <td className="align-top">{row.status.replaceAll("_", " ")}
          {row.comparison_id && <p className="break-all">Comparison: {row.comparison_id}</p>}
        </td>
      </tr>)}</tbody>
    </table>
  </section>
}
