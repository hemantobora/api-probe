# Include Directive (!include) Guide

## Overview

The `!include` directive allows you to load content from external files into your probe configurations. This is useful for:
- Keeping large request bodies separate
- Reusing common payloads across probes
- Better organization and maintainability
- Version controlling payloads separately from probes

## Where You Can Use !include

The `!include` directive works **anywhere** in your YAML config:

### ✅ Request Bodies (REST)
```yaml
body: !include includes/payload.json
```

### ✅ GraphQL Queries
```yaml
query: !include includes/query.graphql
```

### ✅ GraphQL Variables (entire object)
```yaml
variables: !include includes/variables.json
```

### ✅ GraphQL Variables (nested)
```yaml
variables:
  input: !include includes/item-input.json
  filters: !include includes/filters.json
```

### ✅ Inside Included YAML Files
```yaml
# config.yaml
body: !include includes/outer.yaml

# includes/outer.yaml — nested !include works in YAML files
key: value
nested: !include inner.yaml
```

> **Note:** Nested `!include` only works inside `.yaml`/`.yml` files, because `!include` is a YAML tag. It does not work inside `.json` or `.xml` files.

### Notes on `!include` scope

`!include` is processed at YAML load time and works anywhere in the config. However, the loaded content must match what that field expects structurally. For example, `body: !include payload.json` works because `body` expects an object — and the JSON file provides one. If the loaded content doesn't match the expected structure, the parser will raise an error at parse time, not at load time.

## Basic Usage

```yaml
probes:
  - name: "Create User"
    type: rest
    endpoint: "https://api.example.com/users"
    method: POST
    headers:
      Content-Type: "application/json"
    body: !include includes/user.json
    validation:
      status: 201
```

## Supported File Types

### JSON Files (.json)
Parsed as JSON and inserted as a dictionary/array:

```yaml
body: !include includes/payload.json
```

### YAML Files (.yaml, .yml)
Parsed as YAML and inserted as a structure:

```yaml
body: !include includes/config.yaml
```

### Plain Text Files (.txt, .graphql, .xml, etc.)
Inserted as strings:

```yaml
query: !include includes/graphql-query.graphql
body: !include includes/soap-request.xml
```

## Path Resolution

Paths are resolved **relative to the config file location**:

```
my-project/
├── tests/
│   └── api-tests.yaml          # Config file
└── includes/
    └── user.json                # Include file

# In api-tests.yaml:
body: !include ../includes/user.json
```

## Variable Substitution in Included Files

**Variables ARE substituted** in included files! ✅

### Example:

**File: includes/user-template.json**
```json
{
  "user_id": "${USER_ID}",
  "account": "${ACCOUNT}",
  "region": "${REGION}"
}
```

**Config: test.yaml**
```yaml
executions:
  - name: "User A"
    vars:
      - USER_ID: "12345"
      - ACCOUNT: "account-A"
      - REGION: "us-east-1"

probes:
  - name: "Create User"
    type: rest
    endpoint: "https://api.example.com/users"
    method: POST
    headers:
      Content-Type: "application/json"
    body: !include includes/user-template.json
    validation:
      status: 201
      body:
        equals:
          user_id: "${USER_ID}"  # Will be "12345"
```

**How it works:**
1. `!include` loads the file (with literal `"${USER_ID}"` strings)
2. Executor substitutes variables before sending the request
3. Each execution context gets different values

## Use Cases

### 1. Large Request Payloads

**Before:**
```yaml
probes:
  - name: "Update Profile"
    body:
      user:
        firstName: "John"
        lastName: "Doe"
        email: "john@example.com"
        address:
          street: "123 Main St"
          city: "San Francisco"
          state: "CA"
          zip: "94105"
        # ... 50 more lines
```

**After:**
```yaml
probes:
  - name: "Update Profile"
    body: !include includes/profile-update.json
```

### 2. GraphQL Queries

**File: includes/repository-query.graphql**
```graphql
query GetRepository($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    name
    description
    stargazerCount
    forkCount
  }
}
```

**Config:**
```yaml
probes:
  - name: "Get Repository Info"
    type: graphql
    endpoint: "https://api.github.com/graphql"
    query: !include includes/repository-query.graphql
    variables:
      owner: "torvalds"
      name: "linux"
```

### 3. SOAP Envelopes

**File: includes/soap-get-user.xml**
```xml
<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <GetUser xmlns="http://example.com/userservice">
      <userId>${USER_ID}</userId>
    </GetUser>
  </soap:Body>
</soap:Envelope>
```

