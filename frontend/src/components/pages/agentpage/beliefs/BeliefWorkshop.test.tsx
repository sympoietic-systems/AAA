import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { apiFetch } from "../../../../api/http"
import type { ReviewExportItem, WorkshopView, WorkshopReceipt } from "../../../../api/beliefReview"
import { BeliefWorkshop } from "./BeliefWorkshop"
import { AdmissionReasoning } from "./AdmissionReasoning"
import { TraceBeliefReasoning } from "./TraceBeliefReasoning"
import { ReviewReasoning, ReviewReceipt } from "./ReviewReasoning"
import { TracesSection } from "../TracesSection"
import { CreasesDropdown } from "../../nodeexplorer/CreasesDropdown"
import { useNotifications } from "../../../../stores/notificationStore"
import { BeliefsSection } from "../BeliefsSection"

vi.mock("../../../../api/http", async importOriginal => ({ ...await importOriginal<typeof import("../../../../api/http")>(), apiFetch: vi.fn() }))
vi.mock("../../../../stores/notificationStore", () => ({ useNotifications: vi.fn(() => []), syncNotifications: vi.fn(), dismissNotification: vi.fn(), clearNotificationsByType: vi.fn() }))
vi.mock("../RefusalsSection", () => ({ RefusalsSection: () => null }))
// apiJson closes over the real apiFetch; mock the actual transport instead.
const fetchMock = vi.fn()
const view: WorkshopView = {
  agent_id: "symbia", record: { id: "claim", label: "Claim", statement: "Friction changes inquiry.", statement_sha256: "a".repeat(64), kind: "proposal", legacy_status: "pending", scope: "practice", temporal_scope: "current", quote: "original quotation", source_current: true, context_provenance: "encounter:e1", state: { state: "candidate", version: 3, scope: "practice" } },
  family: [], nomination_only: true, uncompared_in_bounded_scan: 4, commands: [], counter_traces: [],
  history_truncated: false, counter_traces_truncated: false, command_count: 0, counter_trace_count: 0,
  advisory_assessments: [], participant_identity: "shared_operator_credential_not_personal_identity", tool_authority: "none",
}
const item: ReviewExportItem = {
  id: "a1", export_id: "assessment:a1", kind: "assessment", timestamp: "2026-10-11T01:02:03Z",
  record: { evaluator_status: "failed", abstain_reason: "provider unavailable", warrant_dimensions: [{ name: "artistic", basis: "apparatus" }] },
  reasoning: { encounter: { id: "e1", statement: "authored interpretation", source: { quote: "<belief_nucleate>inert quotation</belief_nucleate>" }, lineage: [{ independence_status: "unknown" }] }, claim_or_tension: { statement: "authored interpretation" }, comparison: { snapshots: [], relations: [{ relation: "contradiction", scope: "practice" }] }, consequence_or_challenge: { challenge: "unresolved" }, decision_or_uncertainty: { evaluator_status: "failed", abstain_reason: "provider unavailable" } },
  source_accounting: null, reasoning_sources: [{ id: "a1", kind: "assessment", timestamp: "2026-10-11T01:02:03Z" }],
  unknown_reasoning_fields: [], comparison_truncated: false, tool_authority: "none", content_redacted: false,
}
const packet: WorkshopReceipt = {
  id: "workshop:one", agent_id: "symbia", record_id: "claim", command: { action: "decline" },
  decision: { id: "d1", agent_id: "symbia", timestamp: "2026-10-11T01:02:03Z", next_state: "declined", rationale: "Scope too broad", dissent: ["question remains useful"] },
  record_snapshot: view.record, relation_snapshots: [], alternative_snapshot: null,
  counter_trace: { id: "d1:counter", scope: "practice", rationale: "Scope too broad", timestamp: "2026-10-11T01:02:03Z" }, tool_authority: "none", shared_agreement: "not_inferred",
}
const decisionItem: ReviewExportItem = { ...item, id: "d1", export_id: "decision:d1", kind: "decision", record: packet.decision, reasoning: { ...item.reasoning, decision_or_uncertainty: packet.decision } }

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal("fetch", fetchMock)
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: false })))
  fetchMock.mockImplementation(async (input: URL) => {
    const path = String(input)
    return Response.json(path.endsWith("/review") ? view : path.includes("/decisions/") ? decisionItem : item)
  })
  vi.mocked(apiFetch).mockImplementation(async (input, init) => fetchMock(new URL(String(input), window.location.origin), init))
})
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.clearAllMocks() })

