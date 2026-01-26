# Configuration Validation

This guide covers how to validate api-probe configuration files and interpret the results.

- All output prints to stderr (CI-friendly; no mixing with probe output)
- Exit codes: 0 = valid, 1 = invalid, 2 = error (file not found/exception)
- For command syntax and examples, see VALIDATE_COMMAND.md

## Usage

```bash
./run.sh validate <config-file>
```

Docker:

```bash
docker run --rm \
  -v $(pwd)/configs:/configs \
  api-probe:latest validate /configs/tests.yaml
```

## What It Checks

- Structure: required fields, types, probe kinds (rest/graphql)
- Probe rules: GraphQL requires `query`; REST with `body` requires `Content-Type`
- Delay: must be a non-negative number (negative delays produce warnings)
- Variables: lists all `${VAR}` references and whether they are defined in the environment
- Parse: verifies the config can be parsed into internal models and counts probes/executions

## Output Breakdown

- Validation errors (if any)
- Warnings (non-fatal)
- Environment variables referenced:
  - Shows only variable NAMES (no values printed)
  - Split into Defined and Not defined
- Parse results (probe count and execution contexts)

Example (stderr):

```
Validating: examples/passing/simple.yaml
============================================================

📋 ENVIRONMENT VARIABLES REFERENCED:

  ✓ Defined:
    • BASE_URL

  ✗ Not defined:
    • API_KEY

Parsing configuration...
✓ Successfully parsed 3 probe(s)

============================================================
✅ Configuration is valid!
```

With errors:

```
Validating: examples/broken.yaml
============================================================

❌ VALIDATION ERRORS:
  • Probe 1: missing required 'endpoint' field
  • Probe 2: REST probe with body must have Content-Type header

⚠️  WARNINGS:
  • Probe 3: negative delay will be ignored

📋 ENVIRONMENT VARIABLES REFERENCED:

  ✓ Defined:
    • BASE_URL

  ✗ Not defined:
    • API_KEY
    • CLIENT_ID

Parsing configuration...
✗ Parse error: Probe 'Test API' must have 'endpoint' field

============================================================
❌ Configuration has errors
```

## CI/CD Tips

- Capture stderr for logs and diagnostics
- Gate deployments on exit code (0 proceeds, 1/2 blocks)
- Generate an env-var checklist:

```bash
./run.sh validate config.yaml 2>&1 | \
  grep -A 100 "Not defined" | \
  grep "•" | sed 's/.*• //'
```

## See Also

- SCHEMA_SPECIFICATION.md — complete YAML reference
- GETTING_STARTED.md — basic usage and examples
- VALIDATE_COMMAND.md — command-focused reference
