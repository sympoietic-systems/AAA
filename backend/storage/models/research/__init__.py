"""Research domain storage models and persistence contracts."""

from backend.storage.models.research.acquisition import AcquisitionReceipt
from backend.storage.models.research.branch_proposal import (
    BranchProposal,
    BranchProposalDraft,
    BranchScope,
)
from backend.storage.models.research.children import ChildEvidencePacket
from backend.storage.models.research.entities import (
    ResearchBranch,
    ResearchTask,
    ScrapedAsset,
)
from backend.storage.models.research.evidence import (
    ClaimEvidence,
    EvidenceBundle,
    ResearchContract,
    SourceArtifact,
    SourceReference,
    SourceSnapshot,
)
from backend.storage.models.research.receipts import (
    ActionObservation,
    ActionStatus,
    EvidencePacket,
    ProviderAttemptReceipt,
    ReceiptModel,
    ResearchActionReceipt,
)

__all__ = [
    "ResearchTask",
    "ResearchBranch",
    "ScrapedAsset",
    "ReceiptModel",
    "ProviderAttemptReceipt",
    "EvidencePacket",
    "ActionObservation",
    "ResearchActionReceipt",
    "ActionStatus",
    "AcquisitionReceipt",
    "BranchScope",
    "BranchProposalDraft",
    "BranchProposal",
    "EvidenceBundle",
    "ClaimEvidence",
    "SourceReference",
    "SourceArtifact",
    "SourceSnapshot",
    "ResearchContract",
    "ChildEvidencePacket",
]
