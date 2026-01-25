# api-probe

**Containerized API validation tool for post-deployment functional testing in CI/CD pipelines.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

## Features

✅ REST & GraphQL Support  
✅ Multi-Value Variables (parallel test runs)  
✅ Variable Substitution (`${VAR}`)  
✅ Output Variable Capture (chain tests)  
✅ Rich Validations (status, headers, body)  
✅ Silent Success / Verbose Failure  
✅ Docker-First, CI/CD Native  

## Quick Start

```bash
# One command - auto-setup and run
./run.sh examples/simple.yaml
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

## Documentation

- **[Getting Started](GETTING_STARTED.md)** - Installation and basic usage
- **[Schema Reference](docs/schema-specification.md)** - Complete YAML syntax

## Installation

```bash
# Local development
./run.sh examples/simple.yaml

# Docker
docker build -t api-probe .
docker run --rm api-probe /configs/test.yaml
```

See [GETTING_STARTED.md](GETTING_STARTED.md) for details.

## Status

**Version:** 0.1.0  
**Status:** MVP in progress

## License

See [LICENSE](LICENSE)
