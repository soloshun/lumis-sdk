# Core concepts

## Deterministic first

Rules and explicit application code handle known incidents before any model is considered. The
same bounded input, rules, and evidence produce the same rule selection and explanation. Models
are optional adapters, not a runtime requirement or an authority source.

## Evidence, facts, and hypotheses

Evidence identifies supplied observations and their provenance. Confirmed facts remain distinct
from hypotheses. Confidence communicates uncertainty; it never approves an action. Missing
evidence is part of a diagnosis so downstream users can investigate instead of treating a guess as
truth.

## Diagnosis-as-Code

Projects own versioned `DiagnosisRule` or `DiagnosisRuleSet` documents. Rules use stable IDs,
versions, priorities, bounded conditions, evidence requirements, and deterministic tie-breaking.
They can be reviewed, tested with fixtures, and changed independently of SDK source.

## Ports and adapters

Core domain and application services know protocols such as evidence providers, memory stores,
model gateways, policy, approval, and verification. Local reference adapters and optional packages
implement those ports. A provider or platform can be replaced without changing incident truth
semantics.

## Explicit authority

Installing or discovering a plugin grants nothing. Network, filesystem, secret, model, and
execution authorities are declared and allowed separately. Lumis SDK core has no production
executor. A proposal and even an approval remain non-executing records.

## Verification before learning

Human-confirmed or verification-confirmed outcomes may become reusable memory. Failed, unknown,
timed-out, rejected, or superseded outcomes cannot silently become truth. Retrieval exposes score
components and truth filters rather than hiding ranking behind a provider.

## Framework versus product

Lumis SDK is the Apache-2.0 framework. Loomis/Lumis platform is one consumer. Tenancy, billing,
hosted credentials, product UI, and deployment policy do not belong in SDK core unless generalized
through an open, vendor-neutral contract.
