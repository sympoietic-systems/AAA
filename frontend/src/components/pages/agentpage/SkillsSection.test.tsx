import { render, screen, fireEvent, act, cleanup } from "@testing-library/react"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { SkillsSection } from "./SkillsSection"
import { getSkillContent } from "../../../api/client"
vi.mock("../../../api/client", () => ({ getSkillContent: vi.fn(), getAgent: vi.fn().mockResolvedValue({ agent_flux: false }) }))
vi.mock("../../../api/skills", () => ({ getDbSkillSummaries: vi.fn().mockResolvedValue({
  always_active: [], on_demand: ["a", "b"].map(name => ({ id: name, name, content_loaded: false })), all: []
}) }))
vi.mock("./skills/SkillListItem", () => ({ SkillListItem: ({ s }: { s: { name: string } }) => <button data-skill-name={s.name}>{s.name}</button> }))
vi.mock("./skills/SkillDetail", () => ({ SkillDetail: ({ skill, content, loading, contentError }: { skill?: { name: string }; content?: string; loading: boolean; contentError?: string }) =>
  <div data-testid="detail">{JSON.stringify({ name: skill?.name, content, loading, contentError })}</div> }))
function deferred() { let resolve!: (value: { content: string; status: string }) => void; const promise = new Promise<{ content: string; status: string }>(r => { resolve = r }); return { promise, resolve } }
beforeEach(() => { vi.clearAllMocks(); vi.stubGlobal("matchMedia", () => ({ matches: false })) })
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
it("keeps content and loading owned by the selected skill when responses arrive out of order", async () => {
  const a = deferred(), b = deferred()
  vi.mocked(getSkillContent).mockReturnValueOnce(a.promise).mockReturnValueOnce(b.promise)
  render(<SkillsSection />)
  fireEvent.click(await screen.findByText("a")); fireEvent.click(screen.getByText("b"))
  await act(async () => { a.resolve({ content: "A", status: "loaded" }) })
  expect(screen.getByTestId("detail").textContent).toContain('"name":"b"')
  expect(screen.getByTestId("detail").textContent).toContain('"loading":true')
  expect(screen.getByTestId("detail").textContent).not.toContain('"content":"A"')
  await act(async () => { b.resolve({ content: "", status: "loaded" }) })
  expect(screen.getByTestId("detail").textContent).toContain('"content":""')
  expect(screen.getByTestId("detail").textContent).toContain('"loading":false')
})
it("keeps a failed load separate from editable content", async () => {
  vi.mocked(getSkillContent).mockRejectedValueOnce(new Error("offline"))
  render(<SkillsSection />)
  fireEvent.click(await screen.findByText("a"))
  await act(async () => {})
  expect(screen.getByTestId("detail").textContent).toContain('"contentError":"Failed to load content: offline"')
  expect(screen.getByTestId("detail").textContent).not.toContain('"content":')
})