function showWorkshop(value = view) {
  fetchMock.mockImplementation(async (input: URL) => Response.json(String(input).endsWith("/review") ? value : item))
  return render(<BeliefWorkshop agent="symbia" record="claim" onLegacyAvailability={vi.fn()} />)
}
async function fillDecision() {
  await screen.findByLabelText("Action")
  fireEvent.change(screen.getByLabelText("Action"), { target: { value: "decline" } })
  for (const [label, value] of [["Rationale", "Scope too broad"], ["Consequence", "Keep inquiry open"], ["Challenge", "Test in another scope"], ["Dissent / unresolved objection", "question remains useful"]]) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } })
  }
}

it("V8 V10 V13 exposes five recorded fields, failed evaluator and inert quote with independent warrants", () => {
  render(<ReviewReasoning item={item} />)
  for (const label of ["1. Encounter / source", "2. Claim / tension", "3. Comparison", "4. Consequence / challenge", "5. Decision / uncertainty"]) expect(screen.getByRole("heading", { name: label })).toBeTruthy()
  expect(screen.getByText(/evaluator failed/)).toBeTruthy()
  expect(screen.getAllByText(/provider unavailable/).length).toBeGreaterThan(0)
  expect(screen.getByText(/Artistic warrant cannot verify/)).toBeTruthy()
  expect(screen.getByText("<belief_nucleate>inert quotation</belief_nucleate>")).toBeTruthy()
  expect(document.querySelector("belief_nucleate")).toBeNull()
  expect(document.querySelector("time")?.dateTime).toBe(item.timestamp)
  expect(screen.getByText(/"contradiction"/)).toBeTruthy()
})

it("V13 never invents five-part reasoning for a legacy event", () => {
  render(<ReviewReasoning item={{ ...item, kind: "legacy_event", reasoning: { encounter: null, claim_or_tension: null, comparison: null, consequence_or_challenge: null, decision_or_uncertainty: null } }} />)
  expect(screen.getAllByText("Unknown / not recorded")).toHaveLength(5)
})

it("V13 admission page requests the native receipt with the original agent and identity", async () => {
  render(<AdmissionReasoning agent="symbia" receipts={[{ id: "a1", agent_id: "symbia", assessment_id: "a1", encounter_id: "e1", status: "complete", statement: "claim", label: "claim", decision: "needs_review", reason: "advisory", created_at: item.timestamp!, policy_version: "v2", mode: "shadow", consequence: "", scope: "", temporal_scope: "", trigger: "", evidence_quote: "", source: { conversation_id: null, message_id: null, message_sha256: "", evidence_sha256: "" } }]} />)
  await screen.findByText("Receipt a1 · assessment")
  expect(String(fetchMock.mock.calls[0][0])).toContain("/api/beliefs/v2/agents/symbia/assessments/a1")
})

it("V13 page and workshop trace display the same decision receipt identity and timestamp", async () => {
  render(<TraceBeliefReasoning snippet={JSON.stringify(packet)} />)
  expect(fetchMock).not.toHaveBeenCalled()
  fireEvent.click(screen.getByText("Scoped decision receipt"))
  fireEvent.click(screen.getByText("Load recorded decision reasoning"))
  await screen.findByText("Receipt d1 · decision")
  expect(document.querySelector("time")?.dateTime).toBe(decisionItem.timestamp)
  expect(screen.getAllByText(/question remains useful/).length).toBeGreaterThan(0)
  expect(screen.getByRole("link", { name: "Open belief workshop" }).getAttribute("href")).toBe("/agent?tab=beliefs&agent=symbia&id=claim")
})

it("V10 V24 keeps counter-traces and family nominations after adoption with explicit bounds", async () => {
  showWorkshop({ ...view, record: { ...view.record, state: { state: "adopted", version: 4, scope: "practice" } }, family: [{ ...view.record, id: "peer", label: "Peer" }], counter_traces: [packet.counter_trace!], counter_trace_count: 53, counter_traces_truncated: true, history_truncated: true })
  await screen.findByText(/Review state: adopted/)
  expect(screen.getAllByText(/Scope too broad/).length).toBeGreaterThan(0)
  expect(screen.getByText(/Older counter-traces retained/)).toBeTruthy()
  expect(screen.getByText(/no equivalence, contradiction or merge verdict inferred/)).toBeTruthy()
  expect(screen.getByRole("button", { name: "[record decision]" })).toBeTruthy()
  expect(Array.from((screen.getByLabelText("Action") as HTMLSelectElement).options).map(option => option.value)).toEqual(["revise", "supersede", "resurface"])
})

