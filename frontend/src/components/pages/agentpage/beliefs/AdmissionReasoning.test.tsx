import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, expect, it } from "vitest"
import type { AdmissionReceipt } from "../../../../api/types"
import { traceReceipt, traceSummary } from "../../../../utils/beliefAdmission"
import { AdmissionReasoning } from "./AdmissionReasoning"

afterEach(cleanup)

const receipt: AdmissionReceipt = {
  id: "receipt-1", status: "complete", statement: "Memory changes later decisions.", label: "memory",
  decision: "needs_review", reason: "Shadow assessment cannot authorize nucleation.", recommendation: "new_insight",
  created_at: "2026-10-07T01:00:00+00:00", assessed_at: "2026-10-07T01:00:01+00:00",
  policy_version: "belief-admission-v1-shadow", mode: "shadow", consequence: "Reject inert replay.",
  scope: "Memory experiments", temporal_scope: "Repeated trials", trigger: "counterexample", evidence_quote: "A state change alters the next decision.",
  source: { conversation_id: "conversation", message_id: 42, message_sha256: "message-hash", evidence_sha256: "source-hash" },
  comparisons: [{ id: "existing", kind: "belief", label: "Existing conviction", statement: "Memory persists.", statement_sha256: "comparison-hash" }],
  evaluation: { status: "evaluated", model: "fixture-jev", answers: { relation_0: { choice: "extension", confidence: 0.92 } } },
}

it("V122 exposes decisions, time, source, consequence, and comparison uncertainty", () => {
  render(<AdmissionReasoning receipts={[receipt]} statement="A revised formulation." />)
  expect(screen.getByText("needs review")).toBeTruthy()
  expect(screen.getByText(/Statement changed after assessment/)).toBeTruthy()
  expect(screen.getByText(/Proposed consequence: Reject inert replay/)).toBeTruthy()
  expect(screen.getByRole("link", { name: "Source message 42" }).getAttribute("href")).toBe("/nodes?c=conversation&m=42")
  expect(screen.getByRole("link", { name: "Existing conviction" }).getAttribute("href")).toBe("/agent?tab=beliefs&id=existing")
  expect(screen.getByText(/Relation: extension/)).toBeTruthy()
  expect(document.querySelector("time")?.getAttribute("datetime")).toBe(receipt.assessed_at)
})

it("V122 trace parsing retains the same receipt and legacy uncertainty", () => {
  const snippet = `Candidate assessed\n\nAdmission receipt:\n${JSON.stringify(receipt)}`
  expect(traceSummary(snippet)).toBe("Candidate assessed")
  expect(traceReceipt(snippet)).toEqual(receipt)
  expect(traceReceipt("Ordinary trace")).toBeNull()
  expect(traceReceipt("Bad\n\nAdmission receipt:\n{}")).toBeNull()
  render(<AdmissionReasoning receipts={[]} />)
  expect(screen.getByText(/unavailable for this historical record/)).toBeTruthy()
})
