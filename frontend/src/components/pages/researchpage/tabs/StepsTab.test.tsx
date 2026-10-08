import { render, waitFor, cleanup, act } from "@testing-library/react"
import { afterEach, expect, it, vi } from "vitest"
import { StepsTab } from "./StepsTab"
import { getTaskSteps } from "../../../../api/research"
import { sourceStatusLabel } from "../steps/results/helpers"

vi.mock("../../../../api/research", () => ({
  getTaskSteps: vi.fn().mockResolvedValue({ steps: [] }),
  getStepPreview: vi.fn().mockResolvedValue(null),
  executeStep: vi.fn(), rerunTask: vi.fn(), reinitializeTask: vi.fn(),
}))
vi.mock("../steps/StepPipeline", () => ({
  StepPipeline: ({ data }: { data: { steps: { status: string }[] } | null }) => <span data-testid="pipeline-status">{data?.steps[0]?.status}</span>,
}))
vi.mock("../steps/StepDetailPanel", () => ({ StepDetailPanel: () => null }))
afterEach(() => { cleanup(); vi.clearAllMocks() })

it("refreshes terminal steps when active research becomes partial", async () => {
  const view = render(<StepsTab taskId="fixture" orchPhase="digesting" taskStatus="active" />)
  await waitFor(() => expect(getTaskSteps).toHaveBeenCalledTimes(1))
  view.rerender(<StepsTab taskId="fixture" orchPhase="complete" taskStatus="partial" />)
  await waitFor(() => expect(getTaskSteps).toHaveBeenCalledTimes(2))
})

it("displays a failed analysis explicitly instead of counting its explanatory gap as a research result", () => {
  expect(sourceStatusLabel({ analysis_status: "failed", learnings: [], gaps: ["Provider unavailable"] }).label).toBe("analysis failed")
})

it("keeps terminal steps when an older running-state request returns later", async () => {
  let resolveOlder!: (value: Awaited<ReturnType<typeof getTaskSteps>>) => void
  vi.mocked(getTaskSteps).mockImplementationOnce(() => new Promise(resolve => { resolveOlder = resolve }))
  vi.mocked(getTaskSteps).mockResolvedValueOnce({ steps: [{ status: "failed" }] } as Awaited<ReturnType<typeof getTaskSteps>>)
  const view = render(<StepsTab taskId="fixture" orchPhase="digesting" taskStatus="active" />)
  view.rerender(<StepsTab taskId="fixture" orchPhase="complete" taskStatus="partial" />)
  await waitFor(() => expect(view.getByTestId("pipeline-status").textContent).toBe("failed"))
  await act(async () => { resolveOlder({ steps: [{ status: "running" }] } as Awaited<ReturnType<typeof getTaskSteps>>) })
  expect(view.getByTestId("pipeline-status").textContent).toBe("failed")
})
