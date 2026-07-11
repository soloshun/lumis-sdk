# Releasing OpenARIA

OpenARIA uses a manually dispatched GitHub Actions workflow and PyPI Trusted Publishing. No PyPI API token is stored in GitHub.

## One-time account setup

1. Create or sign in to your PyPI account and enable two-factor authentication.
2. In the PyPI account sidebar, open **Publishing** and add a pending GitHub trusted publisher:

   | Field | Value |
   | --- | --- |
   | PyPI Project Name | `openaria` |
   | Owner | `soloshun` |
   | Repository name | `openaria` |
   | Workflow name | `release.yml` |
   | Environment name | `pypi` |

3. In GitHub, create a repository environment named `pypi`. Add yourself as a required reviewer before publishing to PyPI.
4. Repeat the pending-publisher setup on TestPyPI with environment `testpypi`, then create a matching GitHub environment named `testpypi`.

A pending publisher does not reserve a package name; it becomes a normal publisher when the first matching release succeeds. Use the exact package name in `pyproject.toml` and PyPI.

## Release procedure

1. Update the version in `pyproject.toml`, `src/openaria/__init__.py`, and `CHANGELOG.md` together.
2. Run the local release checks:

   ```bash
   uv lock
   uv run ruff format --check .
   uv run ruff check .
   uv run mypy src
   uv run python scripts/generate_config_schema.py --check
   uv run pytest
   uv build --no-sources
   ```

3. Commit and push the version change to `main`.
4. In GitHub Actions, run **Release package** manually. Enter the exact declared version and choose `testpypi`.
5. Test the result from a clean environment:

   ```bash
   uv venv /tmp/openaria-test
   /tmp/openaria-test/bin/python -m pip install \
     --index-url https://test.pypi.org/simple/ \
     --extra-index-url https://pypi.org/simple/ \
     openaria==0.0.1
   /tmp/openaria-test/bin/openaria --version
   ```

6. Run **Release package** again with the same version and select `pypi`. The `pypi` environment provides the manual approval boundary.

PyPI release files are immutable. If a release has a packaging defect, publish a new version rather than attempting to overwrite `0.0.1`.

## Installing from another project

After publishing to PyPI:

```bash
uv add "openaria>=0.0.1,<0.1.0"
```

For a one-off environment installation:

```bash
pip install openaria
```
