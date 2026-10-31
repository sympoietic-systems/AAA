import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, expect, it, vi } from "vitest"
import type { BeliefEventInfo, BeliefNodeInfo } from "../../../../api/types"
import { BeliefDetail } from "./BeliefDetail"
import { getBeliefHistory, getBeliefTimeseries } from "../../../../api/client"
import { apiFetch } from "../../../../api/http"

vi.mock("../../../../api/http", () => ({ apiFetch: vi.fn().mockResolvedValue({ json: async () => [] }) }))
vi.mock("../../../../api/beliefReview", () => ({ getBeliefReview: vi.fn().mockRejectedValue(new Error("Review unavailable in legacy fixture")) }))
vi.mock("../../../../api/client", () => ({
  getBeliefTimeseries: vi.fn().mockResolvedValue({ points: [], span_days: 0, bucket_size: "none" }),
  getBeliefHistory: vi.fn().mockResolvedValue({ events: [], admission_history: [] }),
}))
vi.mock("../../../UI/StructuralAutopoieticGlyph", () => ({ StructuralAutopoieticGlyph: () => null }))
vi.mock("../../../UI/BeliefTimelineChart", () => ({ BeliefTimelineChart: () => null }))
afterEach(() => { cleanup(); vi.clearAllMocks() })

function show(events: BeliefEventInfo[]) {
  const belief: BeliefNodeInfo = {
    id: "clock", label: "Clock", statement: "Intervals stay attributable.", category: "methodological",
    confidence: 0.8, ontological_mass: 1, version: 1, vector_16d: "[]", origin: "authored",
    lifecycle_stage: "crystallized", last_reinforced_at: null, updated_at: null, events,
  }
  render(<BeliefDetail belief={belief} activeBeliefs={[]} onUpdate={vi.fn()} onDelete={vi.fn()} agentFlux={false} />)
  fireEvent.click(screen.getByRole("button", { name: /Log/ }))
}

const base: BeliefEventInfo = {
  id: "event", timestamp: "2026-10-08T12:00:00+00:00", source_id: "source", source_type: "chat_turn",
  delta_confidence: 0.15, mass: 1, confidence: 0.8, description: "Accreted: mass=1.000 (delta=+0.150), conf=0.800",
}

it("V17 keeps historical generic impact separate from measured mass and confidence", () => {
  show([base])
  expect(screen.getByText("impact:0.150 (quantity unknown)")).toBeTruthy()
  expect(screen.queryByText("(+0.150)")).toBeNull()
  expect(screen.queryByText(/pp\)/)).toBeNull()
})

it("V17 shows measured deltas and keeps a clipped zero instead of the legacy score", () => {
  show([{ ...base, delta_mass: 0, confidence_delta: -0.01, impact_quantity: "ontological_mass", impact_unit: "mass" }])
  expect(screen.queryByText("(+0.150)")).toBeNull()
  expect(screen.getByText("(-1.0pp)")).toBeTruthy()
  expect(screen.queryByText(/quantity unknown/)).toBeNull()
})

it("V17 displays the measured mass delta rather than rounded legacy rationale", () => {
  show([{ ...base, delta_mass: -0.002, confidence_delta: 0, impact_quantity: "ontological_mass", impact_unit: "mass" }])
  expect(screen.getByText("(-0.002)")).toBeTruthy()
  expect(screen.queryByText("(+0.150)")).toBeNull()
})

const compactBelief: BeliefNodeInfo = {
  id: "compact", label: "Compact", statement: "Load only selected history.", category: "methodological",
  confidence: 0.8, ontological_mass: 1, version: 1, vector_16d: "[]", origin: "authored",
  lifecycle_stage: "crystallized", last_reinforced_at: null, updated_at: null, events: [], history_loaded: false,
}

it("loads selected history and defers chart and version requests until their tabs open", async () => {
  render(<BeliefDetail belief={compactBelief} activeBeliefs={[]} onUpdate={vi.fn()} onDelete={vi.fn()} agentFlux={false} />)
  await waitFor(() => expect(getBeliefHistory).toHaveBeenCalledWith("compact", "symbia"))
  expect(getBeliefTimeseries).not.toHaveBeenCalled()
  expect(apiFetch).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole("button", { name: /Chart/ }))
  await waitFor(() => expect(getBeliefTimeseries).toHaveBeenCalledWith("compact", 30))
  fireEvent.click(screen.getByRole("button", { name: /Version History/ }))
  await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/api/beliefs/compact/versions"))
})

it("ignores a previous agent's late history response", async () => {
  let finishOld!: (value: { events: BeliefEventInfo[] }) => void
  vi.mocked(getBeliefHistory).mockImplementationOnce(() => new Promise(resolve => { finishOld = resolve }))
  vi.mocked(getBeliefHistory).mockResolvedValueOnce({ events: [{ ...base, description: "Current agent history" }] })
  const props = { belief: compactBelief, activeBeliefs: [], onUpdate: vi.fn(), onDelete: vi.fn(), agentFlux: false }
  const view = render(<BeliefDetail {...props} agentId="old-agent" />)
  view.rerender(<BeliefDetail {...props} agentId="new-agent" />)
  fireEvent.click(screen.getByRole("button", { name: /Log/ }))
  expect(await screen.findByText("Current agent history")).toBeTruthy()
  await act(async () => finishOld({ events: [{ ...base, description: "Stale agent history" }] }))
  expect(screen.queryByText("Stale agent history")).toBeNull()
  expect(screen.getByText("Current agent history")).toBeTruthy()
})
