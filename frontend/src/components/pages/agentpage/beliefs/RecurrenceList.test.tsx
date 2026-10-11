import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, expect, it } from "vitest"
import type { BeliefNodeInfo, RecurrenceGroup } from "../../../../api/types"
import { RecurrenceList } from "./RecurrenceList"
import { recurrenceEntries } from "../../../../utils/beliefRecurrence"

afterEach(cleanup)
const group: RecurrenceGroup = { id: "a", member_ids: ["a", "b"], count: 2,
  count_kind: "visible_queue_entries", standing: "context_incomplete", semantic_equivalence: "unknown",
  independent_warrant_delta: 0, tool_authority: "none", scan_truncated: false, ancestry_unavailable: 0 }
const make = (id: string): BeliefNodeInfo => ({ id, label: id, statement: "Exact fragment.", category: "methodological",
  confidence: .15, ontological_mass: .15, version: 1, vector_16d: "", origin: "emergent",
  lifecycle_stage: "candidate", last_reinforced_at: null, updated_at: null, events: [], recurrence_group: group })

it("V27 preserves every entry, reveals selected member, labels multiplicity without support", () => {
  const entries = recurrenceEntries([make("a"), make("b"), { ...make("c"), recurrence_group: undefined }])
  expect(entries).toHaveLength(2)
  render(<RecurrenceList entries={entries} selectedId="b" renderItem={item => <button key={item.id}>{item.label}</button>} />)
  expect(screen.getByText(/Occurrences add no independent support/)).toBeTruthy()
  expect(screen.getByText(/Repeated fragment/).closest("details")?.open).toBe(true)
  for (const id of ["a", "b", "c"]) expect(screen.getByRole("button", { name: id })).toBeTruthy()
})

it("V27 incomplete metadata never hides a singleton", () => {
  expect(recurrenceEntries([make("b")])).toEqual([[make("b")]])
})
