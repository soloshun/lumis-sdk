# Lumis SDK HTTP JSON evidence

This optional package implements the public asynchronous `EvidenceProvider` contract against one
allowlisted HTTPS JSON endpoint. Core does not install an HTTP client.

Install the independently versioned plugin alongside the released core:

```bash
pip install "lumis-sdk==0.0.8" "lumis-sdk-http-json-evidence==0.1.1"
```

The connector:

- requires exact destination-origin allowlisting and HTTPS;
- never follows redirects;
- loads an optional token from a named environment variable;
- sends minimized incident metadata, not raw incident payloads;
- applies connection/request timeouts, bounded retries, and a response-byte limit;
- returns structured failures instead of converting transport errors into evidence;
- relies on core `EvidenceService` for item/kind/character bounds and conservative redaction.

Discovery grants neither its declared network nor secret authority. Applications must explicitly
load and compose the plugin.
