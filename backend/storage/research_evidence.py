"""Evidence identities and coordinate systems; location never certifies support."""

import hashlib
import json
from typing import Literal
from urllib.parse import quote

from pydantic import AwareDatetime, Field, model_validator

from backend.storage.research_receipts import ReceiptModel


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class RubricItem(ReceiptModel):
    rubric_id: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    hard: bool = True


class ResearchContract(ReceiptModel):
    task_id: str
    revision: int = Field(default=1, ge=1)
    objective: str = Field(min_length=1, max_length=50000)
    subquestion_ids: tuple[str, ...] = Field(default=(), max_length=50)
    scope: str | None = Field(default=None, max_length=10000)
    date_boundary: str | None = Field(default=None, max_length=200)
    rubric: tuple[RubricItem, ...] = Field(default=(), max_length=50)
    source_constraints: dict[str, str] = Field(default_factory=dict, max_length=50)
    mode: Literal["research", "document"] = "research"
    resource_ceilings: dict[str, float] = Field(default_factory=dict, max_length=50)
    policy_version: int = Field(ge=1)

    def content_hash(self) -> str:
        return text_hash(json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")))

    @model_validator(mode="after")
    def validate_resources(self) -> "ResearchContract":
        if any(value < 0 for value in self.resource_ceilings.values()):
            raise ValueError("Resource ceilings cannot be negative")
        if len({item.rubric_id for item in self.rubric}) != len(self.rubric):
            raise ValueError("Rubric identities must be unique")
        return self


class ParserQuality(ReceiptModel):
    method: str | None = Field(default=None, max_length=200)
    parser_version: str | None = Field(default=None, max_length=200)
    config_hash: str | None = None
    score: float | None = Field(default=None, ge=0, le=1)
    ocr_used: bool | None = None
    layout_preserved: bool | None = None
    warnings: tuple[str, ...] = Field(default=(), max_length=50)


class SourceReference(ReceiptModel):
    source_id: str
    source_version: str


class SourceArtifact(SourceReference):
    task_id: str
    canonical_url: str | None = Field(default=None, max_length=8192)
    authorized_file_id: str | None = None
    acquired_at: AwareDatetime | None = None
    publication_date: str | None = None
    original_byte_hash: str | None = None
    representation: str = Field(min_length=1, max_length=200)
    representation_hash: str | None = None
    mime_type: str | None = None
    fetch_status: Literal["available", "unavailable", "blocked", "failed"]
    unavailable_reason: str | None = Field(default=None, max_length=2000)
    raw_artifact_ref: str | None = None
    quality: ParserQuality = Field(default_factory=ParserQuality)


class EvidenceSegment(ReceiptModel):
    task_id: str
    segment_id: str
    source_id: str
    source_version: str
    representation: str
    coordinate_system: Literal["representation_characters", "raw_bytes"] = "representation_characters"
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=10000)
    text_hash: str
    heading_path: tuple[str, ...] = ()
    page: int | None = Field(default=None, ge=1)
    dom_locator: str | None = None
    table_cells: tuple[tuple[str, ...], ...] = ()
    quality: ParserQuality = Field(default_factory=ParserQuality)

    @model_validator(mode="after")
    def validate_span(self) -> "EvidenceSegment":
        if self.end <= self.start or self.text_hash != text_hash(self.text):
            raise ValueError("Evidence span or text hash is invalid")
        if self.coordinate_system == "representation_characters" and self.end - self.start != len(self.text):
            raise ValueError("Character span must match exact text length")
        return self

    def locator(self) -> str:
        return f"evidence://{quote(self.source_id, safe='')}/{quote(self.source_version, safe='')}/{quote(self.segment_id, safe='')}"


class ClaimEvidence(ReceiptModel):
    task_id: str
    claim_id: str
    contract_revision: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=10000)
    rubric_ids: tuple[str, ...] = Field(default=(), max_length=50)
    supporting_segment_ids: tuple[str, ...] = Field(default=(), max_length=50)
    contrary_segment_ids: tuple[str, ...] = Field(default=(), max_length=50)
    source_lineage: tuple[SourceReference, ...] = Field(default=(), max_length=50)
    temporal_scope: str | None = None
    inference_label: Literal["source_quote", "interpretation", "inference"] = "interpretation"
    citation_status: Literal["absent", "resolvable"] = "absent"
    support_status: Literal["unverified", "supported", "disputed", "rejected"] = "unverified"
    reviewed_by: str | None = None
    unresolved_objections: tuple[str, ...] = Field(default=(), max_length=50)

    @model_validator(mode="after")
    def validate_support(self) -> "ClaimEvidence":
        if set(self.supporting_segment_ids) & set(self.contrary_segment_ids):
            raise ValueError("One segment cannot be both supporting and contrary")
        if self.support_status != "unverified" and not self.reviewed_by:
            raise ValueError("Semantic adjudication requires an identified reviewer")
        if self.support_status == "supported" and not self.supporting_segment_ids:
            raise ValueError("Supported claim requires resolvable supporting evidence")
        if self.citation_status == "resolvable" and not (self.supporting_segment_ids or self.contrary_segment_ids):
            raise ValueError("Resolvable citation requires a segment reference")
        return self


