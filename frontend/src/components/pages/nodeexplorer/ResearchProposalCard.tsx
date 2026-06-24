import { useState, useEffect, Children } from "react"
import { getResearchTask, approveProposal, rejectProposal } from "../../../api/client"

function parseProposalChildren(children: any) {
  const childrenArray = Children.toArray(children)
  let objective = ""
  let rationale = ""
  let depth = 2
  let breadth = 3
  let isAgonistic = false

  childrenArray.forEach((child: any) => {
    if (!child || typeof child !== 'object') return
    const tagName = child.type || child.props?.node?.tagName || ""
    const text = child.props?.children
      ? (Array.isArray(child.props.children) ? child.props.children.join("") : String(child.props.children))
      : (child.props?.node?.children?.[0]?.value || "")

    if (tagName === "objective") objective = text.trim()
    else if (tagName === "rationale") rationale = text.trim()
    else if (tagName === "suggested_depth" || tagName === "suggested-depth") depth = parseInt(text.trim()) || 2
    else if (tagName === "suggested_breadth" || tagName === "suggested-breadth") breadth = parseInt(text.trim()) || 3
    else if (tagName === "is_agonistic" || tagName === "is-agonistic") isAgonistic = text.trim().toLowerCase() === "true"
  })

  return { objective, rationale, depth, breadth, isAgonistic }
}

interface ResearchProposalCardProps {
  id?: string
  "data-id"?: string
  children?: any
}

export function ResearchProposalCard(props: ResearchProposalCardProps) {
  const proposalId = props.id || props["data-id"]
  const { objective, rationale, depth, breadth, isAgonistic } = parseProposalChildren(props.children)

  const [status, setStatus] = useState<string>("proposed")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!proposalId) return
    getResearchTask(proposalId)
      .then((task) => {
        if (task && task.status) {
          setStatus(task.status)
        }
      })
      .catch((err) => {
        console.warn("Failed to fetch initial status for proposal:", proposalId, err)
      })
  }, [proposalId])

  const handleApprove = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!proposalId) return
    setLoading(true)
    setError(null)
    try {
      await approveProposal(proposalId)
      setStatus("queued")
    } catch (err: any) {
      setError(err.message || "Failed to approve")
    } finally {
      setLoading(false)
    }
  }

  const handleReject = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!proposalId) return
    setLoading(true)
    setError(null)
    try {
      await rejectProposal(proposalId)
      setStatus("rejected")
    } catch (err: any) {
      setError(err.message || "Failed to reject")
    } finally {
      setLoading(false)
    }
  }

  const estCost = (0.025 * depth * breadth).toFixed(2)

  return (
    <div className="border-l-2 border-semantic-gold pl-3 py-1.5 my-3 flex flex-col gap-1 select-none">
      <div className="text-[10px] text-semantic-gold font-mono font-bold tracking-wider uppercase">
        🔬 Symbia Proposes Research
      </div>
      {objective && (
        <div className="text-ui-primary text-xs font-mono italic my-0.5">
          "{objective}"
        </div>
      )}
      {rationale && (
        <div className="text-ui-secondary text-[11px] font-sans">
          {rationale}
        </div>
      )}
      <div className="text-ui-dim text-[10px] font-mono flex flex-wrap gap-x-2 gap-y-0.5">
        <span>Depth: {depth}</span>
        <span>·</span>
        <span>Breadth: {breadth}</span>
        <span>·</span>
        <span>Est. ${estCost}</span>
        {isAgonistic && (
          <>
            <span>·</span>
            <span className="text-semantic-purple">Agonistic</span>
          </>
        )}
      </div>

      {error && (
        <div className="text-semantic-red text-[10px] font-mono mt-0.5">
          Error: {error}
        </div>
      )}

      <div className="flex items-center gap-4 mt-1 font-mono text-[10px]">
        {loading ? (
          <span className="text-ui-dim animate-pulse">Processing...</span>
        ) : status === "proposed" ? (
          <>
            <button
              onClick={handleApprove}
              className="text-action-dim hover:text-action-hover cursor-pointer"
            >
              [✓ Approve & dispatch]
            </button>
            <button
              onClick={handleReject}
              className="text-action-dim hover:text-semantic-red cursor-pointer"
            >
              [✗ Dismiss]
            </button>
          </>
        ) : status === "queued" ? (
          <span className="text-semantic-gold">[✓ Approved & queued]</span>
        ) : status === "active" ? (
          <span className="text-semantic-gold animate-pulse">[✓ Approved & active...]</span>
        ) : status === "completed" ? (
          <span className="text-semantic-green">
            [✓ Completed · <a href={`/research?id=${proposalId}`} className="underline hover:text-action-hover font-mono">View Report</a>]
          </span>
        ) : status === "rejected" ? (
          <span className="text-ui-dim">[✗ Dismissed]</span>
        ) : status === "expired" ? (
          <span className="text-ui-dim">[✗ Expired]</span>
        ) : status === "failed" ? (
          <span className="text-semantic-red">[✗ Failed]</span>
        ) : (
          <span className="text-ui-secondary">[{status}]</span>
        )}
      </div>
    </div>
  )
}
