# Schema drift investigation runbook

## Purpose

Use this runbook when a pipeline expects a field that is missing or renamed in its input.

## Investigation steps

1. Compare the current input schema with the last successful schema.
2. Inspect the lineage context to identify upstream and downstream assets.
3. Confirm whether an upstream owner renamed, removed, or retyped the field.
4. Check whether a project normalization step should map the replacement field.
5. Record the confirmed resolution after a human reviews the evidence.

## Safety boundary

Do not alter production mappings, schemas, or data directly from this runbook. Prepare a reviewable change after approval.