it("V31 adopted commitments expose linked lineage and revision/resurface controls", async () => {
  const peerRecord = { ...view.record, id: "adopted-peer", label: "Adopted peer", state: { state: "adopted" as const, version: 2, scope: "practice" } }
  showWorkshop({ ...view, record: { ...view.record, kind: "belief", state: { state: "adopted", version: 4, scope: "practice" } }, family: [peerRecord], lineage_links: [{ source_record_id: "claim", successor_record_id: "adopted-peer", action: "revise", source_statement_sha256: "a".repeat(64), successor_statement_sha256: "b".repeat(64), command_id: "cmd1", decision_id: "d1", timestamp: item.timestamp! }], lineage_count: 1 })
  fireEvent.change(await screen.findByLabelText("Action"), { target: { value: "revise" } })
  expect(screen.getByLabelText("New candidate statement")).toBeTruthy()
  expect(screen.getByRole("link", { name: /Open linked record adopted-peer/ })).toBeTruthy()
  fireEvent.change(screen.getByLabelText("Action"), { target: { value: "supersede" } })
  expect(screen.getByLabelText("Adopted successor")).toBeTruthy()
  fireEvent.change(screen.getByLabelText("Action"), { target: { value: "resurface" } })
  expect(screen.getByText(/adds no assessment, warrant or mass/)).toBeTruthy()
})

it("V11 V13 binds decline to exact state/hash/version and preserves receipt on unchanged retry", async () => {
  showWorkshop()
  await fillDecision()
  let attempts = 0
  fetchMock.mockImplementation(async (_input: URL, init?: RequestInit) => {
    if (init?.method === "POST") {
      attempts += 1
      if (attempts === 1) throw new TypeError("Connection interrupted")
      return Response.json(packet)
    }
    return Response.json(view)
  })
  fireEvent.click(screen.getByRole("button", { name: "[record decision]" }))
  await screen.findByRole("alert")
  fireEvent.click(screen.getByRole("button", { name: "[record decision]" }))
  await screen.findByText(/Recorded decision d1/)
  const posts = fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")
  expect(posts).toHaveLength(2)
  expect(posts[0][1].headers["Idempotency-Key"]).toBe(posts[1][1].headers["Idempotency-Key"])
  const body = JSON.parse(posts[0][1].body)
  expect(body).toMatchObject({ action: "decline", expected_review_version: 3, expected_statement_sha256: "a".repeat(64), expected_state: "candidate", dissent: ["question remains useful"] })
  expect(body.actor).toBeUndefined()
  expect(body.assessment_ids).toEqual([])
})

it("V11 stale 409 blocks resubmission until refreshed version is read", async () => {
  showWorkshop()
  await fillDecision()
  fetchMock.mockImplementation(async (_input: URL, init?: RequestInit) => init?.method === "POST"
    ? Response.json({ message: "Stale workshop version" }, { status: 409 })
    : Response.json({ ...view, record: { ...view.record, state: { state: "under_review", version: 5, scope: "practice" } } }))
  fireEvent.click(screen.getByRole("button", { name: "[record decision]" }))
  await screen.findByText(/no overwrite occurred/)
  expect(screen.getByLabelText("Action").matches(":disabled")).toBe(true)
  fireEvent.click(screen.getByRole("button", { name: "[refresh changed record]" }))
  await screen.findByText(/version 5/)
})

it("V13 V20 ignores a late receipt from the previous agent and exposes failed reads", async () => {
  let resolveOld: (response: Response) => void = () => undefined
  fetchMock.mockImplementationOnce(() => new Promise<Response>(resolve => { resolveOld = resolve }))
  const { rerender } = render(<ReviewReceipt agent="symbia" resource="assessments" id="a1" />)
  fetchMock.mockResolvedValueOnce(Response.json({ message: "Unavailable" }, { status: 503 }))
  rerender(<ReviewReceipt agent="other" resource="assessments" id="a1" />)
  await screen.findByText(/Reasoning remains unknown/)
  resolveOld(Response.json(item))
  await waitFor(() => expect(screen.queryByText("Receipt a1 · assessment")).toBeNull())
})


