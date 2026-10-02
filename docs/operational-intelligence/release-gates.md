# Operational reset: path to 0.1.0

Target is **0.1.0**, not 1.0.0. The July Phase 1 guide is retained for historical procedural
reference; its feature-completion assumptions do not qualify the new architecture.
The current package identifier remains `0.1.0rc1` until a new RC is deliberately prepared.

## Gate ledger

| Gate | Evidence required | Reset status |
| --- | --- | --- |
| Preserved history | Remote legacy branch and original release tags | Legacy branch created at `8a371d1`; tags unchanged |
| Schema/control substrate | Old and new tests, strict mypy, generated schema checks | 129 tests on Python 3.11–3.13; PR #93 merged after all ten checks |
| New external connectors | Bounded reads, HTTP mocks, Kubernetes/OTLP format tests | Contract tests; live deployment not implied |
| Live GridCast slice | Scoped graph, 3–5 actual model candidates, observations and abstention run | Pending separate running estate/model run |
| Comparative evaluation | Independent 8–15 incidents, hidden labels, budget-matched baselines | Planned OI-2; no performance claims yet |
| Policy/verification invariants | High-risk gate independent of confidence, no false resolution | Retained old tests; new recovery bridge remains planned |
| Compatibility | Legacy consumers/paper experiment, plugin co-install, migration notes | Old regression tests; independent live consumer checks pending |
| Independent review/adoption | Reviewed connector authority, external controlled walkthrough | Open; implementation tests cannot replace these |
| Distribution | Wheel/sdist installs, licenses, SAST, provenance, immutable tag/version | Qualify at RC preparation |

## Exact progression

1. Merge the reviewed refactor PR into `dev` only after CI. Record commit/check links.
2. Follow the [GridCast integration runbook](gridcast-integration.md); retain real run artifacts.
3. Complete OI-2/3 diagnosis experiments and publish only measured findings. Do not relabel the
   bundled contract replay as a research benchmark.
4. Qualify the desired 0.1.0 scope through the active roadmap; preserve action-authority boundary
   unless an executor RFC and independent verification tests have landed.
5. Close review/adoption/compatibility gates with named evidence. Historical #9/#57 may remain
   open where their evidence requirements still apply; superseded sprint numbering is not done.
6. Prepare the next immutable RC (for example `0.1.0rc2`, after confirming it is unused). Update
   pyproject/version string, lock, release notes and artifact version pins in one PR. Run the
   existing distribution/clean-install/provenance workflows.
7. Promote reviewed `dev` to `main` through a separate PR. Tag/publish only the qualified revision
   and verify public core/plugin installation from PyPI in a clean environment.
8. After candidate feedback and all required gates, prepare/publish `0.1.0`. Leave this ledger
   and the older release guide in the repository for future reference.

SEAMS reproducibility is separate from final release qualification. Pin the specific reviewed
Git revision in artifact runs. Keep ground truth outside runtime input and retain a deterministic
run digest. Update paper results only after re-running its harness; SDK implementation alone does
not change empirical claims or imply paper acceptance.
