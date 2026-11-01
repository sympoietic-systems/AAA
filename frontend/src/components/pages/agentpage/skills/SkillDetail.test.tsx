import { render, screen, fireEvent, cleanup } from "@testing-library/react"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { SkillDetail } from "./SkillDetail"
import type { DbSkillInfo } from "../../../../api/types"
import { updateSkill } from "../../../../api/client"

vi.mock("../../../../api/http", () => ({ apiFetch: vi.fn().mockResolvedValue({ json: async () => ({ versions: [] }) }) }))
vi.mock("../../../../api/client", () => ({ updateSkill: vi.fn().mockResolvedValue({}), deleteSkill: vi.fn() }))
const skill = { id: "one", name: "one", description: "Description", trigger_keywords: [], vector_16d: [],
  lifecycle_stage: "crystallized", confidence: .8, ontological_mass: 1 } as unknown as DbSkillInfo
const props = { skill, onUpdate: vi.fn(), onDelete: vi.fn(), agentFlux: true }
beforeEach(() => vi.clearAllMocks())
afterEach(cleanup)
it("blocks editing while loading or failed, and allows legitimate empty content", async () => {
  const view = render(<SkillDetail {...props} loading />)
  expect((screen.getByText("[edit]") as HTMLButtonElement).disabled).toBe(true)
  view.rerender(<SkillDetail {...props} loading={false} contentError="Load failed" />)
  expect((screen.getByText("[edit]") as HTMLButtonElement).disabled).toBe(true)
  fireEvent.click(screen.getByText("[edit]"))
  expect(updateSkill).not.toHaveBeenCalled()
  view.rerender(<SkillDetail {...props} loading={false} content="" />)
  expect((screen.getByText("[edit]") as HTMLButtonElement).disabled).toBe(false)
  fireEvent.click(screen.getByText("[edit]"))
  fireEvent.click(screen.getByText("[save]"))
  expect(updateSkill).toHaveBeenCalledWith("one", expect.objectContaining({ content: "" }))
})
