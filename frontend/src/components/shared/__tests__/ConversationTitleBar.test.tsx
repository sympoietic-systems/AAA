import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { ConversationTitleBar } from '../ConversationTitleBar'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('ConversationTitleBar', () => {
  const defaultProps = {
    title: 'Test Entanglement',
    onRename: vi.fn(),
    onGenerateTitle: vi.fn(),
  }

  it('renders title text in desktop variant', () => {
    render(<ConversationTitleBar {...defaultProps} />)
    expect(screen.getByText('Test Entanglement')).toBeInTheDocument()
  })

  it('shows fallback title when title is empty', () => {
    render(<ConversationTitleBar {...defaultProps} title="" />)
    expect(screen.getByText('Untitled Entanglement')).toBeInTheDocument()
  })

  it('shows edit form when title is clicked', () => {
    render(<ConversationTitleBar {...defaultProps} />)
    fireEvent.click(screen.getByText('Test Entanglement'))
    const input = screen.getByRole('textbox')
    expect(input).toBeInTheDocument()
    expect(input).toHaveValue('Test Entanglement')
  })

  it('calls onGenerateTitle when button is clicked', () => {
    const onGenerateTitle = vi.fn()
    render(<ConversationTitleBar {...defaultProps} onGenerateTitle={onGenerateTitle} />)
    fireEvent.click(screen.getByTitle('Auto-generate title'))
    expect(onGenerateTitle).toHaveBeenCalled()
  })

  it('calls onRename when editing is submitted', () => {
    const onRename = vi.fn()
    render(
      <ConversationTitleBar {...defaultProps} onRename={onRename} />
    )
    fireEvent.click(screen.getByText('Test Entanglement'))
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'New Title' } })
    fireEvent.blur(input)
    expect(onRename).toHaveBeenCalledWith('New Title')
  })

  it('renders mobile variant with title label prefix', () => {
    render(<ConversationTitleBar {...defaultProps} variant="mobile" />)
    expect(screen.getByText('title:')).toBeInTheDocument()
    expect(screen.getByText('Test Entanglement')).toBeInTheDocument()
  })

  it('renders export button in mobile variant when conversationId provided', () => {
    const onExport = vi.fn()
    render(
      <ConversationTitleBar
        {...defaultProps}
        variant="mobile"
        conversationId="c1"
        onExport={onExport}
      />
    )
    expect(screen.getByTitle('Export conversation as Markdown')).toBeInTheDocument()
  })

  it('does not render export button without conversationId', () => {
    render(<ConversationTitleBar {...defaultProps} variant="mobile" />)
    expect(screen.queryByTitle('Export conversation as Markdown')).not.toBeInTheDocument()
  })
})