class EvidenceExclusion(ReceiptModel):
    candidate_id: str
    reason: Literal[
        "contradicts_claim",
        "out_of_scope",
        "low_relevance",
        "parse_degraded",
        "byte_unknown",
        "no_anchor_in_legacy",
        "unavailable",
    ]
    explanation: str = Field(min_length=1, max_length=2000)


class DecisionReceipt(ReceiptModel):
    task_id: str
    decision_id: str
    action_id: str
    input_hash: str
    contract_hash: str
    policy_hash: str
    allowed_actions: tuple[str, ...] = Field(max_length=50)
    candidate_ids: tuple[str, ...] = Field(max_length=100)
    selected_ids: tuple[str, ...] = Field(default=(), max_length=100)
    exclusions: tuple[EvidenceExclusion, ...] = Field(default=(), max_length=100)
    abstained: bool = False
    fallback_reason: str | None = None
    model: str | None = None
    elapsed_seconds: float | None = Field(default=None, ge=0)
    token_usage: dict[str, int] | None = None
    known_cost_usd: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_candidates(self) -> "DecisionReceipt":
        candidates = set(self.candidate_ids)
        if not set(self.selected_ids) <= candidates or not {e.candidate_id for e in self.exclusions} <= candidates:
            raise ValueError("Decision references candidates not observed at its boundary")
        if set(self.selected_ids) & {e.candidate_id for e in self.exclusions}:
            raise ValueError("Excluded candidate cannot also be selected")
        return self


class SourceSnapshot(ReceiptModel):
    artifact: SourceArtifact
    representation_text: str = Field(max_length=2_000_000)


class EvidenceBundle(ReceiptModel):
    schema_version: Literal[1] = 1
    task_id: str
    contracts: tuple[ResearchContract, ...] = Field(default=(), max_length=100)
    sources: tuple[SourceSnapshot, ...] = Field(default=(), max_length=1000)
    segments: tuple[EvidenceSegment, ...] = Field(default=(), max_length=5000)
    claims: tuple[ClaimEvidence, ...] = Field(default=(), max_length=5000)
    decisions: tuple[DecisionReceipt, ...] = Field(default=(), max_length=5000)

    @model_validator(mode="after")
    def validate_graph(self) -> "EvidenceBundle":
        sources = {(item.artifact.source_id, item.artifact.source_version): item for item in self.sources}
        segments = {item.segment_id: item for item in self.segments}
        contracts = {item.revision: item for item in self.contracts}
        if (
            len(sources) != len(self.sources)
            or len(segments) != len(self.segments)
            or len(contracts) != len(self.contracts)
        ):
            raise ValueError("Evidence bundle contains duplicate identities")
        if sum(len(item.representation_text) for item in self.sources) > 20_000_000:
            raise ValueError("Evidence bundle exceeds text limit")
        records: tuple[ResearchContract | SourceArtifact | EvidenceSegment | ClaimEvidence | DecisionReceipt, ...] = (
            *self.contracts,
            *(s.artifact for s in self.sources),
            *self.segments,
            *self.claims,
            *self.decisions,
        )
        if any(record.task_id != self.task_id for record in records):
            raise ValueError("Evidence bundle crosses task boundaries")
        for source in self.sources:
            expected = text_hash(source.representation_text) if source.representation_text else None
            if source.artifact.representation_hash != expected:
                raise ValueError("Evidence bundle source text changed")
        for segment in self.segments:
            segment_source = sources.get((segment.source_id, segment.source_version))
            if (
                segment_source is None
                or segment.coordinate_system != "representation_characters"
                or segment_source.representation_text[segment.start : segment.end] != segment.text
            ):
                raise ValueError("Evidence bundle segment does not resolve")
            if (
                segment.representation != segment_source.artifact.representation
                or segment.quality != segment_source.artifact.quality
            ):
                raise ValueError("Evidence bundle changed parser provenance")
        for claim in self.claims:
            contract = contracts.get(claim.contract_revision)
            lineage = {(ref.source_id, ref.source_version) for ref in claim.source_lineage}
            if (
                contract is None
                or not set(claim.rubric_ids) <= {item.rubric_id for item in contract.rubric}
                or not lineage <= sources.keys()
            ):
                raise ValueError("Evidence bundle claim has unknown lineage or contract")
            references = claim.supporting_segment_ids + claim.contrary_segment_ids
            if bool(references) != (claim.citation_status == "resolvable"):
                raise ValueError("Evidence bundle citation status differs from references")
            if any(
                ref not in segments or (segments[ref].source_id, segments[ref].source_version) not in lineage
                for ref in references
            ):
                raise ValueError("Evidence bundle claim refers to unknown evidence")
        return self

    def resolve(self, segment_id: str) -> tuple[SourceArtifact, EvidenceSegment]:
        segment = next((item for item in self.segments if item.segment_id == segment_id), None)
        if segment is None:
            raise ValueError("Unknown evidence segment")
        source = next(
            item.artifact
            for item in self.sources
            if (item.artifact.source_id, item.artifact.source_version) == (segment.source_id, segment.source_version)
        )
        return source, segment

    def resolve_locator(self, locator: str) -> tuple[SourceArtifact, EvidenceSegment]:
        """Resolve the exact exported URI without network or database access."""
        for segment in self.segments:
            if segment.locator() == locator:
                return self.resolve(segment.segment_id)
        raise ValueError("Unknown evidence locator")
