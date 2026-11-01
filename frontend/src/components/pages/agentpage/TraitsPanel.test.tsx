import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, expect, it, vi } from "vitest"
import { getBeliefHealth } from "../../../api/client"
import { TraitsPanel } from "./TraitsPanel"

vi.mock("../../../api/client", () => ({
  getAgent: vi.fn().mockResolvedValue({ agent_flux: false }),
  getPersonality: vi.fn().mockResolvedValue({ aspirational_traits: { curiosity: 0.8 } }),
  getBeliefHealth: vi.fn().mockResolvedValue({ somatic: null, ecosystem: null }),
  updateAspirationalTraits: vi.fn(),
}))
vi.mock("./shared/HealthMetrics", () => ({ HealthMetrics: () => null }))
afterEach(cleanup)

it("loads health without downloading the full belief ledger", async () => {
  render(<TraitsPanel />)
  expect(await screen.findByText("Curiosity:")).toBeTruthy()
  expect(getBeliefHealth).toHaveBeenCalledOnce()
})