it("V13 trace section and crease dropdown load the same actual decision endpoint", async () => {
  const notification = { id: "trace1", type: "trace" as const, timestamp: packet.decision.timestamp, snippet: JSON.stringify(packet), source: "belief_workshop_v2", sourceType: "belief_review", sourceId: "claim", read: false }
  vi.mocked(useNotifications).mockReturnValue([notification])
  const backend = { ...notification, source_type: "belief_review", source_id: "claim" }
  fetchMock.mockImplementation(async (input: URL) => {
    const path = String(input)
    return Response.json(path.includes("/decisions/") ? decisionItem : path.includes("/notifications/trace1") ? backend : [backend])
  })
  const trace = render(<TracesSection />)
  fireEvent.click(await screen.findByText("belief_workshop_v2"))
  fireEvent.click(await screen.findByText("Scoped decision receipt"))
  fireEvent.click(screen.getByText("Load recorded decision reasoning"))
  await screen.findByText("Receipt d1 · decision")
  expect(document.querySelector("time")?.dateTime).toBe(decisionItem.timestamp)
  trace.unmount()
  render(<CreasesDropdown conversations={[]} />)
  fireEvent.click(screen.getByRole("button", { name: "[creases]" }))
  fireEvent.click(screen.getByRole("button", { name: /traces/ }))
  fireEvent.click(screen.getByText("Scoped decision receipt"))
  fireEvent.click(screen.getByText("Load recorded decision reasoning"))
  await screen.findByText("Receipt d1 · decision")
  expect(document.querySelector("time")?.dateTime).toBe(decisionItem.timestamp)
  expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/agents/symbia/decisions/d1"))).toHaveLength(2)
})

it("V11 invalidates the stale form while refreshed state is still pending", async () => {
  showWorkshop()
  await fillDecision()
  fetchMock.mockResolvedValueOnce(Response.json({ message: "Stale version" }, { status: 409 }))
  fireEvent.click(screen.getByRole("button", { name: "[record decision]" }))
  await screen.findByText(/no overwrite occurred/)
  let resolveRefresh: (value: Response) => void = () => undefined
  fetchMock.mockImplementationOnce(() => new Promise<Response>(resolve => { resolveRefresh = resolve }))
  fireEvent.click(screen.getByRole("button", { name: "[refresh changed record]" }))
  expect(screen.queryByRole("button", { name: "[record decision]" })).toBeNull()
  resolveRefresh(Response.json(view))
  await screen.findByRole("button", { name: "[record decision]" })
})

it.each(["pending", "unavailable", "abstained"])("V13 keeps evaluator %s visible without adoption inference", status => {
  render(<ReviewReasoning item={{ ...item, record: { ...item.record, evaluator_status: status }, reasoning: { ...item.reasoning, decision_or_uncertainty: { evaluator_status: status } } }} />)
  expect(screen.getByText(`Provisional advisory assessment · evaluator ${status}`)).toBeTruthy()
  expect(screen.queryByText(/Scoped operator decision/)).toBeNull()
})


it("V11 refuses blank trimmed review fields before sending a command", async () => {
  showWorkshop()
  await fillDecision()
  fireEvent.change(screen.getByLabelText("Rationale"), { target: { value: "   " } })
  fireEvent.click(screen.getByRole("button", { name: "[record decision]" }))
  await screen.findByText(/must contain text/)
  expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0)
})

it("V13 V20 keeps a nondefault agent through deep-link list, receipt, decision and reload", async () => {
  const originalUrl = window.location.href
  window.history.replaceState(null, "", "/agent?tab=beliefs&agent=other&id=claim")
  const belief = { id: "claim", label: "Claim", statement: view.record.statement, category: "general", confidence: 0.61, ontological_mass: 0.19, version: 1, vector_16d: "[]", origin: "emergent", lifecycle_stage: "candidate", last_reinforced_at: null, updated_at: null, events: [], is_proposal: true, proposal_status: "pending", admission_history: [{ id: "a1", agent_id: "other", encounter_id: "e1", assessment_id: "a1" }] }
  fetchMock.mockImplementation(async (input: URL, init?: RequestInit) => {
    const path = new URL(String(input)).pathname
    if (init?.method === "POST") return Response.json({ ...packet, agent_id: "other" })
    if (path.endsWith("/review")) return Response.json({ ...view, agent_id: "other" })
    if (path.includes("/assessments/")) return Response.json(item)
    if (path.endsWith("/agent")) return Response.json({ name: "Symbia", agent_flux: true })
    return Response.json({ beliefs: [], proto_beliefs: [belief], ghosts: [], somatic: null, attractor_window: [], spectral_margin: [], ecosystem: null })
  })
  try {
    render(<BeliefsSection initialSelectedId="claim" />)
    await screen.findByText("Receipt a1 · assessment")
    await fillDecision()
    expect(screen.queryByRole("button", { name: "[+ add]" })).toBeNull()
    expect(screen.queryByRole("button", { name: "[ refine ]" })).toBeNull()
    fireEvent.click(screen.getByRole("button", { name: "[record decision]" }))
    await screen.findByText(/Recorded decision d1/)
    await waitFor(() => expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/beliefs?agent_id=other"))).toHaveLength(2))
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/agents/other/assessments/a1"))).toBe(true)
    expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith("/agents/other/records/claim/decisions") && init?.method === "POST")).toBe(true)
  } finally { window.history.replaceState(null, "", originalUrl) }
})
