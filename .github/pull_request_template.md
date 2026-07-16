## Outcome

Describe the adopter-visible result.

## Related issue

Closes #

## Verification

- [ ] `uv run ruff format --check .`
- [ ] `uv run ruff check .`
- [ ] `uv run mypy src`
- [ ] `uv run python scripts/generate_config_schema.py --check`
- [ ] `uv run pytest`
- [ ] `uv build`

## Public contract and compatibility

Describe Python API, CLI, configuration, schema, persistence, or behavior changes. State the
migration path when an existing contract changes.

## Safety and privacy

Describe effects on evidence handling, secrets, network/filesystem authority, model use,
approval, execution, verification, or audit behavior. Write "No change" when none apply.

## Documentation and release notes

- [ ] Public behavior is documented.
- [ ] `CHANGELOG.md` is updated for user-visible behavior.
- [ ] Examples use synthetic or public data only.
