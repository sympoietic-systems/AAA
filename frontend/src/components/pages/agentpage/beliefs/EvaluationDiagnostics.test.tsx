import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, expect, it } from "vitest"
import { EvaluationDiagnostics } from "./EvaluationDiagnostics"

afterEach(cleanup)
it("V28 labels a weak choice separately from verdict and calibrated accuracy", () => {
  render(<EvaluationDiagnostics diagnostics={[{ question_id: "relation_0", choice: "contradiction",
    confidence: .19, threshold: .85, status: "below_threshold", is_semantic_verdict: false,
    comparison_id: "candidate:peer" }]} />)
  expect(screen.getByText("contradiction")).toBeTruthy()
  expect(screen.getByText("0.19 / 0.85")).toBeTruthy()
  expect(screen.getByText(/carry no semantic verdict/)).toBeTruthy()
  expect(screen.getByText(/has not been calibrated as accuracy/)).toBeTruthy()
  expect(screen.getByText(/Comparison: candidate:peer/)).toBeTruthy()
})

it("V28 historical absent data and malformed payloads render no invented observations", () => {
  const { container } = render(<EvaluationDiagnostics diagnostics={[{ question_id: "bad", choice: "<script>",
    confidence: Infinity, threshold: .85, status: "below_threshold", is_semantic_verdict: true }]} />)
  expect(container.textContent).toBe("")
})
