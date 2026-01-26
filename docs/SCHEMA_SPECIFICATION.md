# API-Probe YAML Schema Specification

**Version:** 2.0.0  
**Last Updated:** 2025-01-26

## Overview

This document provides the complete YAML schema specification for api-probe configuration files. The schema defines how to declare API probes, validations, execution contexts, and parallel execution flows for post-deployment functional testing.

---

## Table of Contents

- [Root Structure](#root-structure)
- [Executions Block](#executions-block)
- [Probe Definition](#probe-definition)
- [Group Definition](#group-definition)
- [REST API Probes](#rest-api-probes)
- [GraphQL API Probes](#graphql-api-probes)
- [XML/SOAP API Probes](#xmlsoap-api-probes)
- [Validation Specification](#validation-specification)
- [Output Variables](#output-variables)
- [Include Directive](#include-directive)
- [Variable Substitution](#variable-substitution)
- [Complete Examples](#complete-examples)

---

## Root Structure

The root of every api-probe configuration file contains two optional top-level keys:

```yaml
executions:               # OPTIONAL: Array of execution contexts
  - name: string
    vars: []
  # ...

probes:                    # REQUIRED: Array of Probe or Group objects
  - <probe-or-group>
  - <probe-or-group>
  # ...
```

### Schema

```yaml
executions:               # OPTIONAL: Define multiple execution contexts
  - name: string          # OPTIONAL: Name for this execution (auto-generated if not provided)
    vars:                 # REQUIRED: List of variable definitions
      - VAR_NAME: value   # Variable name and value

probes:                   # REQUIRED: Array of Probe or Group objects
  - name: string          # Probe definition
    # ...
  - group:                # Group definition (parallel execution)
      probes: []
    # ...
```

### Rules

- If `executions` is present and non-empty, each execution runs all probes with its own variables
- If `executions` is absent or empty, probes run once with environment variables
- `probes` array is required and must contain at least one probe or group
- Probes execute in YAML sequence order (top to bottom)
- Groups execute probes in parallel
- Empty `probes` array is valid (no-op)

---

## Executions Block

Define multiple execution contexts to run the same probes with different variables.

### Schema

```yaml
executions:
  - name: string                    # OPTIONAL: Execution name (auto-generated if not provided)
    vars:                           # REQUIRED: List of variable definitions
      - VAR_NAME: "value"           # Hardcoded value
      - VAR_NAME: "${ENV_VAR}"      # Reference environment variable
```

### Field Descriptions

#### `name` (optional)
- **Type:** String
- **Description:** Human-readable name for this execution context
- **Auto-generation:** If not provided, generates like "awesome-paris", "elegant-tokyo"
- **Example:** `"Production User A"`, `"Staging Environment"`
- **Usage:** Shown in failure reports

#### `vars` (required)
- **Type:** List of key-value pairs
- **Description:** Variables for this execution context
- **Syntax:** `- VAR_NAME: "value"`
- **Variable Resolution:**
  1. Check vars in current execution
  2. If value contains `${...}`, resolve from environment
  3. If not found, check environment variables
  4. If still not found, error on use

### Examples

```yaml
executions:
  # Example 1: Hardcoded values
  - name: "Production User A"
    vars:
      - ACCOUNT: "123456789"
      - CLIENT_ID: "client-prod-a"
      - REGION: "us-east-1"
  
  # Example 2: Mix of hardcoded and environment variables
  - name: "Staging"
    vars:
      - ACCOUNT: "999999999"
      - API_KEY: "${STAGING_API_KEY}"    # From environment
      - REGION: "us-west-2"
  
  # Example 3: Auto-generated name
  - vars:                                # Name will be like "beautiful-london"
      - ACCOUNT: "555555555"
      - CLIENT_ID: "client-test"
```

### Variable Resolution Order

For any variable reference `${VAR}` in probes:

1. **First:** Check `executions[current].vars` for `VAR`
2. **Second:** If value is `${OTHER}`, resolve `OTHER` from environment
3. **Third:** If `VAR` not in execution vars, check environment
4. **Fourth:** If still not found, error when variable is used

### Use Cases

- **Multi-user probing:** Probe same flow with different user accounts
- **Multi-region probing:** Probe same API in different regions
- **Multi-environment:** Probe production and staging in one run
- **A/B testing:** Test different configurations

---

## Probe Definition

A Probe represents a single API call with optional validation and output capture.

### Schema

```yaml
- name: string                           # REQUIRED: Unique probe name
  type: rest | graphql                   # REQUIRED: API type
  endpoint: string                       # REQUIRED: URL with ${VAR} support
  
  # REST-specific fields
  method: GET | POST | PUT | DELETE | PATCH  # Optional, default: GET
  headers:                               # Optional: HTTP headers
    Header-Name: string                  # Value with ${VAR} support
  body: object | array | string | !include path  # Optional: Request body
  
  # GraphQL-specific fields
  query: string | !include path          # REQUIRED for GraphQL: Query/mutation
  variables:                             # Optional: GraphQL variables
    varName: any                         # Value with ${VAR} support
  
  # Common fields
  validation:                            # Optional: Response validation
    <validation-spec>
  output:                                # Optional: Variable capture
    varName: path                        # Extract values to variables
```

### Field Descriptions

#### `name` (required)
- **Type:** String
- **Description:** Human-readable probe name, must be unique across all probes
- **Example:** `"OAuth Authentication"`, `"Get User Profile"`

#### `type` (required)
- **Type:** String
- **Values:** `"rest"` or `"graphql"`
- **Description:** Type of API being probed

#### `endpoint` (required)
- **Type:** String with variable substitution
- **Description:** Full URL including protocol
- **Examples:**
  - `"https://api.example.com/users"`
  - `"https://api.example.com/${REGION}/data"`
  - `"${BASE_URL}/auth"`

---

## Group Definition

Groups enable parallel execution of probes. All probes within a group run simultaneously using ThreadPoolExecutor.

### Schema

```yaml
- group:
    probes:
      - name: string
        # ... probe definition
      - name: string
        # ... probe definition
```

### Behavior

- All probes in group execute **in parallel**
- Results maintain original order
- Next item (probe or group) waits for all group probes to complete
- Use for probes that can run independently

### Examples

```yaml
probes:
  # Sequential probe
  - name: "Setup"
    endpoint: "https://api.example.com/setup"
  
  # Parallel group - all 3 run simultaneously
  - group:
      probes:
        - name: "Get User A"
          endpoint: "https://api.example.com/users/1"
        - name: "Get User B"
          endpoint: "https://api.example.com/users/2"
        - name: "Get User C"
          endpoint: "https://api.example.com/users/3"
  
  # Sequential probe after group
  - name: "Cleanup"
    endpoint: "https://api.example.com/cleanup"
```

### Performance

If 3 probes each take 2 seconds:
- **Sequential:** 6 seconds total
- **Parallel (group):** ~2 seconds total ⚡

---

## REST API Probes

REST probes support all standard HTTP methods.

### Schema

```yaml
- name: string
  type: rest
  endpoint: string
  method: GET | POST | PUT | DELETE | PATCH    # Default: GET
  headers:                                      # Optional
    Content-Type: string
    Authorization: string
    # ... other headers
  body: object | array | string | !include path  # Optional
  validation:                                   # Optional
    # ... validation spec
  output:                                       # Optional
    # ... output variables
```

### Content-Type Requirement

If `body` is present, `Content-Type` header is **required**:

```yaml
- name: "Create User"
  type: rest
  endpoint: "https://api.example.com/users"
  method: POST
  headers:
    Content-Type: "application/json"    # REQUIRED when body present
  body:
    name: "John Doe"
```

### Body Types

**Inline Object:**
```yaml
body:
  name: "John"
  email: "john@example.com"
```

**Inline Array:**
```yaml
body:
  - id: 1
  - id: 2
```

**String (for XML, plain text):**
```yaml
body: |
  <?xml version="1.0"?>
  <user><name>John</name></user>
```

**External File:**
```yaml
body: !include ../includes/user-payload.json
```

---

## GraphQL API Probes

GraphQL probes support queries, mutations, and variables.

### Schema

```yaml
- name: string
  type: graphql
  endpoint: string
  query: string | !include path    # REQUIRED: GraphQL query/mutation
  variables:                        # Optional: Query variables
    varName: value
  headers:                          # Optional
    Authorization: string
  validation:                       # Optional
    # ... validation spec
  output:                           # Optional
    # ... output variables
```

### Examples

**Inline Query:**
```yaml
- name: "Get Repository"
  type: graphql
  endpoint: "https://api.github.com/graphql"
  query: |
    query GetRepo($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        name
        stargazerCount
      }
    }
  variables:
    owner: "torvalds"
    name: "linux"
```

**Query from File:**
```yaml
- name: "Get Repository"
  type: graphql
  endpoint: "https://api.github.com/graphql"
  query: !include ../includes/repo-query.graphql
  variables:
    owner: "${REPO_OWNER}"
    name: "${REPO_NAME}"
```

---

## XML/SOAP API Probes

XML and SOAP APIs use REST type with XML content and XPath for validation.

### Schema

```yaml
- name: string
  type: rest
  endpoint: string
  method: POST                      # Usually POST for SOAP
  headers:
    Content-Type: "text/xml; charset=utf-8"
    SOAPAction: string              # SOAP-specific header
  body: string | !include path      # XML/SOAP envelope
  validation:
    body:
      # XPath expressions for XML
```

### Example

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

Validates HTTP response status, headers, and body.

### Schema

```yaml
validation:
  status: integer                   # Optional: Expected status code
  headers:                          # Optional: Header validations
    <validator>: <spec>
  body:                             # Optional: Body validations
    <validator>: <spec>
```

### Available Validators

| Validator | Description | Works On | Example |
|-----------|-------------|----------|---------|
| `status` | Exact status code match | - | `status: 200` |
| `present` | Fields must exist | Headers, Body | `present: ["id", "email"]` |
| `absent` | Fields must NOT exist | Headers, Body | `absent: ["password"]` |
| `equals` | Exact value match | Headers, Body | `equals: { id: "123" }` |
| `matches` | Regex pattern match | Headers, Body | `matches: { email: "^.*@.*$" }` |
| `type` | Type checking | Body | `type: { age: integer }` |
| `contains` | Substring/element check | Headers, Body | `contains: { name: "John" }` |
| `range` | Numeric bounds | Body | `range: { age: [0, 120] }` |

### Status Validation

```yaml
validation:
  status: 200    # Exact match required
```

### Header Validation

**Present:**
```yaml
validation:
  headers:
    present:
      - "Content-Type"
      - "Authorization"
```

**Equals:**
```yaml
validation:
  headers:
    equals:
      Content-Type: "application/json"
      X-Custom: "${EXPECTED_VALUE}"    # Variable substitution!
```

**Contains:**
```yaml
validation:
  headers:
    contains:
      Content-Type: "json"    # Substring match
```

**Matches:**
```yaml
validation:
  headers:
    matches:
      Content-Length: "^[0-9]+$"    # Regex pattern
```

**Absent:**
```yaml
validation:
  headers:
    absent:
      - "X-Debug-Token"
      - "X-Internal-IP"
```

### Body Validation

**Path Notation:**
- JSON: Dot notation or JSONPath (`user.email`, `items[0].id`, `items[*].id`)
- XML: XPath (`//user/email`, `//item[1]/id`)

**Present:**
```yaml
validation:
  body:
    present:
      - "user.id"
      - "user.email"
      - "user.address.city"
```

**Absent:**
```yaml
validation:
  body:
    absent:
      - "password"
      - "secret_key"
      - "api_token"
```

**Equals:**
```yaml
validation:
  body:
    equals:
      user.id: "12345"
      user.name: "John Doe"
      user.active: true
      user.email: "${EXPECTED_EMAIL}"    # Variable substitution!
```

**Matches:**
```yaml
validation:
  body:
    matches:
      user.email: "^[a-z]+@example\\.com$"
      user.id: "^[0-9]+$"
      user.uuid: "^[0-9a-f-]+$"
```

**Type:**
```yaml
validation:
  body:
    type:
      user.name: string
      user.age: integer
      user.balance: number
      user.active: boolean
      user.tags: array
      user.metadata: object
      user.deleted_at: "null"    # Note: Quote "null"
```

Valid types: `string`, `integer`, `number`, `boolean`, `array`, `object`, `"null"`

**Contains:**
```yaml
validation:
  body:
    contains:
      user.tags: "premium"        # Array element or substring
      user.bio: "developer"       # Substring match
```

**Range:**
```yaml
validation:
  body:
    range:
      user.age: [18, 100]         # Min and max (inclusive)
      user.score: [0, null]       # Min only (no maximum)
      user.balance: [null, 1000]  # Max only (no minimum)
```

### Variable Substitution in Validation

**All validation values** support variable substitution:

```yaml
executions:
  - vars:
      - USER_ID: "12345"
      - REGION: "us-east"

probes:
  - validation:
      body:
        equals:
          user_id: "${USER_ID}"           # Validates against "12345"
          region: "${REGION}"              # Validates against "us-east"
        matches:
          email: "^${USER_ID}@.*"         # Pattern with variable
        range:
          age: [0, "${MAX_AGE}"]          # Range with variable
```

---

## Output Variables

Capture values from responses to use in subsequent probes.

### Schema

```yaml
output:
  VAR_NAME: "path"              # Capture from body
  VAR_NAME: "body.path.to.field"
  VAR_NAME: "header.Header-Name"
```

### Path Prefixes

- `body.` - Extract from response body (default if no prefix)
- `header.` - Extract from response headers

### Examples

**Capture from Body:**
```yaml
output:
  USER_ID: "body.id"
  ACCESS_TOKEN: "body.access_token"
  REFRESH_TOKEN: "body.tokens.refresh"
```

**Capture from Headers:**
```yaml
output:
  REQUEST_ID: "header.X-Request-ID"
  RATE_LIMIT: "header.X-RateLimit-Remaining"
```

**Use in Subsequent Probes:**
```yaml
probes:
  - name: "Login"
    endpoint: "https://api.example.com/auth"
    output:
      TOKEN: "body.access_token"
  
  - name: "Get Profile"
    endpoint: "https://api.example.com/profile"
    headers:
      Authorization: "Bearer ${TOKEN}"    # Use captured variable
```

### Variable Scope

- Variables persist within an execution context
- Each execution context has isolated variables
- Variables captured in Probe 1 are available in Probe 2, 3, etc.
- Variables do NOT leak between execution contexts

---

## Include Directive

Load content from external files using `!include`.

### Syntax

```yaml
body: !include path/to/file.ext
query: !include path/to/query.graphql
```

### Supported File Types

| Extension | Parse As | Use For |
|-----------|----------|---------|
| `.json` | JSON | Request bodies |
| `.yaml`, `.yml` | YAML | Structured data |
| `.graphql` | Plain text | GraphQL queries |
| `.xml` | Plain text | XML/SOAP envelopes |
| Others | Plain text | Any text content |

### Path Resolution

Paths are **relative to the config file location**:

```
project/
├── tests/
│   └── api-tests.yaml          # Config file here
└── includes/
    └── user.json                # Include file here

# In api-tests.yaml:
body: !include ../includes/user.json
```

### Variable Substitution in Included Files

Variables **ARE substituted** in included files:

**File: includes/template.json**
```json
{
  "user_id": "${USER_ID}",
  "account": "${ACCOUNT}"
}
```

**Config:**
```yaml
executions:
  - vars:
      - USER_ID: "12345"
      - ACCOUNT: "acc-A"

probes:
  - body: !include ../includes/template.json
    # Sends: {"user_id": "12345", "account": "acc-A"}
```

### Examples

**JSON Body:**
```yaml
- name: "Create User"
  type: rest
  endpoint: "https://api.example.com/users"
  method: POST
  headers:
    Content-Type: "application/json"
  body: !include ../includes/user-create.json
```

**GraphQL Query:**
```yaml
- name: "Get Repository"
  type: graphql
  endpoint: "https://api.github.com/graphql"
  query: !include ../includes/repo-query.graphql
```

**SOAP Envelope:**
```yaml
- name: "SOAP Request"
  type: rest
  method: POST
  headers:
    Content-Type: "text/xml"
  body: !include ../includes/soap-envelope.xml
```

See [Include Directive Guide](INCLUDE_DIRECTIVE.md) for complete documentation.

---

## Variable Substitution

Variables are substituted using `${VAR_NAME}` syntax.

### Syntax

```yaml
"${VAR_NAME}"           # Simple substitution
"prefix-${VAR}-suffix"  # Within strings
```

### Variable Sources

1. **Execution vars** (highest priority)
2. **Environment variables**
3. **Output variables** (captured from previous probes)

### Where Variables Work

✅ **Request fields:**
- `endpoint`
- `headers` (keys and values)
- `body` (all nested values)
- `query`
- `variables`

✅ **Validation values:**
- `equals` values
- `matches` patterns
- `contains` values
- `range` bounds
- All validator values

❌ **Where variables DON'T work:**
- Validation paths/keys (e.g., can't use `${FIELD}: value`)
- Probe names
- Validator names

### Examples

**In Endpoint:**
```yaml
endpoint: "${BASE_URL}/users/${USER_ID}"
```

**In Headers:**
```yaml
headers:
  Authorization: "Bearer ${TOKEN}"
  X-Client-ID: "${CLIENT_ID}"
```

**In Body:**
```yaml
body:
  user_id: "${USER_ID}"
  account: "${ACCOUNT}"
  metadata:
    region: "${REGION}"
```

**In Validation:**
```yaml
validation:
  body:
    equals:
      user_id: "${USER_ID}"      # Variable in validation value
      region: "${REGION}"
    matches:
      email: "^${USER_ID}@.*"    # Variable in regex pattern
```

**In GraphQL Variables:**
```yaml
variables:
  owner: "${REPO_OWNER}"
  name: "${REPO_NAME}"
```

---

## Complete Examples

### Example 1: Multi-Context with Validation

```yaml
executions:
  - name: "Production"
    vars:
      - ACCOUNT: "123456"
      - API_KEY: "${PROD_API_KEY}"
      - REGION: "us-east-1"
  
  - name: "Staging"
    vars:
      - ACCOUNT: "999999"
      - API_KEY: "${STAGING_API_KEY}"
      - REGION: "us-west-2"

probes:
  - name: "Get Account Info"
    type: rest
    endpoint: "https://api.example.com/accounts/${ACCOUNT}"
    headers:
      X-API-Key: "${API_KEY}"
      X-Region: "${REGION}"
    validation:
      status: 200
      body:
        equals:
          account_id: "${ACCOUNT}"       # Variable substitution
          region: "${REGION}"
        type:
          account_id: string
          balance: number
```

### Example 2: Parallel Groups with Include

```yaml
probes:
  - name: "Login"
    type: rest
    endpoint: "${BASE_URL}/auth"
    method: POST
    headers:
      Content-Type: "application/json"
    body: !include ../includes/login.json
    output:
      TOKEN: "body.access_token"
  
  # Parallel group - all run simultaneously
  - group:
      probes:
        - name: "Get User Profile"
          type: rest
          endpoint: "${BASE_URL}/profile"
          headers:
            Authorization: "Bearer ${TOKEN}"
        
        - name: "Get User Settings"
          type: rest
          endpoint: "${BASE_URL}/settings"
          headers:
            Authorization: "Bearer ${TOKEN}"
        
        - name: "Get User Notifications"
          type: rest
          endpoint: "${BASE_URL}/notifications"
          headers:
            Authorization: "Bearer ${TOKEN}"
```

### Example 3: GraphQL with Variables

```yaml
probes:
  - name: "Search Repositories"
    type: graphql
    endpoint: "https://api.github.com/graphql"
    headers:
      Authorization: "Bearer ${GITHUB_TOKEN}"
    query: |
      query SearchRepos($query: String!) {
        search(query: $query, type: REPOSITORY, first: 5) {
          nodes {
            ... on Repository {
              name
              stargazerCount
            }
          }
        }
      }
    variables:
      query: "language:${LANGUAGE} stars:>1000"
    validation:
      status: 200
      body:
        present:
          - "data.search.nodes"
        type:
          data.search.nodes: array
        absent:
          - "errors"
```

---

## Version History

- **v2.0.0** (2025-01-26)
  - Added executions block
  - Added variable substitution in validation
  - Added parallel groups
  - Added XML/SOAP support
  - Added !include directive
  - Enhanced variable resolution

- **v1.0.0** (2025-01-25)
  - Initial release
