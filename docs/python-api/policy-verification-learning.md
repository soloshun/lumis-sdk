# Policy, verification, and learning API

## Proposal-only governance

Build `PlaybookDocument` and `PolicyDocument` values from `lumis_sdk.domain`, then compose them with
`lumis_sdk.application.ProposalService`.

```python
from datetime import UTC, datetime, timedelta

from lumis_sdk.application import ProposalService
from lumis_sdk.domain import (
    DocumentMetadata,
    EvidenceReference,
    ParameterDefinition,
    ParameterType,
    PlaybookAction,
    PlaybookDocument,
    PolicyDocument,
    PolicyRule,
    RiskLevel,
)

playbook = PlaybookDocument(
    metadata=DocumentMetadata(name="worker-recovery", version="1"),
    actions=[
        PlaybookAction(
            name="restart",
            summary="Recommend a bounded worker restart.",
            risk=RiskLevel.HIGH,
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
)
policy = PolicyDocument(
    metadata=DocumentMetadata(name="production-policy", version="4"),
    rules=[
        PolicyRule(
            playbook_name="worker-recovery",
            action_name="restart",
            approval_required=True,
        )
    ],
)

now = datetime.now(UTC)
proposal = ProposalService(playbook, policy).propose(
    proposal_id="proposal-123",
    diagnosis_id="diagnosis-123",
    diagnosis_digest="a" * 64,
    evidence=[EvidenceReference(id="log-1", source="collector", digest="b" * 64)],
    action_name="restart",
    parameters={"replicas": 2},
    created_at=now,
    expires_at=now + timedelta(minutes=15),
)
assert proposal.execution_allowed is False
```

`ApprovalLedger` is a small reference implementation of decision idempotency. Production
applications should persist `ApprovalDecisionRecord` values in their own auditable store.

Checked schemas:

- `schemas/lumis-playbook-v1.schema.json`
- `schemas/lumis-policy-v1.schema.json`
- `schemas/lumis-action-proposal-v1alpha1.schema.json`

## Verification-aware learning

Use `VerificationRequest`, `VerificationRecord`, and `VerificationCheck` for exchange and
persistence. `learn_from_verification` applies conservative promotion rules to a `MemoryStore`.

A passed result requires an explicit `ConfirmedResolution` with:

- `verified=True`;
- `truth_state=TruthState.VERIFICATION_CONFIRMED`;
- the matching `verification_id`.

Failed results become rejected memory. Unknown and timed-out results remain unconfirmed and require
escalation. They never report recovery and never become reusable.

`MemoryQuery(reusable_only=True)` returns only human- or verification-confirmed records.
`MemoryMatch.score_components` exposes `lexical`, `filters`, and `truth` components, while
`reasons` includes the truth state and matched terms.

## Replay evaluation

`lumis_sdk.evaluation.evaluate_replay` accepts `ReplayCase` values and returns exact deterministic
counts. Keep corpora synthetic or public, version them with the application, and report the
methodology with the results.
