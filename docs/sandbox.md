# Diagnostic sandbox: explicit opt-in

Generated code never runs in the SDK host Python process. There is no shell tool, host-execution
fallback, network probe, repository patch application or recovery executor. Disabled by default.

## Threat model and limits

The reference runner uses an ephemeral Docker container with no host mounts, no forwarded
environment variables, no network, a read-only root, an unprivileged user, all capabilities
dropped and no-new-privileges. Only a 16 MiB tmpfs is writable. Approved redacted files are copied
through stdin; generated Python runs against that copy. CPU/memory/PID/duration/input/output
limits apply. Failure/cancellation removes the named container. Images never pull automatically.

**A container shares its host kernel and is not VM-grade isolation for hostile code.**
Use an approved dedicated/rootless daemon or a reviewed stronger runner. Never use a production
daemon, privileged mounts, Docker socket exposure or a daemon holding sensitive workloads.
The operator chooses/trusts the daemon context and image. Allowlisting and heuristic redaction
do not guarantee absence of secrets: review files before provider/container export.
Tests demonstrate constraints, not a security audit.

The tmpfs is noexec, but Python intentionally interprets generated source; the flag does not
mean source cannot execute. Imports are limited to the approved image. No package downloads.

## Step-by-step local qualification

1. Install Docker, select a dedicated development context and confirm docker info.
2. Inspect and explicitly pull an approved Python image. Record its RepoDigest. The current
   qualification uses:

       docker pull python@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016

   This is a tested example digest, not an indefinite endorsement. Review/update it normally.
3. Run real isolation tests from the SDK checkout:

       LUMIS_TEST_SANDBOX_IMAGE=python@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016 \
         uv run pytest tests/test_investigation_safety.py tests/test_incident_agent.py -q

   Expect identity/network/filesystem/copy checks, invalid/non-finite/oversized output refusal,
   and timeout/cancellation cleanup. Ordinary tests skip Docker unless this variable is set.
4. Approve exact files to copy, never credentials/environment/secrets.
5. Merge these fields into your complete YAML, keeping independent evidence queries:

       investigator:
         sandbox:
           enabled: true
           image: python@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016
           timeout_seconds: 10
           memory_mb: 128
           cpus: 0.5
           pids: 32
           max_output_bytes: 8000
       queries:
         - id: synthetic-reproduction
           provider: probe
           entity_id: service:demo
           key: reproduced
           description: Synthetic reproduction against approved copied source

   Ensure budget.query_timeout_seconds / total deadline allow the probe to finish.
6. Register a hypothesis requesting that query with predictions/falsifiers for its key.
   The probe tool accepts hypothesis/query IDs, purpose, generated code and optional repository
   ID. Code must print exactly one JSON object with a finite scalar, for example {"value": true}.
7. Review receipts: purpose/status/redacted output/code digest and copied-source digest when
   applicable. Generated source is not retained unless included in a tentative suggestion.
   Store approved experiment source separately when exact replay is needed.

## Evidence interpretation

Probe evidence is quality: degraded. A model-authored experiment could simply print the expected
answer; it cannot establish a production fact, causality or supported diagnosis. It remains
available for human review; mechanical support requires independent observed telemetry.
Its timestamp is the incident-end **replay coordinate**, not a historical production observation.

No sandbox benchmark is production-fix verification. Application/verification happen outside
the SDK; record human outcomes separately. No automatic recovery or learning.

## Failure behavior

Missing daemon/image, disabled/unregistered/reused probe, invalid scope, exceeded budget,
timeout/cancellation, nonzero exit, oversized output or invalid JSON yield no trusted measurement.
Receipts are sanitized. Cleanup retries briefly to cover daemon creation/cancellation races;
a daemon outage or creation delayed beyond that bounded window can prevent removal,
so inspect your dedicated daemon after failures. Never enable a host fallback.

Flags follow the [Docker container run reference](https://docs.docker.com/engine/containers/run/).
