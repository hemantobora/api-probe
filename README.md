# api-probe

**Containerized API validation tool for post-deployment functional testing in CI/CD pipelines.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

## Features

✅ REST & GraphQL Support  
✅ XML/SOAP Support (XPath)  
✅ Multiple Execution Contexts (test different users/accounts)  
✅ Variable Substitution in requests AND validations  
✅ Output Variable Capture with expressions (len, has, empty)  
✅ Conditional Probe Execution (ignore field with expressions)  
✅ Conditional Validation (skip headers/body based on response)  
✅ Parallel Group Execution  
✅ Include Directive (!include) for external files  
✅ Rich Validations (status, headers, body)  
✅ Timeout, Retry, Debug support  
✅ Response Time Validation  
✅ Progress Reporting to stderr  
✅ Silent Success / Verbose Failure  
✅ Docker-First, CI/CD Native  

## Quick Start

### Local Development

```bash
# One command - auto-setup and run
./run.sh examples/passing/simple.yaml

# Run all examples
chmod +x run-examples.sh
./run-examples.sh
```

### Docker

```bash
# Build
docker build -t api-probe .

# Run
docker run --rm \
  -v $(pwd)/examples:/configs \
  api-probe /configs/passing/simple.yaml
```

## Example

```yaml
executions:
  - name: "Production User"
    vars:
      - ACCOUNT: "123456789"
      - API_KEY: "${PROD_API_KEY}"  # From environment
  
  - name: "Staging User"
    vars:
      - ACCOUNT: "987654321"
      - API_KEY: "${STAGING_API_KEY}"

probes:
  - name: "Login"
    type: rest
    endpoint: "${BASE_URL}/auth"
    method: POST
    headers:
      Content-Type: "application/json"
    body: !include includes/login-body.json  # External file
    validation:
      status: 200
      response_time: 1000  # Must respond within 1 second
      body:
        equals:
          account_id: "${ACCOUNT}"  # Variable substitution in validation!
    output:
      TOKEN: "body.access_token"
      HAS_PREMIUM: "has(body.premium)"  # Expression evaluation
  
  - name: "Get Profile"
    type: rest
    endpoint: "${BASE_URL}/profile"
    headers:
      Authorization: "Bearer ${TOKEN}"
    validation:
      status: 200
      body:
        present: ["id", "email"]
  
  - name: "Get Premium Features"
    type: rest
    endpoint: "${BASE_URL}/features"
    ignore: "!HAS_PREMIUM"  # Skip if not premium user
    validation:
      status: 200
      body:
        ignore: "empty(body.features)"  # Skip validation if empty
        present: ["features[0].name"]
```

## Multiple Execution Contexts

Test different user accounts, regions, or environments in one run:

```yaml
executions:
  - name: "US East User"
    vars:
      - CLIENT_ID: "client-123"
      - REGION: "us-east-1"
  
  - name: "EU West User"
    vars:
      - CLIENT_ID: "client-456"
      - REGION: "eu-west-1"

probes:
  - name: "API Test"
    endpoint: "https://api.example.com/${REGION}/data"
    headers:
      X-Client: "${CLIENT_ID}"
    validation:
      body:
        equals:
          region: "${REGION}"  # Validates against execution-specific value
```

Each execution runs independently with isolated variables.

See [examples/passing/executions-block.yaml](examples/passing/executions-block.yaml) for details.

## Conditional Execution

Skip probes or validation based on previous results:

```yaml
probes:
  - name: "Get Offers"
    endpoint: "https://api.example.com/offers"
    output:
      OFFER_COUNT: "len(body.offers)"  # Capture count using expression
      HAS_PREMIUM: "has(body.premium)"
  
  - name: "Process Rich Offers"
    endpoint: "https://api.example.com/process"
    ignore: "OFFER_COUNT <= 2"  # Skip if not enough offers
    validation:
      status: 200
  
  - name: "Validate Premium Features"
    endpoint: "https://api.example.com/user"
    validation:
      status: 200
      body:
        ignore: "!HAS_PREMIUM"  # Skip body validation if not premium
        present:
          - "premium.tier"
          - "premium.benefits"
```

**Expression Functions:**
- `len(VAR)` - Get length of array/string/dict
- `has(VAR)` - Check if exists and not empty
- `empty(VAR)` - Check if empty or None

**Operators:** `==`, `!=`, `>`, `<`, `>=`, `<=`, `&&`, `||`, `!`

