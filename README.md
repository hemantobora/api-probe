# api-probe

**Containerized API validation tool for post-deployment functional testing in CI/CD pipelines.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

## Features

✅ REST & GraphQL Support  
✅ XML/SOAP Support (XPath)  
✅ Multi-Value Variables (parallel test runs)  
✅ Variable Substitution (`${VAR}`)  
✅ Output Variable Capture (chain tests)  
✅ Rich Validations (status, headers, body)  
✅ Silent Success / Verbose Failure  
✅ Docker-First, CI/CD Native  

## Quick Start

### Local Development

```bash
# One command - auto-setup and run
./run.sh examples/passing/simple.yaml
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
tests:
  - name: "Login"
    type: rest
    endpoint: "${BASE_URL}/auth"
    method: POST
    headers:
      Content-Type: "application/json"
    body:
      username: "${USERNAME}"
      password: "${PASSWORD}"
    validation:
      status: 200
    output:
      TOKEN: "body.access_token"
  
  - name: "Get Profile"
    type: rest
    endpoint: "${BASE_URL}/profile"
    headers:
      Authorization: "Bearer ${TOKEN}"
    validation:
      status: 200
      body:
        present: ["id", "email"]
```

## Multi-Value Variables (Parallel Testing)

Test multiple contexts in one run:

```bash
# Environment
export CLIENT_ID="client1,client2,client3"
export REGION="us-east,eu-west"

# Creates 3 parallel runs with position-based pairing
docker run --rm \
  -v $(pwd)/configs:/configs \
  -e CLIENT_ID="client1,client2,client3" \
  -e REGION="us-east,eu-west" \
  api-probe /configs/test.yaml
```

See [examples/passing/multi-value.yaml](examples/passing/multi-value.yaml) for details.

## Documentation

- **[Getting Started](docs/GETTING_STARTED.md)** - Installation and basic usage
- **[Schema Reference](docs/schema-specification.md)** - Complete YAML syntax
- **[Docker Usage](docs/DOCKER.md)** - Container usage and CI/CD integration
- **[XML/SOAP Guide](docs/XML_SOAP_GUIDE.md)** - XPath expressions and SOAP testing

## Examples

### Passing Examples (Expected: ✓ Silent Success)
- [simple.yaml](examples/passing/simple.yaml) - Basic REST API tests
- [comprehensive.yaml](examples/passing/comprehensive.yaml) - All validation keywords
- [complex-validation.yaml](examples/passing/complex-validation.yaml) - Advanced patterns
- [graphql.yaml](examples/passing/graphql.yaml) - GraphQL API testing
- [xml-soap.yaml](examples/passing/xml-soap.yaml) - XML/SOAP with XPath
- [multi-value.yaml](examples/passing/multi-value.yaml) - Parallel execution
- [advanced-features.yaml](examples/passing/advanced-features.yaml) - JSONPath + parallel groups

### Failing Examples (Expected: ✗ Verbose Errors)
- [test-failures.yaml](examples/failing/test-failures.yaml) - Intentional failures for testing

## CI/CD Integration

### GitHub Actions
```yaml
- name: API Tests
  run: |
    docker run --rm \
      -v ${{ github.workspace }}/configs:/configs \
      -e API_KEY="${{ secrets.API_KEY }}" \
      api-probe:latest /configs/tests.yaml
```

### Concourse
```yaml
- task: api-tests
  image: api-probe-image
  params:
    API_KEY: ((api-key))
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

**Version:** 0.1.0  
**Status:** Production Ready

## License

See [LICENSE](LICENSE)
