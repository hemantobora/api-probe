# API-Probe YAML Schema Specification

**Version:** 2.3.0  

## Overview

This document provides the complete YAML schema specification for api-probe configuration files. The schema defines how to declare API probes, validations, execution contexts, and parallel execution flows for post-deployment functional testing.

---

## Table of Contents

- [Root Structure](#root-structure)
- [Executions Block](#executions-block)
- [Per-Execution Validation Overrides](#per-execution-validation-overrides)
- [Probe Definition](#probe-definition)
- [Group Definition](#group-definition)
- [REST API Probes](#rest-api-probes)
- [GraphQL API Probes](#graphql-api-probes)
- [XML/SOAP API Probes](#xmlsoap-api-probes)
- [Validation Specification](#validation-specification)
- [Output Variables](#output-variables)
- [Include Directive](#include-directive)
- [Variable Substitution](#variable-substitution)
- [Type Coercion Tags](#type-coercion-tags)
- [Progress Reporting](#progress-reporting)
- [Expression Evaluation](#expression-evaluation)
- [Validation Conditional Ignore](#validation-conditional-ignore)
- [Complete Examples](#complete-examples)

---

## Root Structure

The root of every api-probe configuration file contains two top-level keys:

```yaml
executions:               # OPTIONAL: Array of execution contexts
  - name: string
    vars: []

probes:                   # REQUIRED: Array of Probe or Group objects
  - <probe-or-group>
```

### Rules

- If `executions` is present and non-empty, each execution runs all probes with its own variables
- If `executions` is absent or empty, probes run once with environment variables
- `probes` array is required and must contain at least one probe or group
- Probes execute in YAML sequence order (top to bottom)
- Groups execute their probes in parallel
- Empty `probes` array is valid (no-op)

---

## Executions Block

Define multiple execution contexts to run the same probes with different variables.

### Schema

```yaml
executions:
  - name: string                    # OPTIONAL: Execution name (auto-generated if not provided)
    vars:                           # OPTIONAL: List of variable definitions (default: [])
      - VAR_NAME: "value"           # Hardcoded value
      - VAR_NAME: "${ENV_VAR}"      # Reference environment variable
    # vars defaults to [] if omitted
    validations:                    # OPTIONAL: Per-execution validation overrides keyed by probe name
      "Probe Name":
        <validation-spec>
```

### Field Descriptions

#### `name` (optional)
- **Type:** String
- **Description:** Human-readable name for this execution context
- **Auto-generation:** If not provided, generates like "awesome-paris", "elegant-tokyo"
- **Usage:** Shown in failure reports

#### `vars` (optional)
- **Type:** List of key-value pairs
- **Default:** Empty list
- **Description:** Variables for this execution context
- **Variable Resolution Order:**
  1. Check vars in current execution
  2. If value contains `${...}`, resolve from environment
  3. If not found in execution vars, check environment variables
  4. If still not found, error on use

### Examples

```yaml
executions:
  # Hardcoded values
  - name: "Production User A"
    vars:
      - ACCOUNT: "123456789"
      - CLIENT_ID: "client-prod-a"
      - REGION: "us-east-1"

  # Mix of hardcoded and environment variables
  - name: "Staging"
    vars:
      - ACCOUNT: "999999999"
      - API_KEY: "${STAGING_API_KEY}"    # Resolved from environment
      - REGION: "us-west-2"

  # Auto-generated name
  - vars:
      - ACCOUNT: "555555555"
      - CLIENT_ID: "client-test"
```

---

## Per-Execution Validation Overrides

Each execution context can supply a `validations` block that overrides or replaces the inline `validation:` defined on individual probes. This allows the same probe definitions to be validated differently per environment — for example, stricter assertions in production than in staging.

### Schema

```yaml
executions:
  - name: string
    vars: [...]
    validations:                        # OPTIONAL
      "Exact Probe Name":               # Key must match probe name exactly
        status: integer | string
        response_time: integer
        headers:
          <validator>: <spec>
        body:
          <validator>: <spec>
```

### How It Works

When a probe runs, its validation is resolved in this order:

1. If the execution has a `validations` block **and** the probe name is a key in it → that spec is used (or skipped if the value is `null`)
2. Otherwise → the probe's own inline `validation:` block is used
3. If neither is present → no validation is run for that probe

In other words: **probes not listed in the `validations` block fall back to their inline `validation:` as normal**. The `validations` block is a selective override, not an allowlist.

To explicitly suppress validation for a specific probe (overriding its inline `validation:`), set its value to `null`:

```yaml
validations:
  "Probe A":       ~   # null — explicitly skip validation
  "Probe B":
    status: 200
```

Variable substitution (`${VAR}`) is applied to override specs at runtime, exactly as it is for inline validation.

### Key Rules

- Keys in `validations` must match probe names **exactly** (case-sensitive)
- Probes not listed in the `validations` block are **unaffected** — they fall back to their inline `validation:` as normal
- The override is **total replacement**, not a merge — if you override a probe, specify everything you want validated
- Set a probe's value to `null` (`~`) to explicitly suppress validation for that probe (overrides its inline `validation:`)
- Works with `!include` — the entire `validations` dict can be loaded from an external file

### Inline File per Execution

The most powerful use is loading a separate validation file per execution context:

```yaml
executions:
  - name: "Production"
    vars:
      - BASE_URL: "https://api.prod.example.com"
    validations: !include validations/prod.yaml

  - name: "Staging"
    vars:
      - BASE_URL: "https://api.staging.example.com"
    validations: !include validations/staging.yaml

probes:
  - name: "Get User"
    type: rest
    endpoint: "${BASE_URL}/user"
    # no inline validation — comes entirely from execution validations block

  - name: "List Orders"
    type: rest
    endpoint: "${BASE_URL}/orders"
    # no inline validation
```

```yaml
# validations/prod.yaml — strict
"Get User":
  status: 200
  response_time: 300
  body:
    present:
      - "data.id"
      - "data.email"
    type:
      data.id: string
      data.email: string
    absent:
      - "debug"
      - "internal_flags"

"List Orders":
  status: 200
  response_time: 500
  body:
    type:
      "$": array
    length:
      "$": [1, null]
```

```yaml
# validations/staging.yaml — relaxed
"Get User":
  status: 200
  body:
    present:
      - "data.id"

"List Orders":
  status: "2xx"
```

### Inline Overrides with Variable Substitution

Variables from `vars` are available inside the `validations` block:

```yaml
executions:
  - name: "User A"
    vars:
      - ACCOUNT_ID: "123"
      - EXPECTED_REGION: "us-east-1"
    validations:
      "Get Account":
        status: 200
        body:
          equals:
            account.id: "${ACCOUNT_ID}"       # substituted at runtime
            account.region: "${EXPECTED_REGION}"

  - name: "User B"
    vars:
      - ACCOUNT_ID: "456"
      - EXPECTED_REGION: "eu-west-1"
    validations:
      "Get Account":
        status: 200
        body:
          equals:
            account.id: "${ACCOUNT_ID}"       # different value per execution
            account.region: "${EXPECTED_REGION}"

probes:
  - name: "Get Account"
    type: rest
    endpoint: "${BASE_URL}/accounts/${ACCOUNT_ID}"
```

### Mixing Inline and Override

A probe can have both an inline `validation:` and appear in `validations:`. The override always wins for that execution; other executions without an override use the inline block:

```yaml
executions:
  - name: "Production"     # uses validations override below
    vars:
      - ENV: "prod"
    validations:
      "Health Check":
        status: 200
        response_time: 200   # strict in prod

  - name: "Staging"        # no validations key — uses inline validation
    vars:
      - ENV: "staging"

probes:
  - name: "Health Check"
    type: rest
    endpoint: "${BASE_URL}/health"
    validation:              # used by Staging; ignored by Production
      status: "2xx"
      response_time: 2000
```

---

## Probe Definition

A Probe represents a single API call with optional validation and output capture.

### Schema

```yaml
- name: string                                     # REQUIRED: Unique probe name
  type: rest | graphql                             # REQUIRED: API type
  endpoint: string                                 # REQUIRED: URL with ${VAR} support

  # REST-specific
  method: GET | POST | PUT | DELETE | PATCH        # Default: GET
  headers:
    Header-Name: string
  body: object | array | string | !include path

  # GraphQL-specific
  query: string | !include path                    # REQUIRED for graphql
  variables:
    varName: any

  # Common options
  delay: number                                    # Seconds to wait before executing
  timeout: number                                  # Request timeout in seconds (default: 30)
  retry:
    max_attempts: integer                          # Total attempts, >= 1
    delay: number                                  # Seconds between retries (default: 0)
  verify: boolean                                  # SSL certificate verification (default: true)
  debug: boolean                                   # Print request/response to stderr (default: false)
  ignore: boolean | integer | string               # Skip probe if true/1/${VAR}=true or expression

  validation:                                      # Optional: Response validation
    <validation-spec>

  output:                                          # Optional: Capture values to variables
    VAR_NAME: path
```

### Field Descriptions

#### `name` (required)
- **Type:** String
- **Description:** Human-readable probe name
- **Note:** Duplicate names produce a validation warning. Output capture and reporting may behave unexpectedly with duplicates.

#### `type` (required)
- **Type:** String
- **Values:** `"rest"` or `"graphql"`

#### `endpoint` (required)
- **Type:** String with variable substitution
- **Examples:** `"https://api.example.com/users"`, `"${BASE_URL}/auth"`

#### `delay` (optional)
- **Type:** Number (float), seconds
- **Default:** None
- **Use cases:** Rate limiting compliance, waiting for async operations

#### `timeout` (optional)
- **Type:** Number (float), seconds
- **Default:** 30

#### `retry` (optional)
- **Type:** Object
- **Fields:**
  - `max_attempts` — integer >= 1, total number of attempts
  - `delay` — non-negative number, seconds between retries (default: 0)
- **Behavior:** Retries on request exceptions (timeout, connection error). Does NOT retry on validation failures.

```yaml
retry:
  max_attempts: 3
  delay: 2
```

#### `verify` (optional)
- **Type:** Boolean
- **Default:** `true`
- **Description:** Whether to verify SSL/TLS certificates on the request.
  Set to `false` for APIs using self-signed certificates or internal corporate CAs.
- **Note:** When `false`, SSL warnings are suppressed for that probe only — other probes are not affected.

```yaml
verify: false    # Skip cert validation for this probe
verify: true     # Explicit (same as default)
                 # Omitting verify also defaults to true
```

#### `debug` (optional)
- **Type:** Boolean
- **Default:** `false`
- **Output includes:** Request method, URL, headers, body preview (200 chars), response status, headers, body preview (500 chars), retry attempts

#### `ignore` (optional)
- **Type:** Boolean, Integer (0/1), String (`"${VAR}"` or expression)
- **Default:** `false` (probe runs)
- **Truthy values for string:** `"true"`, `"1"`, `"yes"`, `"on"`
- **Behavior:** Ignored probes do not execute, do not appear in output, and do not affect exit codes
- See [Expression Evaluation](#expression-evaluation) for expression syntax

---

## Group Definition

Groups enable parallel execution using a thread pool. Two mutually exclusive modes are supported: **flat** (classic) and **staged**.

### Flat Group Schema

```yaml
- group:
    name: string                        # Optional: auto-generated if not provided
    ignore: boolean | integer | string  # Optional: skip entire group
    probes:                             # REQUIRED (flat mode)
      - <probe>
      - <probe>
```

### Staged Group Schema

```yaml
- group:
    name: string                        # Optional: auto-generated if not provided
    ignore: boolean | integer | string  # Optional: skip entire group
    stages:                             # REQUIRED (staged mode)
      - name: string                    # Optional: auto-generated as "Stage N" if not provided
        probes:                         # REQUIRED
          - <probe>
          - <probe>
      - name: string
        probes:
          - <probe>
          - <probe>
```

### Flat Mode Behavior

- All probes in the group execute in parallel
- All probes share the same execution context (output variables are visible to all)
- Results maintain YAML declaration order
- The next item (probe or group) waits for all group probes to complete
- If 3 probes each take 2 seconds: sequential = 6s, parallel group = ~2s

### Staged Mode Behavior

- All stages execute in parallel with each other
- Probes within each stage execute sequentially
- Each stage gets an **isolated variable scope** — a snapshot of the parent context at group entry
- Output captured by a probe in Stage 1 is available to subsequent probes in Stage 1 only — it does not leak to Stage 2 or back to the parent
- If a probe's referenced variable is not set in its stage context, it is skipped (same behavior as top-level probes)
- The group finishes when all stages complete
- Results are reported flat, in stage declaration order, then probe declaration order within each stage

### Mutually Exclusive

A group must have either `probes` or `stages` — not both. The validator will report an error if both are present.

### Staged Group Example

```yaml
- group:
    name: "Auth + Product Flow"
    stages:
      - name: "User A Flow"
        probes:
          - name: "Auth - User A"         # runs first in this stage
            type: rest
            endpoint: "${AUTH_URL}"
            output:
              TOKEN_A: "data.token"
          - name: "Product - User A"      # runs after Auth - User A
            type: graphql                 # skipped if TOKEN_A not set
            endpoint: "${API_URL}/graphql"
            headers:
              Authorization: "Bearer ${TOKEN_A}"

      - name: "User B Flow"               # runs in parallel with User A Flow
        probes:
          - name: "Auth - User B"
            type: rest
            endpoint: "${AUTH_URL}"
            output:
              TOKEN_B: "data.token"       # TOKEN_B is isolated to this stage
          - name: "Product - User B"      # TOKEN_A is NOT visible here
            type: graphql
            endpoint: "${API_URL}/graphql"
            headers:
              Authorization: "Bearer ${TOKEN_B}"
```

---

## REST API Probes

### Content-Type Requirement

`Content-Type` header is **required** when `body` is present:

```yaml
- name: "Create User"
  type: rest
  endpoint: "https://api.example.com/users"
  method: POST
  headers:
    Content-Type: "application/json"
  body:
    name: "John Doe"
```

### Body Types

```yaml
# Inline object
body:
  name: "John"
  email: "john@example.com"

# Inline array
body:
  - id: 1
  - id: 2

# String (XML, plain text)
body: |
  <?xml version="1.0"?>
  <user><name>John</name></user>

# External file
body: !include ../includes/user-payload.json
```

---

## GraphQL API Probes

### Schema

```yaml
- name: string
  type: graphql
  endpoint: string
  query: string | !include path    # REQUIRED
  variables:
    varName: value
  headers:
    Authorization: string
  validation: ...
  output: ...
```

### GraphQL Variables and Types

GraphQL `variables` are sent verbatim in the request payload. Use [Type Coercion Tags](#type-coercion-tags) to ensure variables are sent as the correct JSON type when the value comes from an environment variable (which is always a string):

```yaml
variables:
  limit: !int "${PAGE_SIZE}"        # Sent as JSON number
  active: !bool "${IS_ACTIVE}"      # Sent as JSON boolean
  threshold: !float "${MIN_SCORE}"  # Sent as JSON float
  tag: "${TAG}"                     # Sent as JSON string (default)
```

---

## XML/SOAP API Probes

XML and SOAP APIs use `type: rest` with XML content and XPath for validation.

```yaml
- name: "SOAP Request"
  type: rest
  endpoint: "https://soap.example.com/service"
  method: POST
  headers:
    Content-Type: "text/xml; charset=utf-8"
    SOAPAction: "http://example.com/GetUser"
  body: !include ../includes/soap-request.xml
  validation:
    status: 200
    body:
      present:
        - "//default:GetUserResult/default:name"
      equals:
        "//default:GetUserResult/default:name": "John Doe"
```

See [XML/SOAP Guide](XML_SOAP_GUIDE.md) for complete XPath documentation.

---

## Validation Specification

### Schema

```yaml
validation:
  status: integer | string              # Expected status code or pattern
  response_time: integer                # Max response time in milliseconds
  headers:
    <validator>: <spec>
  body:
    <validator>: <spec>
```

### Available Validators

| Validator | Description | Works On |
|-----------|-------------|----------|
| `status` | Exact or pattern status code | — |
| `response_time` | Max response time (ms) | — |
| `present` | Fields must exist | Headers, Body |
| `absent` | Fields must NOT exist | Headers, Body |
| `equals` | Exact value match | Headers, Body |
| `matches` | Regex pattern match (non-strings coerced to string) | Headers, Body |
| `type` | Type checking | Body |
| `contains` | Substring / array element | Headers, Body |
| `range` | Numeric bounds | Body |
| `length` | Array or string length | Body |

### Status Validation

```yaml
status: 200       # Exact match
status: "2xx"     # Any 200–299
status: "3xx"     # Any 300–399
status: "4xx"     # Any 400–499
status: "5xx"     # Any 500–599
```

### Response Time Validation

```yaml
validation:
  response_time: 1000    # Must respond within 1000ms
```

The actual response time is always shown in the report output regardless of whether `response_time` is set in validation.

### Body Path Notation

- **JSON dot notation:** `user.email`, `items[0].id`
- **JSONPath:** `$.data.plans`, `$[0].id`
- **Root array:** `$` (entire array), `$[0]` (first element)
- **XPath (XML):** `//user/email`

### Body Validators

**present / absent:**
```yaml
body:
  present:
    - "user.id"
    - "user.email"
  absent:
    - "password"
    - "secret_key"
```

**equals:**
```yaml
body:
  equals:
    user.id: "12345"
    user.active: true
    user.email: "${EXPECTED_EMAIL}"
```

**matches:**
```yaml
body:
  matches:
    user.email: "^[a-z]+@example\\.com$"
    user.id: "^[0-9]+$"     # string field
    user.age: "^\\d+$"      # integer field — coerced to string before matching
```

**type:**
```yaml
body:
  type:
    user.name: string
    user.age: integer
    user.balance: number
    user.active: boolean
    user.tags: array
    user.metadata: object
    user.deleted_at: null        # unquoted null works
    user.deleted_at: "null"      # quoted string also works
```

**contains:**
```yaml
body:
  contains:
    user.tags: "premium"      # Array element or substring
    user.bio: "developer"
```

**range:**
```yaml
body:
  range:
    user.age: [18, 100]         # Min and max (inclusive)
    user.score: [0, null]       # Min only (no upper bound)
    user.balance: [null, 1000]  # Max only (no lower bound)
```

> **Note:** Range bounds must be literal numbers or `null`. Variable substitution (`${VAR}`) is not supported for range bounds — use literal values only.

**length:**
```yaml
body:
  length:
    items: 5              # Exactly 5
    results: [1, 100]     # Between 1–100
    name: [0, 50]         # String length 0–50 chars
    tags: [1, null]       # At least 1, no upper limit
```

### Root-Level Array Responses

When the response body is an array (not wrapped in an object):

```yaml
body:
  type:
    "$": array
  length:
    "$": [1, 100]
  present:
    - "$[0].id"
    - "$[0].name"
  equals:
    "$[0].id": 1
```

---

## Output Variables

Capture values from responses for use in subsequent probes.

### Schema

```yaml
output:
  VAR_NAME: path
```

### Path Convention

Output paths use the **same bare path convention as validators** — no prefix required for body fields:

| Path | Extracts |
|------|----------|
| `data.token` | Body field `data.token` |
| `$.data.items[0].id` | JSONPath into body |
| `headers.X-Request-ID` | Response header |
| `status` | HTTP status code (integer) |

```yaml
# Body fields — bare path, same as validators
output:
  TOKEN: "data.access_token"
  USER_ID: "data.user.id"
  FIRST_ITEM: "$.data.items[0].id"

# Headers — prefix with headers.
output:
  REQUEST_ID: "headers.X-Request-ID"
  RATE_LIMIT: "headers.X-RateLimit-Remaining"

# Status code
output:
  LAST_STATUS: "status"
```

### Variable Scope

- Variables persist within an execution context throughout the run
- Each execution context has isolated variables
- Variables captured in Probe 1 are available in Probe 2, 3, etc.
- Variables do NOT leak between execution contexts

### Use in Subsequent Probes

```yaml
probes:
  - name: "Login"
    endpoint: "https://api.example.com/auth"
    output:
      TOKEN: "data.access_token"

  - name: "Get Profile"
    endpoint: "https://api.example.com/profile"
    headers:
      Authorization: "Bearer ${TOKEN}"
```

---

## Include Directive

Load content from external files using `!include`.

### Syntax

```yaml
field: !include path/to/file.ext
```

Paths are resolved **relative to the config file location**.

### Supported File Types

| Extension | Parsed As | Use For |
|-----------|-----------|---------|
| `.json` | JSON | Request bodies, GraphQL variables |
| `.yaml`, `.yml` | YAML | Structured data, validation fragments |
| `.graphql` | Plain text | GraphQL queries |
| `.xml` | Plain text | SOAP envelopes |
| Other | Plain text | Any text content |

### Where `!include` Works

`!include` is processed at YAML load time, before variable substitution. It works anywhere in the config that expects the type of data the file contains:

```yaml
body: !include ../includes/payload.json           # ✅ REST body
query: !include ../includes/query.graphql         # ✅ GraphQL query
variables: !include ../includes/variables.json    # ✅ Entire variables object
variables:
  input: !include ../includes/item-input.json     # ✅ Nested in variables
```

### Variable Substitution in Included Files

`!include` runs first, then variable substitution runs at execution time. So `${VAR}` placeholders inside included files are substituted correctly:

```json
// includes/auth-request.json
{
  "client_id": "${CLIENT_ID}",
  "client_secret": "${CLIENT_SECRET}"
}
```

```yaml
# config.yaml — ${CLIENT_ID} will be substituted at runtime
body: !include ../includes/auth-request.json
```

**Note:** You cannot use `${VAR}` inside the path of an `!include` itself, because substitution has not run yet when the YAML loader processes the directive.

See [Include Directive Guide](INCLUDE_DIRECTIVE.md) for complete documentation.

---

## Variable Substitution

Variables are substituted using `${VAR_NAME}` syntax at execution time.

### Variable Sources (priority order)

1. **Execution vars** (highest — from `executions[current].vars`)
2. **Environment variables**
3. **Output variables** (captured from previous probes in the same run)

### Where Variables Work

✅ **Supported:**
- `endpoint`
- `headers` (values)
- `body` (all nested values)
- `query`
- `variables` (GraphQL variable values)
- All validation values (`equals`, `matches`, `contains`)

❌ **Not supported:**
- Validation field paths / keys (e.g. `${FIELD}: value` on the left side)
- Probe `name`
- `!include` file paths

### Examples

```yaml
endpoint: "${BASE_URL}/users/${USER_ID}"

headers:
  Authorization: "Bearer ${TOKEN}"

body:
  user_id: "${USER_ID}"
  region: "${REGION}"

validation:
  body:
    equals:
      user_id: "${USER_ID}"
    matches:
      email: "^${USER_ID}@.*"
```

---

## Type Coercion Tags

By default, environment variables and execution vars are strings. When a GraphQL operation or downstream API requires a specific JSON type (integer, boolean, float), use type coercion tags.

### Supported Tags

| Tag | Target Type | Fallback on failure |
|-----|-------------|---------------------|
| `!int` | Integer | String + `[WARN]` to stderr |
| `!float` | Float | String + `[WARN]` to stderr |
| `!bool` | Boolean | String + `[WARN]` to stderr |
| `!str` | String | N/A (always succeeds) |

### Syntax

```yaml
field: !int "${VAR}"       # Substitute then coerce to int
field: !bool "${VAR}"      # Substitute then coerce to bool
field: !float "${VAR}"     # Substitute then coerce to float
field: !str "${VAR}"       # Explicit string (same as default)
```

### Boolean Coercion Rules

| Input value | Result |
|-------------|--------|
| `"true"`, `"1"`, `"yes"` | `true` |
| `"false"`, `"0"`, `"no"` | `false` |
| Anything else | String fallback + `[WARN]` |

### Where Tags Apply

Tags are most useful on GraphQL `variables` where the schema enforces types:

```yaml
- name: "Search Products"
  type: graphql
  endpoint: "${API_URL}"
  query: |
    query($limit: Int!, $active: Boolean!, $threshold: Float!) {
      products(limit: $limit, active: $active, minScore: $threshold) {
        id name
      }
    }
  variables:
    limit: !int "${PAGE_SIZE}"         # Int! — must be integer
    active: !bool "${SHOW_ACTIVE}"     # Boolean! — must be boolean
    threshold: !float "${MIN_SCORE}"   # Float! — must be float
    tag: "${TAG}"                      # String — default, no tag needed
```

Tags also work on any other probe field that accepts a value:

```yaml
body:
  count: !int "${ITEM_COUNT}"
  ratio: !float "${RATIO}"
  enabled: !bool "${FEATURE_FLAG}"
```

### Behavior When Coercion Fails

Coercion is soft — it never causes a probe to fail:

```
# PAGE_SIZE="abc"
[WARN] !int coercion failed for value 'abc' — keeping as string

# SHOW_ACTIVE="maybe"
[WARN] !bool coercion failed for value 'maybe' (expected true/false/yes/no/1/0) — keeping as string
```

The variable is kept as a string and the request proceeds. The API may then reject the type, which will surface as a validation failure.

### Literal Values

Tags also work on literal (non-variable) values, though it is rarely needed since YAML already handles native types:

```yaml
# These are equivalent:
limit: !int "10"
limit: 10            # YAML native integer — preferred for literals
```

---

## Progress Reporting

Execution progress is always printed to stderr. Actual response time is shown for every probe.

There are two distinct output sections: **live progress** printed as probes execute, and the **final report** printed after all probes complete.

### Live Progress Format

Printed to stderr immediately as each probe runs. When multiple executions are active, each line is suffixed with `[execution name]` so interleaved output from concurrent executions is identifiable:

```
  → OAuth Authentication [Production]
    ✓ Passed [Production]
  → OAuth Authentication [Staging]
    ✓ Passed (validation skipped) [Staging]
  → Get User Profile [Production]
    ✓ Passed [Production]
  → Get User Profile [Staging]
    ✗ Failed (1 error(s)) [Staging]
  → Cleanup [Production]
    ⊗ Skipped: Variable CACHE_ID not defined
```

For single-execution runs (no `executions` block), the suffix is omitted:

```
  → OAuth Authentication
    ✓ Passed

  → Get User Profile
    ✗ Failed (1 error(s))
```

### Final Report Format

When using `executions`, the live interleaved progress is followed by a separator and then the full structured report, printed once all executions have completed. Each execution gets its own section headed by `▶ Executed: <name>`.

On **failure:**

```
============================================================
EXECUTION COMPLETE — FULL REPORT
============================================================
============================================================
VALIDATION FAILURES
============================================================

▶ Executed: Production Context
============================================================
Production Context
------------------------------------------------------------
Probe: Get User Profile
  Endpoint: https://api.example.com/profile
  Response time: 1821ms
  ✗ Expected status 200, got 404
    Field: status_code
    Expected: 200
    Got: 404

Probe: Cleanup
  Endpoint: https://api.example.com/cleanup
  ⊗ Skipped: Variable CACHE_ID not defined

============================================================
SUMMARY
  Runs:   0/1 passed
  Probes: 1/3 passed
  Skipped: 1/3 skipped
============================================================
```

On **success:**

```
============================================================
EXECUTION COMPLETE — FULL REPORT
============================================================
============================================================
VALIDATION PASSED
============================================================

▶ Executed: Production Context
============================================================
Production Context
------------------------------------------------------------
Probe: OAuth Authentication
  Endpoint: https://api.example.com/auth
  Response time: 243ms
  ✓ Passed

Probe: Get User Profile
  Endpoint: https://api.example.com/profile
  Response time: 1821ms
  ✓ Passed

============================================================
SUMMARY
  Runs:   1/1 passed
  Probes: 2/2 passed
============================================================
```

### Progress Symbols

| Symbol | Meaning |
|--------|---------|
| `▶` | Execution context starting |
| `→` | Probe starting |
| `✓ Passed` | Probe passed with validation |
| `✓ Passed (no validation)` | Probe executed but has no inline `validation:` block defined |
| `✓ Passed (validation skipped)` | Probe executed but validation was explicitly suppressed via `~` null override in the execution's `validations` block |
| `✗` | Probe failed |
| `⊗` | Probe skipped (not executed) |

### Response Time

Actual response time is shown for every completed probe, regardless of whether `response_time` validation is configured. The `response_time` validation field sets a threshold that triggers a failure; the reported time is always shown for observability.

### Capturing Output

All progress goes to stderr:

```bash
# Progress only (suppress stdout)
./run.sh config.yaml 2>&1 >/dev/null

# Save progress to log
./run.sh config.yaml 2>execution.log

# See both (normal)
./run.sh config.yaml
```

---

## Expression Evaluation

Expressions are supported in `output` and `ignore` fields.

### Supported Functions

| Function | Returns | Example |
|----------|---------|---------|
| `len(VAR)` | Integer | `len(body.offers)` |
| `has(VAR)` | Boolean | `has(body.data)` |
| `empty(VAR)` | Boolean | `empty(body.errors)` |

### Supported Operators

`==`, `!=`, `>`, `<`, `>=`, `<=`, `&&`, `||`, `!`

### Path Syntax in Expressions

Expressions (used in `len()`, `has()`, `empty()`, and comparisons) use a **`body.` prefix** to reference response body fields. This is distinct from output capture paths which use bare paths:

| Context | Syntax | Example |
|---------|--------|---------|
| Output capture path | Bare path | `"data.offers"` |
| Expression referencing body | `body.` prefix | `"len(body.offers)"` |
| Expression referencing captured variable | Variable name | `"OFFER_COUNT <= 2"` |

### In `output`

```yaml
output:
  OFFERS: "data.offers"                              # Bare path — output capture
  OFFER_COUNT: "len(body.offers)"                    # Expression — body. prefix required
  HAS_CONTENT: "has(body.offers[0].content)"         # Expression — body. prefix required
  IS_VALID: "len(body.offers) > 2 && has(body.offers[0].content)"  # Expression
```

### In `ignore`

```yaml
ignore: "OFFER_COUNT <= 2"                           # References captured variable
ignore: "!has(body.premium)"                         # References body directly
ignore: "len(body.offers) > 2 && has(body.offers[0].content)"  # Body expression
```

### Error Handling

| Location | On error |
|----------|----------|
| `output` | Variable set to `None`, `[WARN]` to stderr |
| `ignore` | Returns `false` (probe runs), `[WARN]` to stderr |
| Validation `ignore` | Returns `false` (validation runs), `[WARN]` to stderr |

---

## Validation Conditional Ignore

`headers` and `body` validation blocks support an `ignore` field to skip validation conditionally.

### Schema

```yaml
validation:
  headers:
    ignore: string      # Expression — skip all header validation if true
    present: [...]
    equals: {...}
  body:
    ignore: string      # Expression — skip all body validation if true
    present: [...]
    type: {...}
```

### Supported Expressions in `ignore`

Validation `ignore` expressions can reference `body.*` paths and captured output variables. The HTTP status code is **not** available as a variable in validation ignore expressions — use body paths and captured variables only.

### Examples

```yaml
validation:
  status: "2xx"

  headers:
    ignore: "empty(body.data)"  # Skip header checks if body is empty
    present:
      - "X-Request-ID"

  body:
    ignore: "empty(body.data)"  # Skip body checks if data is empty
    present:
      - "data.id"
    length:
      data: [1, 100]
```

```yaml
# Using a captured output variable from a previous probe
validation:
  body:
    ignore: "SKIP_BODY_CHECK == 'true'"   # SKIP_BODY_CHECK captured earlier
    present:
      - "data.results"
```

---

## Complete Examples

### Example 1: Multi-Context with SSL Skip

```yaml
executions:
  - name: "Production"
    vars:
      - ACCOUNT: "123456"
      - API_KEY: "${PROD_API_KEY}"

  - name: "Internal Staging"
    vars:
      - ACCOUNT: "999999"
      - API_KEY: "${STAGING_API_KEY}"

probes:
  - name: "Get Account Info"
    type: rest
    endpoint: "https://internal-staging.corp.com/accounts/${ACCOUNT}"
    verify: false                  # Self-signed cert on internal staging
    headers:
      X-API-Key: "${API_KEY}"
    validation:
      status: 200
      response_time: 500
      body:
        equals:
          account_id: "${ACCOUNT}"
        type:
          balance: number
```

### Example 2: GraphQL with Typed Variables

```yaml
executions:
  - name: "Production"
    vars:
      - PAGE_SIZE: "20"
      - SHOW_ACTIVE: "true"
      - MIN_SCORE: "0.75"

probes:
  - name: "Search Products"
    type: graphql
    endpoint: "${API_URL}/graphql"
    headers:
      Authorization: "Bearer ${TOKEN}"
    query: |
      query($limit: Int!, $active: Boolean!, $threshold: Float!) {
        products(limit: $limit, active: $active, minScore: $threshold) {
          id
          name
          score
        }
      }
    variables:
      limit: !int "${PAGE_SIZE}"
      active: !bool "${SHOW_ACTIVE}"
      threshold: !float "${MIN_SCORE}"
    validation:
      status: 200
      body:
        present:
          - "data.products"
        type:
          data.products: array
        length:
          data.products: [1, null]
        absent:
          - "errors"
```

### Example 3: Auth Flow with Output Capture

```yaml
probes:
  - name: "Login"
    type: rest
    endpoint: "${BASE_URL}/auth/token"
    method: POST
    headers:
      Content-Type: "application/json"
    body:
      client_id: "${CLIENT_ID}"
      client_secret: "${CLIENT_SECRET}"
    output:
      TOKEN: "data.access_token"
      EXPIRES_IN: "data.expires_in"
      REQUEST_ID: "headers.X-Request-ID"
    validation:
      status: 200
      body:
        present:
          - "data.access_token"
        type:
          data.access_token: string

  - group:
      probes:
        - name: "Get Profile"
          type: rest
          endpoint: "${BASE_URL}/profile"
          headers:
            Authorization: "Bearer ${TOKEN}"
          validation:
            status: 200

        - name: "Get Settings"
          type: rest
          endpoint: "${BASE_URL}/settings"
          headers:
            Authorization: "Bearer ${TOKEN}"
          validation:
            status: 200
```

### Example 5: Per-Execution Validation Overrides

```yaml
# Probe definitions are environment-agnostic.
# Each execution supplies its own validation rules via !include.

executions:
  - name: "Production"
    vars:
      - BASE_URL: "https://api.prod.example.com"
      - API_KEY: "${PROD_API_KEY}"
    validations: !include validations/prod.yaml

  - name: "Staging"
    vars:
      - BASE_URL: "https://api.staging.example.com"
      - API_KEY: "${STAGING_API_KEY}"
    validations: !include validations/staging.yaml

probes:
  - name: "Login"
    type: rest
    endpoint: "${BASE_URL}/auth/token"
    method: POST
    headers:
      Content-Type: "application/json"
      X-API-Key: "${API_KEY}"
    body:
      grant_type: "client_credentials"
    output:
      TOKEN: "data.access_token"

  - name: "Get User"
    type: rest
    endpoint: "${BASE_URL}/user"
    headers:
      Authorization: "Bearer ${TOKEN}"
```

```yaml
# validations/prod.yaml
"Login":
  status: 200
  response_time: 300
  body:
    present:
      - "data.access_token"
      - "data.expires_in"
    type:
      data.access_token: string
      data.expires_in: integer

"Get User":
  status: 200
  response_time: 300
  body:
    present:
      - "data.id"
      - "data.email"
      - "data.role"
    absent:
      - "debug"
      - "internal_flags"
    type:
      data.id: string
      data.role: string
```

```yaml
# validations/staging.yaml
"Login":
  status: 200
  body:
    present:
      - "data.access_token"

"Get User":
  status: "2xx"
  body:
    present:
      - "data.id"
```

---

### Example 4: Retry, Timeout, and Debug

```yaml
probes:
  - name: "Health Check"
    type: rest
    endpoint: "${BASE_URL}/health"
    timeout: 5
    retry:
      max_attempts: 3
      delay: 2
    validation:
      status: "2xx"
      response_time: 3000

  - name: "Slow Internal API"
    type: rest
    endpoint: "https://internal.corp.com/data"
    verify: false
    timeout: 30
    debug: true
    retry:
      max_attempts: 2
      delay: 5
    validation:
      status: 200
      body:
        type:
          "$": array
        length:
          "$": [1, null]
```