**Config:**
```yaml
probes:
  - name: "SOAP Get User"
    type: rest
    endpoint: "https://soap.example.com/userservice"
    method: POST
    headers:
      Content-Type: "text/xml; charset=utf-8"
      SOAPAction: "http://example.com/GetUser"
    body: !include includes/soap-get-user.xml
```

### 4. Reusable Templates with Variables

**File: includes/auth-request.json**
```json
{
  "client_id": "${CLIENT_ID}",
  "client_secret": "${CLIENT_SECRET}",
  "grant_type": "client_credentials",
  "scope": "${SCOPE}"
}
```

**Config:**
```yaml
executions:
  - name: "Production"
    vars:
      - CLIENT_ID: "prod-client"
      - CLIENT_SECRET: "${PROD_SECRET}"
      - SCOPE: "read write"
  
  - name: "Staging"
    vars:
      - CLIENT_ID: "staging-client"
      - CLIENT_SECRET: "${STAGING_SECRET}"
      - SCOPE: "read"

probes:
  - name: "Get Access Token"
    body: !include includes/auth-request.json
    # Different values for each execution!
```

### 5. GraphQL Variables from External Files

**File: includes/item-input.json**
```json
{
  "name": "${ITEM_NAME}",
  "description": "A complex item with many fields",
  "specifications": {
    "weight": 2.5,
    "dimensions": {
      "length": 30,
      "width": 20,
      "height": 10
    }
  },
  "tags": ["tag1", "tag2", "tag3"]
}
```

**Config:**
```yaml
probes:
  - name: "Create Item"
    type: graphql
    endpoint: "https://api.example.com/graphql"
    query: |
      mutation CreateItem($input: ItemInput!) {
        createItem(input: $input) {
          id
          name
        }
      }
    variables:
      input: !include includes/item-input.json
      # Variables ARE substituted in included files!
```

## Best Practices

### 1. Organize by Category

```
project/
├── tests/
│   ├── auth-tests.yaml
│   └── user-tests.yaml
└── includes/
    ├── auth/
    │   ├── login.json
    │   └── refresh-token.json
    └── users/
        ├── create-user.json
        └── update-profile.json
```

### 2. Use Templates for Multiple Contexts

Create templates with variables:

```json
{
  "environment": "${ENVIRONMENT}",
  "client_id": "${CLIENT_ID}",
  "data": {
    "value": "${TEST_VALUE}"
  }
}
```

### 3. Version Control Benefits

- Track payload changes separately from test logic
- Review large payloads more easily
- Reuse across multiple probe files

### 4. Keep Probes Readable

Use !include for:
- ✅ Payloads >10 lines
- ✅ Complex GraphQL queries
- ✅ SOAP envelopes
- ✅ Reusable templates

Keep inline for:
- ❌ Simple payloads (1-5 lines)
- ❌ Probe-specific data

## Examples

See:
- [include-directive.yaml](../examples/passing/include-directive.yaml) - Basic usage
- [include-with-variables.yaml](../examples/passing/include-with-variables.yaml) - Variable substitution

## Limitations

1. **Circular includes not supported**
   ```yaml
   # file-a.yaml
   body: !include file-b.yaml
   
   # file-b.yaml
   data: !include file-a.yaml  # ERROR: circular
   ```

2. **Content must match the expected structure**
   The `!include` tag itself works anywhere in YAML. What matters is whether the loaded content is the right type for that field:
   - `body: !include payload.json` ✅ (JSON object matches body)
   - `query: !include query.graphql` ✅ (text matches query string)
   - `variables: !include vars.json` ✅ (JSON object matches variables)
   - `validations: !include validations.yaml` ✅ (YAML dict matches validations)
   - Nested `!include` inside included YAML files ✅
   - Nested `!include` inside JSON/XML files ❌ (not YAML, tag not parsed)

3. **File must exist at load time**
   - Files are loaded when config is parsed
   - Missing files cause immediate errors

## Troubleshooting

### File Not Found

**Error:** `FileNotFoundError: [Errno 2] No such file or directory: 'includes/user.json'`

**Solution:** Check path is relative to config file location:
```yaml
# If config is in tests/ and include is in includes/:
body: !include ../includes/user.json
```

### Variables Not Substituted

**Problem:** `${USER_ID}` appears in request literally

**Solution:** This should work automatically. If not:
1. Check variable is defined in executions or environment
2. Verify variable name is correct (case-sensitive)
3. Ensure using `${VAR}` syntax, not `$VAR`

### JSON Parse Error

**Error:** `json.JSONDecodeError: Expecting property name`

**Solution:** Validate JSON file:
```bash
# Check JSON syntax
cat includes/user.json | python -m json.tool
```
