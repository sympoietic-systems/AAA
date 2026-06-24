import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { ResearchProposalCard } from '../ResearchProposalCard'

const { getResearchTask, approveProposal, rejectProposal } = vi.hoisted(() => ({
  getResearchTask: vi.fn().mockResolvedValue({ status: 'proposed' }),
  approveProposal: vi.fn().mockResolvedValue(undefined),
  rejectProposal: vi.fn().mockResolvedValue(undefined),
}))

vi.mock('../../../../api/client', () => ({
  getResearchTask,
  approveProposal,
  rejectProposal,
}))

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function el(type: string, text: string) {
  return createElement(type, {}, text)
}

describe('ResearchProposalCard', () => {
  it('renders the proposal header', async () => {
    render(<ResearchProposalCard id="r1" />)
    await waitFor(() => {
      expect(screen.getByText(/Symbia Proposes Research/)).toBeInTheDocument()
    })
  })

  it('parses objective from child elements', async () => {
    const objective = el('objective', 'Test the system')
    render(<ResearchProposalCard id="r1">{objective}</ResearchProposalCard>)
    await waitFor(() => {
      expect(screen.getByText(/"Test the system"/)).toBeInTheDocument()
    })
  })

  it('parses rationale from child elements', async () => {
    const rationale = el('rationale', 'Because it is needed')
    render(<ResearchProposalCard id="r1">{rationale}</ResearchProposalCard>)
    await waitFor(() => {
      expect(screen.getByText('Because it is needed')).toBeInTheDocument()
    })
  })

  it('shows approve and dismiss buttons when proposed', async () => {
    getResearchTask.mockResolvedValue({ status: 'proposed' })
    render(<ResearchProposalCard id="r1" />)
    await waitFor(() => {
      expect(screen.getByText(/Approve & dispatch/)).toBeInTheDocument()
      expect(screen.getByText(/Dismiss/)).toBeInTheDocument()
    })
  })

  it('calls approveProposal on approve click', async () => {
    render(<ResearchProposalCard id="r1" />)
    await waitFor(() => {
      fireEvent.click(screen.getByText(/Approve & dispatch/))
    })
    expect(approveProposal).toHaveBeenCalledWith('r1')
  })

  it('shows queued status after approve', async () => {
    approveProposal.mockResolvedValue(undefined)
    render(<ResearchProposalCard id="r1" />)
    await waitFor(() => {
      fireEvent.click(screen.getByText(/Approve & dispatch/))
    })
    await waitFor(() => {
      expect(screen.getByText(/Approved & queued/)).toBeInTheDocument()
    })
  })

  it('parses depth and breadth from child elements', async () => {
    render(
      <ResearchProposalCard id="r1">
        {el('suggested_depth', '4')}
        {el('suggested_breadth', '5')}
      </ResearchProposalCard>
    )
    await waitFor(() => {
      expect(screen.getByText('Depth: 4')).toBeInTheDocument()
      expect(screen.getByText('Breadth: 5')).toBeInTheDocument()
    })
  })
})
