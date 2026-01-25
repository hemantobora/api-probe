# API-Probe YAML Schema Specification

**Version:** 1.0.0  
**Last Updated:** 2025-01-26

## Overview

This document provides the complete YAML schema specification for api-probe configuration files. The schema defines how to declare API tests, validations, and execution flows for post-deployment functional testing.

---

## Table of Contents

- [Root Structure](#root-structure)
- [Test Definition](#test-definition)
- [Group Definition](#group-definition)
- [REST API Tests](#rest-api-tests)
- [GraphQL API Tests](#graphql-api-tests)
- [Validation Specification](#validation-specification)
- [Output Variables](#output-variables)
- [Include Directive](#include-directive)
- [Variable Substitution](#variable-substitution)
- [Design Principles](#design-principles)
- [Complete Examples](#complete-examples)

---

## Root Structure

The root of every api-probe configuration file contains a single `tests` array:

```yaml
tests:
  - <test-or-group>
  - <test-or-group>
  # ...
```

### Schema

```yaml
tests:                    # REQUIRED: Array of Test or Group objects
  - name: string          # Test definition
    # ...
  - group:                # Group definition
      tests: []
    # ...
```

### Rules

- Root element MUST be `tests` array
- Array contains Test objects or Group objects
- Tests execute in YAML sequence order (top to bottom)
- Groups execute tests in parallel
- Empty `tests` array is valid (no-op)

---

## Test Definition

A Test represents a single API call with optional validation and output capture.

### Schema

```yaml
- name: string                           # REQUIRED: Unique test name
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
- **Description:** Human-readable test name, must be unique across all tests
- **Example:** `"OAuth Authentication"`, `"Get User Profile"`
- **Rules:**
  - Must be unique within configuration
  - Used in failure reporting
  - No special restrictions on characters

#### `type` (required)
- **Type:** Enum (`rest`, `graphql`)
- **Description:** Specifies the API protocol
- **Default:** None (must be specified)
- **Rules:**
  - `rest`: Standard REST API with HTTP methods
  - `graphql`: GraphQL endpoint (always POST, auto-sets Content-Type)

#### `endpoint` (required)
- **Type:** String (URL)
- **Description:** Target API endpoint with variable substitution support
- **Examples:**
  ```yaml
  endpoint: "https://api.example.com/v1/users"
  endpoint: "https://api.example.com/v1/accounts/${ACCOUNT_ID}"
  endpoint: "${BASE_URL}/graphql"
  ```
- **Rules:**
  - Must be valid URL format (with or without protocol, defaults to https)
  - Supports `${VARIABLE}` substitution
  - Protocol is optional: `api.example.com` → `https://api.example.com`

#### `method` (REST only, optional)
- **Type:** Enum (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`)
- **Default:** `GET`
- **Description:** HTTP method for REST requests
- **Example:**
  ```yaml
  method: POST
  ```
- **Rules:**
  - Ignored for GraphQL tests (always POST)
  - Case-insensitive

#### `headers` (optional)
- **Type:** Object (key-value pairs)
- **Description:** HTTP headers to include in request
- **Examples:**
  ```yaml
  headers:
    Authorization: "Bearer ${ACCESS_TOKEN}"
    X-Client-ID: "${CLIENT_ID}"
    Accept: "application/json"
  ```
- **Rules:**
  - Keys: Header names (case-insensitive per HTTP spec)
  - Values: String with `${VAR}` substitution support
  - **CRITICAL (REST):** If `body` is present, `Content-Type` header is MANDATORY
  - **GraphQL:** Content-Type auto-set to `application/json` (can override)

#### `body` (REST only, optional)
- **Type:** Object, Array, String, or `!include` directive
- **Description:** Request body payload
- **Examples:**
  ```yaml
  # JSON object
  body:
    username: "${USERNAME}"
    password: "${PASSWORD}"
  
  # JSON array
  body:
    - id: 1
    - id: 2
  
  # String (for text/xml)
  body: "<user><name>${NAME}</name></user>"
  
  # Include from file
  body: !include bodies/create-order.yaml
  ```
- **Rules:**
  - **MANDATORY:** If body is present, headers MUST include `Content-Type`
  - Serialization based on Content-Type:
    - `application/json` → JSON.dumps()
    - `application/x-www-form-urlencoded` → urlencode()
    - `application/xml`, `text/xml` → XML serialization
  - Supports variable substitution in values
  - Supports `!include` directive

#### `query` (GraphQL only, required)
- **Type:** String or `!include` directive
- **Description:** GraphQL query or mutation
- **Examples:**
  ```yaml
  # Inline query
  query: |
    query GetUser($id: ID!) {
      user(id: $id) {
        name
        email
      }
    }
  
  # Include from file
  query: !include queries/get-user.graphql
  ```
- **Rules:**
  - Required when `type: graphql`
  - Can be inline string or `!include` directive
  - Supports variable substitution in string values

#### `variables` (GraphQL only, optional)
- **Type:** Object
- **Description:** GraphQL query variables
- **Example:**
  ```yaml
  variables:
    id: "${USER_ID}"
    limit: 10
    filter:
      status: "active"
  ```
- **Rules:**
  - Keys: GraphQL variable names (without `$` prefix)
  - Values: Any JSON-serializable value with `${VAR}` substitution
  - Sent as part of GraphQL request body: `{"query": "...", "variables": {...}}`

#### `validation` (optional)
- **Type:** Object (validation specification)
- **Description:** Response validation rules
- **See:** [Validation Specification](#validation-specification)

#### `output` (optional)
- **Type:** Object (key-value pairs)
- **Description:** Extract values from response to variables
- **See:** [Output Variables](#output-variables)

### Validation Rules

1. **Uniqueness:** Test `name` must be unique across all tests
2. **Content-Type:** If REST test has `body`, headers MUST contain `Content-Type`
3. **GraphQL Query:** If `type: graphql`, `query` is required
4. **Method:** GraphQL tests ignore `method` (always POST)

---

## Group Definition

A Group executes multiple tests in parallel.

### Schema

```yaml
- group:
    tests:
      - name: string
        # ... test definition
      - name: string
        # ... test definition
```

### Rules

- `group` keyword has NO attributes (only `tests` array)
- All tests within group execute in parallel
- Group waits for ALL tests to complete before continuing
- Tests in different groups execute sequentially (YAML order)
- Groups can NOT be nested

### Example

```yaml
tests:
  # Sequential test
  - name: "Get Auth Token"
    type: rest
    endpoint: "https://api.example.com/auth"
    # ...
  
  # Parallel group (all 3 run simultaneously)
  - group:
      tests:
        - name: "Get User Profile"
          # ...
        - name: "Get User Preferences"
          # ...
        - name: "Get User Activity"
          # ...
  
  # Sequential test (waits for group to complete)
  - name: "Update User Settings"
    # ...
```

---

## REST API Tests

### Minimal Example

```yaml
- name: "Health Check"
  type: rest
  endpoint: "https://api.example.com/health"
```

### Complete Example

```yaml
- name: "Create Order"
  type: rest
  endpoint: "https://api.example.com/v1/orders"
  method: POST
  headers:
    Content-Type: "application/json"
    Authorization: "Bearer ${ACCESS_TOKEN}"
    X-Idempotency-Key: "${ORDER_ID}"
  body:
    customerId: "${CUSTOMER_ID}"
    items:
      - productId: "PROD-123"
        quantity: 2
      - productId: "PROD-456"
        quantity: 1
    shippingAddress:
      street: "123 Main St"
      city: "San Francisco"
      state: "CA"
      zip: "94102"
  validation:
    status: 201
    headers:
      present:
        - "Location"
        - "X-Request-ID"
      equals:
        Content-Type: "application/json"
    body:
      present:
        - "orderId"
        - "status"
        - "createdAt"
      equals:
        status: "pending"
      matches:
        orderId: "^ORD-[0-9]{10}$"
  output:
    ORDER_ID: "body.orderId"
    REQUEST_ID: "headers.X-Request-ID"
```

### Content-Type Handling

The `Content-Type` header determines how the request body is serialized:

| Content-Type | Serialization | Example |
|--------------|---------------|---------|
| `application/json` | JSON.dumps() | `{"key": "value"}` |
| `application/x-www-form-urlencoded` | urlencode() | `key=value&foo=bar` |
| `application/xml`, `text/xml` | XML serialization | `<root><key>value</key></root>` |

**CRITICAL RULE:** If `body` is present, `Content-Type` header is **MANDATORY**. Tests will fail immediately if missing.

---

## GraphQL API Tests

### Minimal Example

```yaml
- name: "Get User"
  type: graphql
  endpoint: "https://api.example.com/graphql"
  query: |
    query {
      user(id: "123") {
        name
        email
      }
    }
```

### Complete Example

```yaml
- name: "Create User Mutation"
  type: graphql
  endpoint: "${GRAPHQL_ENDPOINT}"
  headers:
    Authorization: "Bearer ${ADMIN_TOKEN}"
    X-Request-ID: "${REQUEST_ID}"
  query: |
    mutation CreateUser($input: CreateUserInput!) {
      createUser(input: $input) {
        user {
          id
          name
          email
          createdAt
        }
        errors {
          field
          message
        }
      }
    }
  variables:
    input:
      name: "John Doe"
      email: "john@example.com"
      role: "admin"
  validation:
    status: 200
    body:
      present:
        - "data.createUser.user.id"
        - "data.createUser.user.email"
      absent:
        - "data.createUser.errors"
      equals:
        data.createUser.user.name: "John Doe"
      matches:
        data.createUser.user.id: "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
  output:
    USER_ID: "body.data.createUser.user.id"
```

### GraphQL-Specific Rules

1. **Content-Type:** Auto-set to `application/json` (can be overridden in headers)
2. **Method:** Always POST (cannot be changed)
3. **Request Format:**
   ```json
   {
     "query": "query GetUser($id: ID!) { ... }",
     "variables": { "id": "123" }
   }
   ```
4. **Response Format:** Standard GraphQL response:
   ```json
   {
     "data": { ... },
     "errors": [ ... ]  // optional
   }
   ```

---

## Validation Specification

Validation rules assert expected response characteristics. All validations are optional.

### Schema

```yaml
validation:
  status: integer                 # Expected status code
  headers:                        # Header validations
    present: [string]             # Headers that must exist
    absent: [string]              # Headers that must NOT exist
    equals:                       # Headers with exact values
      Header-Name: string
    matches:                      # Headers matching regex
      Header-Name: regex
    contains:                     # Headers containing substring
      Header-Name: string
  body:                           # Body validations
    present: [path]               # Fields that must exist
    absent: [path]                # Fields that must NOT exist
    equals:                       # Fields with exact values
      path: value
    matches:                      # Fields matching regex
      path: regex
    type:                         # Fields with specific types
      path: type
    contains:                     # Fields containing value
      path: value
    range:                        # Numeric fields within range
      path: [min, max]
```

### Status Code Validation

```yaml
validation:
  status: 200
```

- **Type:** Integer
- **Description:** Expected HTTP status code
- **Rules:**
  - Exact match required
  - Validation fails if actual status differs

### Header Validations

#### `present`

Assert headers exist (value can be anything, including empty):

```yaml
validation:
  headers:
    present:
      - "Authorization"
      - "X-Request-ID"
      - "ETag"
```

- **Type:** Array of strings (header names)
- **Rules:**
  - Header must exist in response
  - Value is ignored (can be empty string)
  - Header names are case-insensitive

#### `absent`

Assert headers do NOT exist:

```yaml
validation:
  headers:
    absent:
      - "X-Internal-Token"
      - "X-Debug-Info"
```

- **Type:** Array of strings (header names)
- **Rules:**
  - Header must not be present
  - Useful for security validation

#### `equals`

Assert exact header values:

```yaml
validation:
  headers:
    equals:
      Content-Type: "application/json"
      X-API-Version: "2.0"
```

- **Type:** Object (header-name: expected-value)
- **Rules:**
  - Exact string match (case-sensitive for values)
  - Header names case-insensitive
  - Supports variable substitution: `Authorization: "Bearer ${EXPECTED_TOKEN}"`

#### `matches`

Assert header values match regex:

```yaml
validation:
  headers:
    matches:
      X-Request-ID: "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
      ETag: "^\"[a-f0-9]{32}\"$"
```

- **Type:** Object (header-name: regex-pattern)
- **Rules:**
  - Full regex support (Python `re` module)
  - Backslashes must be escaped in YAML: `\\d` → `\\\\d`
  - Partial matches allowed (use `^` and `$` anchors for exact)

#### `contains`

Assert header value contains substring:

```yaml
validation:
  headers:
    contains:
      Content-Type: "json"
      Set-Cookie: "session="
```

- **Type:** Object (header-name: substring)
- **Rules:**
  - Case-sensitive substring match
  - Useful for partial value validation

### Body Validations

Body validations use **path expressions** to navigate response structure:
- **JSON responses:** JSONPath
- **XML responses:** XPath

Path expressions are auto-detected based on response `Content-Type` header.

#### `present`

Assert fields exist in response body:

```yaml
validation:
  body:
    present:
      - "id"
      - "user.email"
      - "items[0].name"
      - "data.createUser.user.id"  # GraphQL
```

- **Type:** Array of path expressions
- **Rules:**
  - Field must exist (value can be null)
  - JSONPath for JSON: `data.user.email`, `items[0].id`
  - XPath for XML: `//user/email`, `/root/items/item[1]/id`

#### `absent`

Assert fields do NOT exist:

```yaml
validation:
  body:
    absent:
      - "password"
      - "internalId"
      - "data.errors"  # GraphQL errors
```

- **Type:** Array of path expressions
- **Rules:**
  - Field must not exist at all
  - `null` values count as present
  - Useful for security (e.g., password not in response)

#### `equals`

Assert exact field values:

```yaml
validation:
  body:
    equals:
      status: "active"
      user.role: "admin"
      count: 42
      isPremium: true
      data.user.verified: true  # GraphQL
```

- **Type:** Object (path: expected-value)
- **Rules:**
  - Type-strict equality
  - String: `"active"` ≠ `"Active"`
  - Number: `42` ≠ `"42"`
  - Boolean: `true` ≠ `"true"`
  - Supports variable substitution: `status: "${EXPECTED_STATUS}"`

#### `matches`

Assert field values match regex patterns:

```yaml
validation:
  body:
    matches:
      email: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
      orderId: "^ORD-[0-9]{10}$"
      phone: "^\\+1[0-9]{10}$"
```

- **Type:** Object (path: regex-pattern)
- **Rules:**
  - Only works on string fields
  - Full regex support
  - Escape backslashes: `\d` → `\\d` in YAML
  - Partial matches allowed unless anchored

#### `type`

Assert field types:

```yaml
validation:
  body:
    type:
      age: integer
      balance: number
      name: string
      isPremium: boolean
      tags: array
      metadata: object
      optionalField: null
```

- **Type:** Object (path: type-name)
- **Supported Types:**
  - `integer`: Whole numbers (1, 42, -5)
  - `number`: Integers or floats (1, 3.14, -2.5)
  - `string`: Text values
  - `boolean`: true or false
  - `array`: Lists/arrays
  - `object`: Objects/dictionaries
  - `null`: Explicit null value
- **Rules:**
  - Type mismatch = validation failure
  - `integer` is stricter than `number`

#### `contains`

Assert substring/element presence:

```yaml
validation:
  body:
    contains:
      description: "premium features"  # substring in string
      tags: "verified"                  # element in array
      message: "success"
```

- **Type:** Object (path: value)
- **Rules:**
  - **For strings:** Substring match (case-sensitive)
  - **For arrays:** Element match (exact equality)
  - Does not work on objects or numbers

#### `range`

Assert numeric values within range:

```yaml
validation:
  body:
    range:
      age: [18, 65]         # 18 <= age <= 65
      balance: [0, null]    # balance >= 0 (no upper limit)
      score: [null, 100]    # score <= 100 (no lower limit)
      temperature: [-273.15, 1000]
```

- **Type:** Object (path: [min, max])
- **Rules:**
  - Inclusive range: `min <= value <= max`
  - `null` = no limit on that bound
  - Only works on numeric fields (integer or number)
  - Non-numeric fields cause validation failure

### Validation Behavior

- **All validations execute:** Failures don't stop subsequent validations
- **All failures reported:** Comprehensive error reporting
- **Validation order:** Not guaranteed (don't rely on order)
- **Path extraction:** Values extracted before validation applied

---

## Output Variables

Output variables extract values from responses and make them available to subsequent tests.

### Schema

```yaml
output:
  VARIABLE_NAME: path-expression
```

### Path Prefixes

All output paths MUST use one of these prefixes:

| Prefix | Description | Example |
|--------|-------------|---------|
| `body.` | Extract from response body | `body.access_token` |
| `headers.` | Extract from response header | `headers.X-Request-ID` |
| `status` | Extract status code | `status` |

### Examples

```yaml
output:
  ACCESS_TOKEN: "body.access_token"
  USER_ID: "body.user.id"
  REQUEST_ID: "headers.X-Request-ID"
  ORDER_ID: "body.data.createOrder.orderId"  # GraphQL
  STATUS_CODE: "status"
```

### Usage in Subsequent Tests

Variables become available for substitution:

```yaml
tests:
  - name: "Login"
    type: rest
    endpoint: "https://api.example.com/auth"
    body:
      username: "${USERNAME}"
      password: "${PASSWORD}"
    output:
      ACCESS_TOKEN: "body.access_token"
  
  - name: "Get Profile"
    type: rest
    endpoint: "https://api.example.com/profile"
    headers:
      Authorization: "Bearer ${ACCESS_TOKEN}"  # Uses captured variable
```

### Rules

1. **Prefix Required:** Must use `body.`, `headers.`, or `status`
2. **Path Expression:** After prefix, use JSONPath or XPath
3. **Variable Scope:** Available to all subsequent tests in same execution context
4. **Namespace:** Single namespace shared with environment variables
5. **Multi-Value Isolation:** Each parallel run has isolated variable namespace
6. **Extraction Failure:** Non-existent paths result in test failure

---

## Include Directive

The `!include` directive loads content from external files, providing flexibility and modularity in configuration management.

### Syntax

```yaml
fieldName: !include path/to/file.ext
```

### Supported Locations

The `!include` directive works anywhere a complex object or string value would go. This provides maximum flexibility for organizing your configurations.

**Top-level fields:**
- `body`: REST request bodies
- `query`: GraphQL queries
- `variables`: GraphQL variables
- `validation`: Complete validation specification

**Within validation blocks:**
- `validation.headers`: Header validation rules
- `validation.body`: Body validation rules
- Individual validation keywords (for even finer granularity)

### Usage Patterns

#### Pattern 1: Include Entire Validation Block

Most common use case - reuse complete validation specifications:

```yaml
# main.yaml
tests:
  - name: "Get User"
    type: rest
    endpoint: "https://api.example.com/users/${USER_ID}"
    validation: !include validations/user-response.yaml

# validations/user-response.yaml
status: 200
headers:
  present:
    - "Content-Type"
    - "X-Request-ID"
body:
  present:
    - "id"
    - "email"
    - "createdAt"
  type:
    id: string
    email: string
    verified: boolean
```

#### Pattern 2: Include Partial Validation Sections

Mix inline and included validations for flexibility:

```yaml
# Test-specific status, reusable body validations
validation:
  status: 200
  headers:
    present: ["X-Request-ID"]
  body: !include validations/user-body-checks.yaml

# validations/user-body-checks.yaml
present:
  - "id"
  - "email"
  - "profile"
type:
  id: string
  email: string
  verified: boolean
equals:
  status: "active"
```

#### Pattern 3: Multiple Includes in Single Test

Compose validations from multiple reusable files:

```yaml
validation:
  status: 201
  headers: !include validations/common-response-headers.yaml
  body: !include validations/created-resource-body.yaml

# validations/common-response-headers.yaml
present:
  - "X-Request-ID"
  - "X-RateLimit-Remaining"
equals:
  Content-Type: "application/json"

# validations/created-resource-body.yaml
present:
  - "id"
  - "createdAt"
matches:
  id: "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
type:
  createdAt: string
```

#### Pattern 4: Include Request Bodies

Keep request payloads in separate files:

```yaml
# main.yaml
- name: "Create Order"
  type: rest
  endpoint: "https://api.example.com/orders"
  method: POST
  headers:
    Content-Type: "application/json"
  body: !include bodies/order-payload.yaml

# bodies/order-payload.yaml
customerId: "${CUSTOMER_ID}"
items:
  - productId: "PROD-123"
    quantity: 2
shipping:
  method: "express"
```

#### Pattern 5: Include GraphQL Queries and Variables

```yaml
# main.yaml
- name: "Create User"
  type: graphql
  endpoint: "${GRAPHQL_ENDPOINT}"
  query: !include queries/create-user.graphql
  variables: !include variables/new-user-vars.yaml
  validation: !include validations/graphql-user-created.yaml
```

### Path Resolution

- **Relative paths:** Resolved from config file location
  ```yaml
  body: !include ../bodies/create-user.yaml
  validation: !include ./validations/common.yaml
  ```
- **Absolute paths:** Used as-is
  ```yaml
  query: !include /app/queries/get-products.graphql
  ```

### File Types

#### YAML Files (`.yaml`, `.yml`)

```yaml
# bodies/create-order.yaml
customerId: "${CUSTOMER_ID}"
items:
  - productId: "PROD-123"
    quantity: 2

# main.yaml
tests:
  - name: "Create Order"
    type: rest
    endpoint: "https://api.example.com/orders"
    method: POST
    headers:
      Content-Type: "application/json"
    body: !include bodies/create-order.yaml
```

#### GraphQL Files (`.graphql`, `.gql`)

```graphql
# queries/get-user.graphql
query GetUser($id: ID!) {
  user(id: $id) {
    id
    name
    email
    profile {
      avatar
      bio
    }
  }
}
```

```yaml
# main.yaml
tests:
  - name: "Get User"
    type: graphql
    endpoint: "https://api.example.com/graphql"
    query: !include queries/get-user.graphql
    variables:
      id: "${USER_ID}"
```

#### JSON Files (`.json`)

```json
// bodies/search-params.json
{
  "query": "${SEARCH_TERM}",
  "filters": {
    "category": "electronics",
    "priceRange": [100, 500]
  },
  "limit": 20
}
```

```yaml
body: !include bodies/search-params.json
```

### Rules

1. **Relative to Config:** Relative paths resolve from config file directory
2. **File Must Exist:** Missing files cause immediate failure
3. **No Remote URLs:** Only local filesystem paths supported (v1.0)
4. **Variable Substitution:** Works in included content
5. **Nested Includes:** NOT supported (included files can't include others)
6. **Circular Detection:** Not applicable (no nested includes)

---

## Variable Substitution

Variables can be substituted anywhere in the configuration using `${VARIABLE}` syntax.

### Syntax

```yaml
"${VARIABLE_NAME}"
```

### Variable Sources

1. **Environment Variables:** Set before execution
   ```bash
   export CLIENT_ID="abc123"
   export BASE_URL="https://api.example.com"
   ```

2. **Output Variables:** Captured from previous test responses
   ```yaml
   output:
     ACCESS_TOKEN: "body.access_token"
   ```

3. **Multi-Value Variables:** Comma-separated for parallel execution
   ```bash
   export CLIENT_ID="client1,client2,client3"
   ```

### Usage Examples

```yaml
tests:
  - name: "Authenticate"
    type: rest
    endpoint: "${BASE_URL}/auth"
    headers:
      X-Client-ID: "${CLIENT_ID}"
    body:
      username: "${USERNAME}"
      password: "${PASSWORD}"
    output:
      ACCESS_TOKEN: "body.access_token"
  
  - name: "Get Account"
    type: rest
    endpoint: "${BASE_URL}/accounts/${ACCOUNT_ID}"
    headers:
      Authorization: "Bearer ${ACCESS_TOKEN}"
```

### Multi-Value Variable Expansion

Comma-separated environment variables create parallel test runs:

```bash
export CLIENT_ID="client1,client2,client3"
export ACCOUNT="acc1,acc2"
export BASE_URL="https://api.example.com"
```

This creates **3 parallel execution contexts:**

| Run | CLIENT_ID | ACCOUNT | BASE_URL |
|-----|-----------|---------|----------|
| 1 | client1 | acc1 | https://api.example.com |
| 2 | client2 | acc2 | https://api.example.com |
| 3 | client3 | acc2 | https://api.example.com |

**Position-Based Pairing:**
- Index 0: `client1`, `acc1`
- Index 1: `client2`, `acc2`
- Index 2: `client3`, `acc2` (last value repeats)

**Key Points:**
- Single-value variables (e.g., `BASE_URL`) are shared across all runs
- Each run has isolated variable namespace
- Output variables scoped to run (no cross-contamination)
- Number of runs = max value count across all multi-value variables

### Rules

1. **Undefined Variables:** Cause immediate test failure
2. **Missing Values:** Tests requiring undefined variables are skipped
3. **Variable Naming:** Case-sensitive, alphanumeric + underscore
4. **Nested Substitution:** NOT supported: `${VAR_${OTHER}}`
5. **Escaping:** No escape mechanism (use literal `${` is not possible in v1.0)

---

## Design Principles

### 1. Explicit Over Implicit

- **Content-Type Required:** If REST body present, Content-Type is mandatory
- **Path Prefixes Required:** Output paths must use `body.`, `headers.`, or `status`
- **Type Required:** Test `type` must be specified (`rest` or `graphql`)

### 2. Fail Fast on Configuration Errors

- Invalid YAML syntax → immediate failure
- Missing required fields → immediate failure
- Invalid path expressions → immediate failure
- Missing Content-Type with body → immediate failure

### 3. Fail Gracefully on Execution Errors

- Validation failures → collect all, continue execution
- HTTP errors → report, continue to next test
- Missing variables → skip test, continue execution

### 4. Silent Success, Verbose Failure

- All tests pass → exit 0, no output
- Any test fails → detailed failure report, exit 1

### 5. Security First

- Never log environment variable values
- Never expose credentials in error messages
- Sanitize all output

### 6. Declarative Configuration

- Execution order determined by YAML sequence
- No conditional logic in config
- No loops or control flow
- Keep configs simple and readable

---

## Complete Examples

### REST API Example

```yaml
tests:
  # Sequential: Get OAuth token
  - name: "OAuth Authentication"
    type: rest
    endpoint: "https://api.example.com/oauth/token"
    method: POST
    headers:
      Content-Type: "application/x-www-form-urlencoded"
    body:
      grant_type: "client_credentials"
      client_id: "${CLIENT_ID}"
      client_secret: "${CLIENT_SECRET}"
    validation:
      status: 200
      body:
        present:
          - "access_token"
          - "expires_in"
        type:
          access_token: string
          expires_in: integer
        range:
          expires_in: [3600, null]
    output:
      ACCESS_TOKEN: "body.access_token"
  
  # Parallel group: Fetch multiple resources
  - group:
      tests:
        - name: "Get Account Details"
          type: rest
          endpoint: "https://api.example.com/v1/accounts/${ACCOUNT_ID}"
          headers:
            Authorization: "Bearer ${ACCESS_TOKEN}"
          validation:
            status: 200
            body:
              present:
                - "accountId"
                - "status"
                - "balance"
              equals:
                accountId: "${ACCOUNT_ID}"
                status: "active"
              type:
                balance: number
        
        - name: "Get Transactions"
          type: rest
          endpoint: "https://api.example.com/v1/accounts/${ACCOUNT_ID}/transactions"
          headers:
            Authorization: "Bearer ${ACCESS_TOKEN}"
          validation:
            status: 200
            body:
              type:
                items: array
              present:
                - "items"
                - "total"
        
        - name: "Get Account Settings"
          type: rest
          endpoint: "https://api.example.com/v1/accounts/${ACCOUNT_ID}/settings"
          headers:
            Authorization: "Bearer ${ACCESS_TOKEN}"
          validation:
            status: 200
  
  # Sequential: Create transaction
  - name: "Create Transaction"
    type: rest
    endpoint: "https://api.example.com/v1/transactions"
    method: POST
    headers:
      Content-Type: "application/json"
      Authorization: "Bearer ${ACCESS_TOKEN}"
    body: !include bodies/transaction.yaml
    validation:
      status: 201
      headers:
        present:
          - "Location"
      body:
        present:
          - "transactionId"
        matches:
          transactionId: "^TXN-[0-9]{12}$"
    output:
      TRANSACTION_ID: "body.transactionId"
```

### GraphQL Example

```yaml
tests:
  - name: "Admin Login"
    type: graphql
    endpoint: "${GRAPHQL_ENDPOINT}"
    query: |
      mutation Login($email: String!, $password: String!) {
        login(email: $email, password: $password) {
          token
          user {
            id
            role
          }
        }
      }
    variables:
      email: "${ADMIN_EMAIL}"
      password: "${ADMIN_PASSWORD}"
    validation:
      status: 200
      body:
        present:
          - "data.login.token"
          - "data.login.user.id"
        equals:
          data.login.user.role: "admin"
        absent:
          - "errors"
    output:
      ADMIN_TOKEN: "body.data.login.token"
      ADMIN_ID: "body.data.login.user.id"
  
  - name: "Create User"
    type: graphql
    endpoint: "${GRAPHQL_ENDPOINT}"
    headers:
      Authorization: "Bearer ${ADMIN_TOKEN}"
    query: !include mutations/create-user.graphql
    variables: !include variables/new-user.yaml
    validation:
      status: 200
      body:
        present:
          - "data.createUser.user"
        absent:
          - "data.createUser.errors"
          - "errors"
    output:
      NEW_USER_ID: "body.data.createUser.user.id"
  
  - name: "Query User"
    type: graphql
    endpoint: "${GRAPHQL_ENDPOINT}"
    headers:
      Authorization: "Bearer ${ADMIN_TOKEN}"
    query: !include queries/get-user.graphql
    variables:
      id: "${NEW_USER_ID}"
    validation:
      status: 200
      body:
        equals:
          data.user.id: "${NEW_USER_ID}"
        type:
          data.user.createdAt: string
```

### SOAP/XML Example

```yaml
tests:
  - name: "SOAP Request"
    type: rest
    endpoint: "https://api.example.com/soap"
    method: POST
    headers:
      Content-Type: "text/xml; charset=utf-8"
      SOAPAction: "http://example.com/GetUserInfo"
    body: |
      <?xml version="1.0"?>
      <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
        <soap:Header/>
        <soap:Body>
          <GetUserInfo xmlns="http://example.com/">
            <UserId>${USER_ID}</UserId>
          </GetUserInfo>
        </soap:Body>
      </soap:Envelope>
    validation:
      status: 200
      headers:
        contains:
          Content-Type: "xml"
      body:
        present:
          - "//soap:Envelope/soap:Body/GetUserInfoResponse/User/Name"
          - "//soap:Envelope/soap:Body/GetUserInfoResponse/User/Email"
```

---

## Validation Keywords Reference

| Keyword | Scope | Type | Description |
|---------|-------|------|-------------|
| `status` | Root | integer | Expected HTTP status code |
| `present` | headers, body | array | Fields that must exist |
| `absent` | headers, body | array | Fields that must NOT exist |
| `equals` | headers, body | object | Fields with exact values |
| `matches` | headers, body | object | Fields matching regex patterns |
| `contains` | headers, body | object | Fields containing substring/element |
| `type` | body | object | Fields with specific types |
| `range` | body | object | Numeric fields within range |

---

## Path Expression Syntax

### JSONPath (for JSON responses)

```yaml
# Simple field
"user"

# Nested field
"user.email"

# Array index
"items[0]"

# All array elements
"items[*]"

# Nested in array
"items[0].name"

# GraphQL data structure
"data.user.profile.avatar"
```

### XPath (for XML responses)

```yaml
# Absolute path
"/root/user/email"

# Relative path (anywhere)
"//user/email"

# Array-like (first element)
"/root/items/item[1]/name"

# Attribute
"//user/@id"

# Namespaced (SOAP)
"//soap:Envelope/soap:Body/Response/User/Email"
```

---

## Schema Validation

### Required Fields

- Root: `tests` (array)
- Test: `name`, `type`, `endpoint`
- GraphQL: `query` (when type=graphql)

### Validation Rules

1. Test names must be unique
2. REST with body requires Content-Type header
3. Output paths must use valid prefixes
4. Include paths must point to existing files
5. Variable substitution must reference defined variables

---

## Best Practices

1. **Use meaningful test names:** Aid in debugging failures
2. **Group related tests:** Parallelize independent operations
3. **Capture essential variables:** Minimize dependencies
4. **Validate security:** Use `absent` for sensitive fields
5. **Use includes:** Keep configs DRY and maintainable
6. **Type checking:** Use `type` validation for robustness
7. **Range validation:** Prevent invalid numeric values
8. **Regex validation:** Enforce format constraints

---

**End of Schema Specification**
