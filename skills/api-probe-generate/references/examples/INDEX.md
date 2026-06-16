# Example pattern library

Canonical, runnable api-probe files showing the **shape** of each feature. Consult the closest match before emitting YAML.

**These are structural references only.** Never copy their endpoints, hostnames, request bodies, or expected values into generated probes (e.g. `httpbin.org`, `countries.trevorblades.com`, the sample IDs). Every real value must come from the user's actual API — the examples only show *how the YAML is shaped*.

| File | Demonstrates |
|------|--------------|
| `passing/simple.yaml` | Basic REST: `status`, `body.present`, `body.equals`, a POST with inline body |
| `passing/graphql.yaml` | GraphQL query + variables, `output` capture, `absent: [errors]` |
| `passing/groups-parallel.yaml` | Flat group (parallel, shared scope) and staged group (isolated parallel workflows) |
| `passing/executions-block.yaml` | Multiple executions, each with its own variables/base URL |
| `passing/include-directive.yaml` | `!include` for request bodies (paths relative to the probe file) |
| `passing/complex-validation.yaml` | Rich validators: `type`, `matches`, `range`, `length`, `contains` |
| `passing/xml-soap.yaml` | SOAP/XML probe with an inline XML body |
| `includes/login-body.json` | Payload referenced by `include-directive.yaml` |
| `includes/user-profile.json` | Payload referenced by `include-directive.yaml` |

The bundled `!include` paths (`../includes/...`) resolve within this folder, so the examples can be run as-is for reference.

---

Provenance: copied from the api-probe repository's top-level `examples/` directory. If those examples change upstream, refresh this folder to match. When the skill runs inside a project that has its own `examples/` of api-probe probes, prefer those as the more current source.
