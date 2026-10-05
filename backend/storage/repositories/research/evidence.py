"""Immutable, task-scoped evidence. SQL validates lineage and exact spans."""

import json
from datetime import UTC, datetime
from typing import Any

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository
from backend.storage.repositories.research.action_receipt import ReceiptConflictError
from backend.storage.research_evidence import (
    ClaimEvidence,
    DecisionReceipt,
    EvidenceBundle,
    EvidenceSegment,
    ResearchContract,
    SourceArtifact,
    text_hash,
)


class ResearchEvidenceRepository(BaseRepository):
    @with_connection
    def preserve_import(self, task_id: str, bundle: EvidenceBundle) -> None:
        """Archive foreign provenance without creating local execution authority."""
        payload = bundle.model_dump_json()
        if len(payload) > 20_000_000:
            raise ReceiptConflictError("Imported evidence exceeds payload limit")
        with self.atomic():
            row = (
                self._conn()
                .execute("SELECT bundle_json FROM research_imported_evidence WHERE task_id=?", (task_id,))
                .fetchone()
            )
            if row:
                if row[0] != payload:
                    raise ReceiptConflictError("Imported provenance is immutable")
                return
            self._conn().execute(
                "INSERT INTO research_imported_evidence VALUES (?, ?, ?)",
                (task_id, bundle.task_id, payload),
            )

    @with_connection
    def imported_bundle(self, task_id: str) -> EvidenceBundle | None:
        row = (
            self._conn()
            .execute("SELECT bundle_json FROM research_imported_evidence WHERE task_id=?", (task_id,))
            .fetchone()
        )
        return EvidenceBundle.model_validate_json(row[0]) if row else None

    @with_connection
    def put_contract(self, contract: ResearchContract) -> None:
        with self.atomic():
            existing = self.get_contract(contract.task_id, contract.revision)
            if existing is not None:
                if existing != contract:
                    raise ReceiptConflictError("Contract revision is immutable")
                return
            previous = self.get_contract(contract.task_id, contract.revision - 1) if contract.revision > 1 else None
            if contract.revision > 1 and previous is None:
                raise ReceiptConflictError("Contract revisions must be consecutive")
            if previous is not None:
                new_rubric = {item.rubric_id: item for item in contract.rubric}
                if any(item.hard and new_rubric.get(item.rubric_id) != item for item in previous.rubric):
                    raise ReceiptConflictError("Contract revision cannot remove or weaken hard rubric items")
                if any(
                    key not in contract.resource_ceilings or contract.resource_ceilings[key] > ceiling
                    for key, ceiling in previous.resource_ceilings.items()
                ):
                    raise ReceiptConflictError("Contract revision cannot increase resource ceilings")
            self._conn().execute(
                "INSERT INTO research_contracts VALUES (?, ?, ?, ?)",
                (contract.task_id, contract.revision, contract.content_hash(), contract.model_dump_json()),
            )

    @with_connection
    def get_contract(self, task_id: str, revision: int) -> ResearchContract | None:
        row = (
            self._conn()
            .execute("SELECT contract_json FROM research_contracts WHERE task_id=? AND revision=?", (task_id, revision))
            .fetchone()
        )
        return ResearchContract.model_validate_json(row[0]) if row else None

    @with_connection
    def put_source(
        self, artifact: SourceArtifact, representation_text: str, segments: tuple[EvidenceSegment, ...]
    ) -> SourceArtifact:
        if len(representation_text) > 2_000_000 or len(segments) > 1000:
            raise ReceiptConflictError("Source representation exceeds evidence storage limits")
        if artifact.representation_hash != (text_hash(representation_text) if representation_text else None):
            raise ReceiptConflictError("Source representation hash does not match stored text")
        if artifact.fetch_status != "available" and representation_text:
            raise ReceiptConflictError("Unavailable source cannot supply an available representation")
        if artifact.fetch_status == "available" and not representation_text:
            raise ReceiptConflictError("Available source requires representation text")
        for segment in segments:
            if (segment.task_id, segment.source_id, segment.source_version, segment.representation) != (
                artifact.task_id,
                artifact.source_id,
                artifact.source_version,
                artifact.representation,
            ):
                raise ReceiptConflictError("Segment lineage differs from its source")
            if segment.coordinate_system != "representation_characters":
                raise ReceiptConflictError("Raw-byte resolution is unavailable for stored text representations")
            if segment.start < 0 or segment.end <= segment.start or segment.text_hash != text_hash(segment.text):
                raise ReceiptConflictError("Segment coordinates or text hash are invalid")
            if representation_text[segment.start : segment.end] != segment.text or segment.end > len(
                representation_text
            ):
                raise ReceiptConflictError("Segment does not resolve to exact source text")
            if segment.quality != artifact.quality:
                raise ReceiptConflictError("Segment cannot silently improve source parser quality")
        with self.atomic():
            existing = self.get_source(artifact.task_id, artifact.source_id, artifact.source_version)
            if existing is not None:
                stored, text = existing
                if text != representation_text or stored.model_dump(exclude={"acquired_at"}) != artifact.model_dump(
                    exclude={"acquired_at"}
                ):
                    raise ReceiptConflictError("Source version is immutable")
                artifact = stored
            else:
                self._conn().execute(
                    "INSERT INTO research_source_versions VALUES (?, ?, ?, ?, ?)",
                    (
                        artifact.task_id,
                        artifact.source_id,
                        artifact.source_version,
                        artifact.model_dump_json(),
                        representation_text,
                    ),
                )
            for segment in segments:
                old = self.get_segment(segment.task_id, segment.segment_id)
                if old is not None:
                    if old != segment:
                        raise ReceiptConflictError("Evidence segment identity is immutable")
                else:
                    self._conn().execute(
                        "INSERT INTO research_evidence_segments VALUES (?, ?, ?, ?, ?)",
                        (
                            segment.task_id,
                            segment.segment_id,
                            segment.source_id,
                            segment.source_version,
                            segment.model_dump_json(),
                        ),
                    )
        return artifact

    @with_connection
    def get_source(self, task_id: str, source_id: str, source_version: str) -> tuple[SourceArtifact, str] | None:
        row = (
            self._conn()
            .execute(
                "SELECT artifact_json, representation_text FROM research_source_versions WHERE task_id=? AND source_id=? AND source_version=?",
                (task_id, source_id, source_version),
            )
            .fetchone()
        )
        return (SourceArtifact.model_validate_json(row[0]), str(row[1])) if row else None

    @with_connection
    def get_segment(self, task_id: str, segment_id: str) -> EvidenceSegment | None:
        row = (
            self._conn()
            .execute(
                "SELECT segment_json FROM research_evidence_segments WHERE task_id=? AND segment_id=?",
                (task_id, segment_id),
            )
            .fetchone()
        )
        return EvidenceSegment.model_validate_json(row[0]) if row else None

    @with_connection
    def resolve(self, task_id: str, segment_id: str) -> tuple[SourceArtifact, EvidenceSegment]:
        segment = self.get_segment(task_id, segment_id)
        source = self.get_source(task_id, segment.source_id, segment.source_version) if segment else None
        if segment is None or source is None or source[1][segment.start : segment.end] != segment.text:
            raise ReceiptConflictError("Evidence locator does not resolve within this task")
        return source[0], segment

    @with_connection
    def put_claim(self, claim: ClaimEvidence) -> None:
        with self.atomic():
            contract = self.get_contract(claim.task_id, claim.contract_revision)
            if contract is None or not set(claim.rubric_ids) <= {item.rubric_id for item in contract.rubric}:
                raise ReceiptConflictError("Claim references an unknown contract or rubric item")
            lineage = {(ref.source_id, ref.source_version) for ref in claim.source_lineage}
            for source_id, version in lineage:
                if self.get_source(claim.task_id, source_id, version) is None:
                    raise ReceiptConflictError("Claim references an unknown source version")
            references = claim.supporting_segment_ids + claim.contrary_segment_ids
            for segment_id in references:
                artifact, _ = self.resolve(claim.task_id, segment_id)
                if (artifact.source_id, artifact.source_version) not in lineage:
                    raise ReceiptConflictError("Claim segment is missing its source lineage")
            if bool(references) != (claim.citation_status == "resolvable"):
                raise ReceiptConflictError("Claim citation status must report actual segment resolution")
            row = (
                self._conn()
                .execute(
                    "SELECT claim_json FROM research_claim_evidence WHERE task_id=? AND claim_id=?",
                    (claim.task_id, claim.claim_id),
                )
                .fetchone()
            )
            if row is not None:
                if ClaimEvidence.model_validate_json(row[0]) != claim:
                    raise ReceiptConflictError("Claim identity is immutable; review requires a new claim revision")
                return
            self._conn().execute(
                "INSERT INTO research_claim_evidence VALUES (?, ?, ?, ?)",
                (claim.task_id, claim.claim_id, claim.contract_revision, claim.model_dump_json()),
            )

    @with_connection
    def put_decision(self, receipt: DecisionReceipt) -> None:
        with self.atomic():
            action = (
                self._conn()
                .execute(
                    "SELECT request_json, status FROM research_action_receipts WHERE task_id=? AND action_id=?",
                    (receipt.task_id, receipt.action_id),
                )
                .fetchone()
            )
            if not action or action[1] != "running":
                raise ReceiptConflictError("Decision requires the current running task action")
            request = json.loads(action[0])
            task = (
                self._conn()
                .execute("SELECT orchestrator_state FROM research_tasks WHERE id=?", (receipt.task_id,))
                .fetchone()
            )
            active = json.loads(task[0] or "{}").get("active_action_id") if task else None
            deadline = datetime.fromisoformat(request["deadline"]) if request.get("deadline") else None
            if active != receipt.action_id or (deadline is not None and datetime.now(UTC) >= deadline):
                raise ReceiptConflictError("Late evidence decision cannot enter the current task")
            if (receipt.contract_hash, receipt.policy_hash) != (request["contract_hash"], request["policy_hash"]):
                raise ReceiptConflictError("Decision changed its action contract or policy")
            row = (
                self._conn()
                .execute(
                    "SELECT decision_json FROM research_evidence_decisions WHERE task_id=? AND decision_id=?",
                    (receipt.task_id, receipt.decision_id),
                )
                .fetchone()
            )
            if row is not None:
                if DecisionReceipt.model_validate_json(row[0]) != receipt:
                    raise ReceiptConflictError("Decision identity is immutable")
                return
            self._conn().execute(
                "INSERT INTO research_evidence_decisions VALUES (?, ?, ?, ?)",
                (receipt.task_id, receipt.decision_id, receipt.action_id, receipt.model_dump_json()),
            )

    @with_connection
    def export_bundle(self, task_id: str) -> dict[str, Any]:
        """Bounded pages; complete immutable records with self-contained locators."""
        queries = {
            "contracts": "SELECT rowid,contract_json FROM research_contracts WHERE task_id=? AND rowid>? ORDER BY rowid LIMIT 50",
            "sources": "SELECT rowid,artifact_json,representation_text FROM research_source_versions WHERE task_id=? AND rowid>? ORDER BY rowid LIMIT 50",
            "segments": "SELECT rowid,segment_json FROM research_evidence_segments WHERE task_id=? AND rowid>? ORDER BY rowid LIMIT 50",
            "claims": "SELECT rowid,claim_json FROM research_claim_evidence WHERE task_id=? AND rowid>? ORDER BY rowid LIMIT 50",
            "decisions": "SELECT rowid,decision_json FROM research_evidence_decisions WHERE task_id=? AND rowid>? ORDER BY rowid LIMIT 50",
        }
        bundle: dict[str, Any] = {"schema_version": 1, "task_id": task_id}
        total_characters = 0
        for name, query in queries.items():
            records: list[dict[str, Any]] = []
            after = 0
            while True:
                rows = self._conn().execute(query, (task_id, after)).fetchall()
                if not rows:
                    break
                for row in rows:
                    total_characters += len(row[1]) + (len(row[2]) if name == "sources" else 0)
                    if total_characters > 20_000_000 or len(records) >= 5000:
                        raise ReceiptConflictError("Evidence export exceeds its bounded payload contract")
                    record = json.loads(row[1])
                    records.append({"artifact": record, "representation_text": row[2]} if name == "sources" else record)
                after = rows[-1][0]
            bundle[name] = records
        return bundle
