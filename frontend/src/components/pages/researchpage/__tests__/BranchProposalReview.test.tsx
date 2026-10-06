import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { BranchProposalReview } from "../BranchProposalReview"
import type { BranchProposal } from "../../../../api/research"

const { getBranchProposal, approveBranchProposal, declineBranchProposal } = vi.hoisted(() => ({
  getBranchProposal: vi.fn(), approveBranchProposal: vi.fn(), declineBranchProposal: vi.fn(),
}))
vi.mock("../../../../api/research", () => ({ getBranchProposal, approveBranchProposal, declineBranchProposal }))

const proposal: BranchProposal = {
  proposal_id: "proposal", task_id: "task", parent_objective: "Parent question", expires_at: "2026-10-06T02:00:00Z", status: "pending", approved_scopes: null,
  draft: {
    question: "Compare requirements", rationale: "Source-backed different validation norms", cut_kind: "validation_norm", overlap: "Shared question", risk: "Fragmentation", parent_attempt_reserve: 8, parent_budget_reserve_usd: .1,
    scopes: [
      { scope_id: "a", question: "Experimental claims", retrieval_vocabulary: ["experiment"], validation_norm: "Replication", attempt_allocation: 8, budget_allocation_usd: .1 },
      { scope_id: "b", question: "Interpretive claims", retrieval_vocabulary: ["interpretation"], validation_norm: "Situated reading", attempt_allocation: 8, budget_allocation_usd: .1 },
    ],
  },
  witnesses: [{ segment_id: "segment", text: "Exact source quotation", source_url: "https://fixture.test/evidence", source_version: "version", representation: "sensory_text_v1", warnings: ["original_bytes_unavailable"] }],
}

describe("BranchProposalReview", () => {
  afterEach(cleanup)
  beforeEach(() => {
    vi.clearAllMocks()
    getBranchProposal.mockResolvedValue(proposal)
    approveBranchProposal.mockResolvedValue({ ...proposal, status: "approved" })
    declineBranchProposal.mockResolvedValue({ ...proposal, status: "declined" })
  })
  it("requires human acknowledgement and sends edited scopes", async () => {
    const resolved = vi.fn()
    render(<BranchProposalReview taskId="task" status="waiting_for_branch_approval" onResolved={resolved} />)
    const approve = await screen.findByRole("button", { name: "Approve edited scopes" })
    expect(approve).toBeDisabled()
    fireEvent.change(screen.getAllByLabelText("Question")[0], { target: { value: "Narrower experimental question" } })
    fireEvent.change(screen.getAllByLabelText("Retrieval vocabulary (comma separated)")[0], { target: { value: "experiment, replication" } })
    fireEvent.click(screen.getByRole("checkbox"))
    fireEvent.click(approve)
    await waitFor(() => expect(resolved).toHaveBeenCalledOnce())
    expect(approveBranchProposal.mock.calls[0][2][0].question).toBe("Narrower experimental question")
    expect(approveBranchProposal.mock.calls[0][2][0].retrieval_vocabulary).toEqual(["experiment", "replication"])
    expect(screen.getByText("Exact source quotation")).toBeInTheDocument()
  })
  it("declines without child approval and surfaces errors", async () => {
    declineBranchProposal.mockRejectedValue(new Error("Proposal already resolved"))
    render(<BranchProposalReview taskId="task" status="waiting_for_branch_approval" onResolved={vi.fn()} />)
    fireEvent.click(await screen.findByRole("button", { name: "Decline and continue one line" }))
    expect(await screen.findByRole("alert")).toHaveTextContent("Proposal already resolved")
    expect(approveBranchProposal).not.toHaveBeenCalled()
  })
  it("ignores a source response owned by an earlier task", async () => {
    let finish: (value: BranchProposal) => void = () => {}
    getBranchProposal.mockImplementationOnce(() => new Promise<BranchProposal>(resolve => { finish = resolve }))
    getBranchProposal.mockResolvedValueOnce({ ...proposal, task_id: "other", parent_objective: "Other parent" })
    const view = render(<BranchProposalReview taskId="task" status="waiting_for_branch_approval" onResolved={vi.fn()} />)
    view.rerender(<BranchProposalReview taskId="other" status="waiting_for_branch_approval" onResolved={vi.fn()} />)
    await screen.findByText("Parent objective: Other parent")
    await act(async () => { finish(proposal) })
    expect(screen.queryByText("Parent objective: Parent question")).not.toBeInTheDocument()
  })
  it("cannot approve a proposal on a terminal parent", async () => {
    render(<BranchProposalReview taskId="task" status="cancelled" onResolved={vi.fn()} />)
    expect(await screen.findByRole("button", { name: "Approve edited scopes" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Decline and continue one line" })).toBeDisabled()
  })
})
