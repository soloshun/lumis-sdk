# OpenARIA cookbooks

Cookbooks are small, runnable teaching projects that use OpenARIA core in a specific domain. They are not part of the core package's runtime dependency set. Each cookbook owns its synthetic data, domain rules, knowledge documents, optional integrations, and setup instructions.

## Current cookbook domains

| Cookbook | Domain and lesson | Optional agent stack |
| --- | --- | --- |
| [simple-log-diagnosis](simple-log-diagnosis/README.md) | The smallest configuration-driven local diagnosis. | None |
| [recording-resolution](recording-resolution/README.md) | Save a human-confirmed outcome to local incident memory. | None |
| [data-pipeline-investigation](data-pipeline-investigation/README.md) | Schema drift, unfamiliar transformation failure, and telemetry redaction in a data pipeline. | Agno + OpenRouter |
| [ml-regression-monitoring](ml-regression-monitoring/README.md) | Feature drift, feature contracts, and candidate-model quality in one regression pipeline. | Agno + OpenRouter |
| [software-delivery-ci-investigation](software-delivery-ci-investigation/README.md) | CI lockfiles, workflow permissions, and Terraform references in one delivery pipeline. | Agno Toolkit + OpenRouter |

## Shared structure

Agentic cookbooks keep their framework-facing declaration in an `openaria/` directory:

```text
cookbook-name/
├── openaria/
│   ├── openaria.yml       # project, local state, report, and input paths
│   └── rules.yml          # project-owned deterministic rules
├── knowledge/             # optional runbooks and playbooks
├── synthetic_project/     # synthetic code and data only
└── README.md              # domain-specific teaching guide
```

This organization keeps configuration easy to find without mixing it with source, data, or provider-specific code. Relative paths in `openaria/openaria.yml` are resolved from that directory; the supplied cookbooks point local reports and SQLite memory back to their cookbook root.

## Adding a cookbook

Start with one bounded incident class and synthetic inputs. Explain the domain, the signals being tested, deterministic and unknown paths, safety boundary, and exact commands in the cookbook README. Keep optional providers and frameworks inside the cookbook. Add core functionality only when it is vendor-agnostic and useful to more than one cookbook.

The three initial domains now cover data pipelines, ML regression monitoring, and software delivery. They are synthetic proof-of-concept cookbooks, not production integrations.