See [SCHEMA_SPECIFICATION.md](docs/SCHEMA_SPECIFICATION.md#expression-evaluation) for details.

## Parallel Groups

Run probes in parallel for faster execution:

```yaml
probes:
  - name: "Sequential Test"
    endpoint: "https://api.example.com/test"
  
  # All probes in group run in parallel
  - group:
      probes:
        - name: "Parallel Test 1"
          endpoint: "https://api.example.com/delay/2"
        - name: "Parallel Test 2"
          endpoint: "https://api.example.com/delay/2"
        - name: "Parallel Test 3"
          endpoint: "https://api.example.com/delay/2"
  # Group completes in ~2 seconds instead of 6 seconds
```

See [examples/passing/groups-parallel.yaml](examples/passing/groups-parallel.yaml) for details.

## Include Directive

Keep large request bodies in separate files:

```yaml
probes:
  - name: "Create User"
    type: rest
    endpoint: "https://api.example.com/users"
    method: POST
    headers:
      Content-Type: "application/json"
    body: !include includes/user-profile.json
    validation:
      status: 201
```

See [examples/passing/include-directive.yaml](examples/passing/include-directive.yaml) for details.

## Documentation

- **[GETTING_STARTED.md](docs/GETTING_STARTED.md)** - Installation and basic usage
- **[SCHEMA_SPECIFICATION.md](docs/SCHEMA_SPECIFICATION.md)** - Complete YAML syntax
- **[DOCKER.md](docs/DOCKER.md)** - Container usage and CI/CD integration
- **[XML_SOAP_GUIDE.md](docs/XML_SOAP_GUIDE.md)** - XPath expressions and SOAP testing
- **[INCLUDE_DIRECTIVE.md](docs/INCLUDE_DIRECTIVE.md)** - YAML include directive usage

## Examples

### Passing Examples (Expected: ✓ Silent Success)
- [simple.yaml](examples/passing/simple.yaml) - Basic REST API probes
- [comprehensive.yaml](examples/passing/comprehensive.yaml) - All validation keywords
- [complex-validation.yaml](examples/passing/complex-validation.yaml) - Advanced patterns
- [graphql.yaml](examples/passing/graphql.yaml) - GraphQL API testing
- [xml-soap.yaml](examples/passing/xml-soap.yaml) - XML/SOAP with XPath
- [executions-block.yaml](examples/passing/executions-block.yaml) - Multiple execution contexts
- [multi-context.yaml](examples/passing/multi-context.yaml) - Multi-user testing
- [no-executions.yaml](examples/passing/no-executions.yaml) - Single run with env vars
- [groups-parallel.yaml](examples/passing/groups-parallel.yaml) - Parallel group execution
- [include-directive.yaml](examples/passing/include-directive.yaml) - External file includes
- [advanced-features.yaml](examples/passing/advanced-features.yaml) - JSONPath + parallel groups

### Failing Examples (Expected: ✗ Verbose Errors)
- [test-failures.yaml](examples/failing/test-failures.yaml) - Basic intentional failures
- [validation-failures.yaml](examples/failing/validation-failures.yaml) - All validator failures
- [variable-validation-failures.yaml](examples/failing/variable-validation-failures.yaml) - Variable validation errors
- [group-failures.yaml](examples/failing/group-failures.yaml) - Failures in parallel groups
- [execution-names-in-reports.yaml](examples/failing/execution-names-in-reports.yaml) - Execution names in failure output
- [multiple-execution-failures.yaml](examples/failing/multiple-execution-failures.yaml) - Different failures per execution
- [auto-generated-names-failures.yaml](examples/failing/auto-generated-names-failures.yaml) - Auto-generated execution names

## Running All Examples

```bash
# Set executable permission
chmod +x run-examples.sh

# Run all passing and failing examples
./run-examples.sh
```

This will run all 15 passing examples and 7 failing examples with proper environment variables.

## CI/CD Integration

### GitHub Actions
```yaml
- name: API Tests
  run: |
    docker run --rm \
      -v ${{ github.workspace }}/configs:/configs \
      -e PROD_API_KEY="${{ secrets.PROD_API_KEY }}" \
      -e STAGING_API_KEY="${{ secrets.STAGING_API_KEY }}" \
      api-probe:latest /configs/tests.yaml
```

### Concourse
```yaml
- task: api-tests
  image: api-probe-image
  params:
    PROD_API_KEY: ((prod-api-key))
    STAGING_API_KEY: ((staging-api-key))
  run:
    path: api-probe
    args: ["/configs/tests.yaml"]
```

See [DOCKER.md](docs/DOCKER.md) for more CI/CD examples.

## Installation

### Docker (Recommended)
```bash
docker build -t api-probe .
docker run --rm api-probe --help
```

### Local Development
```bash
./run.sh examples/passing/simple.yaml
```

See [GETTING_STARTED.md](docs/GETTING_STARTED.md) for details.

## Status

**Version:** 2.4.0  
**Status:** Production Ready

## Version History

- **v2.4.0**
  - Added expression evaluation in `output` field (len, has, empty functions)
  - Added expression evaluation in `ignore` field (len, has, empty functions)
  - Added `ignore` field in validation headers and body sections
  - Expressions support operators: ==, !=, >, <, >=, <=, &&, ||, !
  - Expressions can access response data: status, body.*, headers.*

- **v2.3.0**
  - Added `ignore` field for probes and groups (conditional execution)
  - Added `name` field for groups (with auto-generation)
  - Improved parallel group progress reporting with names

- **v2.2.0**
  - Added timeout field for request timeouts
  - Added retry configuration for automatic retries
  - Added debug flag for request/response logging
  - Added response_time validation for performance checks
  - Added status pattern matching (2xx, 3xx, 4xx, 5xx)
  - Added progress reporting to stderr
  - Fixed length validator for root-level arrays ($)

- **v2.1.0**
  - Added delay field for probes
  - Added length validator for arrays and strings

- **v2.0.0**
  - Added executions block
  - Added variable substitution in validation
  - Added parallel groups
  - Added XML/SOAP support
  - Added !include directive
  - Enhanced variable resolution

- **v1.0.0**
  - Initial release

## License

See [LICENSE](LICENSE)
