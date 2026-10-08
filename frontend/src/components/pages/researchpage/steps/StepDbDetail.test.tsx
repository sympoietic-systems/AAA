import { cleanup, fireEvent, render, waitFor } from "@testing-library/react"
import { afterEach, expect, it, vi } from "vitest"
import type { TaskStepsResponse } from "../../../../api/research"
import { DbStepDetail } from "./StepDbDetail"
import { executeStep } from "../../../../api/research"

vi.mock("../../../../api/research", () => ({
  getTaskMetaLog: vi.fn().mockResolvedValue({ entries: [] }),
  getStepPreview: vi.fn(), executeStep: vi.fn(), reinitializeTask: vi.fn(),
}))
vi.mock("../../../../hooks/useNotes", () => ({ useNotes: () => ({ notes: [] }) }))
vi.mock("./StepResultTab", () => ({ StepResultTab: () => null }))
vi.mock("./StepInputTab", () => ({ StepInputTab: () => null }))
vi.mock("./StepLogTab", () => ({ StepLogTab: () => null }))
vi.mock("../../../shared/NotesSection", () => ({ NotesSection: () => null }))

afterEach(cleanup)

it("renders empty failed-step tabs without undefined counts", async () => {
  const data = {
    steps: [{ id: "step", step_number: 2, step_type: "search", status: "failed", step_data: "{}" }],
    results_by_step: {}, plan: null,
  } as unknown as TaskStepsResponse
  const view = render(<DbStepDetail taskId="task" selectedId="step" data={data} />)
  await waitFor(() => expect(view.getByRole("button", { name: "input" })).toBeTruthy())
  for (const label of ["result", "log", "notes"]) expect(view.getByRole("button", { name: label })).toBeTruthy()
  expect(view.container.textContent).not.toContain("undefined")
  vi.mocked(executeStep).mockRejectedValueOnce(new Error("A research phase is already running; wait for it to finish."))
  fireEvent.click(view.getByRole("button", { name: /rerun step/ }))
  await waitFor(() => expect(view.getByRole("alert").textContent).toContain("already running"))
})
