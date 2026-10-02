"""Contract and invariant tests for proposal-only recovery governance."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from lumis_sdk.application import (
    ApprovalLedger,
    DecisionConflictError,
    ProposalPolicyError,
    ProposalService,
)
from lumis_sdk.domain import (
    ActionProposal,
    ApprovalDecisionRecord,
    DecisionStatus,
    DocumentMetadata,
    EvidenceReference,
    ParameterDefinition,
    ParameterType,
    PlaybookAction,
    PlaybookDocument,
    PolicyDocument,
    PolicyRule,
    ProposalState,
    RiskLevel,
    canonical_digest,
)

NOW = datetime(2026, 7, 16, tzinfo=UTC)
DIGEST = "a" * 64


def _service(
    risk: RiskLevel,
    *,
    approval_required: bool,
    auto_approve_up_to: RiskLevel | None,
) -> ProposalService:
    return ProposalService(
        PlaybookDocument(
            metadata=DocumentMetadata(name="restart-worker", version="1.2.0"),
            actions=[
                PlaybookAction(
                    name="restart",
                    summary="Recommend restarting a bounded worker pool.",
                    risk=risk,
                    parameters=[
                        ParameterDefinition(
                            name="replicas",
                            type=ParameterType.INTEGER,
                            minimum=1,
                            maximum=5,
                        )
                    ],
                )
            ],
        ),
        PolicyDocument(
            metadata=DocumentMetadata(name="default-recovery", version="3"),
            rules=[
                PolicyRule(
                    playbook_name="restart-worker",
                    action_name="restart",
                    approval_required=approval_required,
                    auto_approve_up_to=auto_approve_up_to,
                )
            ],
        ),
    )


def _propose(service: ProposalService) -> ActionProposal:
    return service.propose(
        proposal_id="proposal-1",
        diagnosis_id="diagnosis-1",
        diagnosis_digest=DIGEST,
        evidence=[EvidenceReference(id="log-1", source="fixture", digest=DIGEST)],
        action_name="restart",
        parameters={"replicas": 2},
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=30),
    )


@pytest.mark.parametrize("risk", list(RiskLevel))
def test_proposals_never_grant_execution_authority(risk: RiskLevel) -> None:
    proposal = _propose(
        _service(
            risk,
            approval_required=risk is RiskLevel.HIGH,
            auto_approve_up_to=None if risk is RiskLevel.HIGH else risk,
        )
    )
    assert proposal.execution_allowed is False


def test_high_risk_cannot_be_configured_for_auto_approval() -> None:
    with pytest.raises(ValidationError, match="never be auto-approved"):
        PolicyRule(
            playbook_name="restart-worker",
            action_name="restart",
            approval_required=False,
            auto_approve_up_to=RiskLevel.HIGH,
        )


def test_maximum_diagnosis_confidence_cannot_weaken_high_risk_gate() -> None:
    """Analysis confidence is not an input to the independent risk approval decision."""
    from lumis_sdk.domain import DiagnosisResult, Severity, TriageResult

    diagnosis = DiagnosisResult(
        triage=TriageResult(classification="model", severity=Severity.HIGH, summary="Candidate"),
        root_cause_hypothesis="Model claims certainty",
        confidence=1.0,
    )
    service = _service(RiskLevel.HIGH, approval_required=True, auto_approve_up_to=None)
    proposal = service.propose(
        proposal_id="high-confidence",
        diagnosis_id="diagnosis-1",
        diagnosis_digest=canonical_digest(diagnosis),
        evidence=[EvidenceReference(id="log-1", source="fixture", digest=DIGEST)],
        action_name="restart",
        parameters={"replicas": 2},
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=30),
    )
    assert diagnosis.confidence == 1.0
    assert proposal.state is ProposalState.PENDING
    assert proposal.approval_required
    assert not proposal.execution_allowed


def test_unknown_action_and_unbounded_parameter_fail_closed() -> None:
    service = _service(
        RiskLevel.MEDIUM,
        approval_required=True,
        auto_approve_up_to=None,
    )
    with pytest.raises(ProposalPolicyError, match="unknown playbook action"):
        service.propose(
            proposal_id="bad",
            diagnosis_id="diagnosis-1",
            diagnosis_digest=DIGEST,
            evidence=[EvidenceReference(id="log-1", source="fixture", digest=DIGEST)],
            action_name="delete-everything",
            parameters={},
            created_at=NOW,
            expires_at=NOW + timedelta(minutes=1),
        )
    with pytest.raises(ProposalPolicyError, match="exceeds its maximum"):
        service.propose(
            proposal_id="bad-parameter",
            diagnosis_id="diagnosis-1",
            diagnosis_digest=DIGEST,
            evidence=[EvidenceReference(id="log-1", source="fixture", digest=DIGEST)],
            action_name="restart",
            parameters={"replicas": 50},
            created_at=NOW,
            expires_at=NOW + timedelta(minutes=1),
        )


def test_decisions_are_attributable_idempotent_and_revision_pinned() -> None:
    proposal = _propose(_service(RiskLevel.HIGH, approval_required=True, auto_approve_up_to=None))
    decision = ApprovalDecisionRecord(
        decision_id="decision-1",
        proposal_id=proposal.proposal_id,
        proposal_revision=proposal.revision,
        status=DecisionStatus.APPROVED,
        actor="on-call@example.com",
        reason="Reviewed evidence and bounded impact.",
        decided_at=NOW + timedelta(minutes=5),
    )
    ledger = ApprovalLedger()
    approved = ledger.apply(proposal, decision, now=decision.decided_at)
    assert approved.state is ProposalState.APPROVED
    assert ledger.apply(proposal, decision, now=decision.decided_at) == approved
    with pytest.raises(DecisionConflictError, match="different decision"):
        ledger.apply(
            proposal,
            decision.model_copy(update={"reason": "Different content"}),
            now=decision.decided_at,
        )


def test_canonical_digest_is_stable_across_round_trip() -> None:
    proposal = _propose(
        _service(RiskLevel.LOW, approval_required=False, auto_approve_up_to=RiskLevel.LOW)
    )
    assert canonical_digest(proposal) == canonical_digest(
        ActionProposal.model_validate_json(proposal.model_dump_json())
    )
