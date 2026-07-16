# Independently packaged fixture plugin

This synthetic package demonstrates the v0.3 plugin boundary without a vendor service, network
request, credential, model, or execution capability.

It contains:

- a `lumis_sdk.plugins` entry point;
- a static `lumis-plugin.json` manifest included at wheel root;
- a zero-argument callable factory with the same runtime manifest;
- one contract test using the public Lumis SDK testkit.

Build the SDK and plugin, install both into a clean environment, and inspect metadata:

```bash
uv build --no-sources
uv build --project cookbook/plugin-package

uv venv /tmp/lumis-plugin-demo --python 3.11
uv pip install --python /tmp/lumis-plugin-demo/bin/python \
  dist/lumis_sdk-*.whl \
  cookbook/plugin-package/dist/lumis_sdk_fixture_plugin-*.whl

/tmp/lumis-plugin-demo/bin/lumis plugins list
/tmp/lumis-plugin-demo/bin/lumis plugins doctor
```

Listing and doctor do not import `lumis_fixture_plugin`. Application code must explicitly call
`ImportlibPluginCatalog.load("fixture-evidence")` before the factory runs.
