# schema_mismatch_in_dataframe

## Purpose

Recommend an investigation path when a dataframe transformation expects a field that is absent from the current schema.

## Risk

Medium. A mapping or schema-related change can affect downstream datasets and dashboards.

## Approval

Human approval is required before any mapping, code, or schema change.

## Recommendation-only steps

1. Verify the replacement field against the source-owner contract.
2. Prepare a reviewable mapping change or pull request.
3. Re-run the validation in a safe environment after approval.
4. Confirm downstream freshness and record the outcome.

## Execution boundary

This cookbook does not execute these steps. It may only propose this playbook and request approval.
