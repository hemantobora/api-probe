# Getting Started with api-probe

## Installation

### Quick Start (Recommended)

```bash
# Make run script executable
chmod +x run.sh

# Run - auto-creates venv and installs everything
./run.sh examples/passing/simple.yaml
```

The `run.sh` script will:
1. Create `venv/` if it doesn't exist
2. Install dependencies from `requirements.txt`
3. Install api-probe in development mode
4. Run your config

### Manual Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install api-probe
pip install -e .

# Run
api-probe examples/passing/simple.yaml
```

## Basic Usage

### Simple REST API Probe

```yaml
# config.yaml
probes:
  - name: "Health Check"
    type: rest
    endpoint: "https://httpbin.org/status/200"
    validation:
      status: 200
```

Run it:
```bash
./run.sh config.yaml
```

### With Variables (No Executions Block)

```yaml
probes:
  - name: "Get User"
    type: rest
    endpoint: "${BASE_URL}/users/${USER_ID}"
    headers:
      Authorization: "Bearer ${TOKEN}"
    validation:
      status: 200
      body:
        present:
          - "id"
          - "email"
```

Set environment variables and run:
```bash
export BASE_URL="https://api.example.com"
export USER_ID="123"
export TOKEN="abc123"
./run.sh config.yaml
```

### Multiple Execution Contexts

Probe different users/accounts/regions in one run:

```yaml
executions:
  - name: "Production User A"
    vars:
      - ACCOUNT: "123456789"
      - CLIENT_ID: "client-prod-a"
      - API_KEY: "${PROD_API_KEY}"  # From environment
  
  - name: "Staging User"
    vars:
      - ACCOUNT: "999999999"
      - CLIENT_ID: "client-staging"
      - API_KEY: "${STAGING_API_KEY}"

probes:
  - name: "Get Account Info"
    type: rest
    endpoint: "https://api.example.com/accounts/${ACCOUNT}"
    headers:
      X-API-Key: "${API_KEY}"
      X-Client-ID: "${CLIENT_ID}"
    validation:
      status: 200
      body:
        equals:
          account_id: "${ACCOUNT}"  # Variable substitution in validation!
          client_id: "${CLIENT_ID}"
```

Run with environment variables:
```bash
export PROD_API_KEY="prod-secret"
export STAGING_API_KEY="staging-secret"
./run.sh config.yaml
```

**Result:** 2 executions run independently:
- "Production User A" with its variables
- "Staging User" with its variables

### Chaining Probes (Output Variables)

```yaml
probes:
  # First probe - login
  - name: "Login"
    type: rest
    endpoint: "https://api.example.com/auth"
    method: POST
    headers:
      Content-Type: "application/json"
    body:
      username: "${USERNAME}"
      password: "${PASSWORD}"
    validation:
      status: 200
    output:
      ACCESS_TOKEN: "body.access_token"
  
  # Second probe - uses captured token
  - name: "Get Profile"
    type: rest
    endpoint: "https://api.example.com/profile"
    headers:
      Authorization: "Bearer ${ACCESS_TOKEN}"
    validation:
      status: 200
```

## Exit Codes

- `0` - All probes passed (silent, no output)
- `1` - One or more probes failed (verbose output)
- `2` - Configuration error

## Project Structure

```
api-probe/
├── run.sh              # Local dev runner
├── src/api_probe/      # Source code
│   ├── cli.py          # Entry point
│   ├── config/         # Config loading
│   ├── execution/      # Probe execution
│   ├── validation/     # Validators
│   ├── http/           # HTTP client
│   └── reporting/      # Output formatting
├── examples/           # Example configs
│   ├── passing/        # Probes that should pass
│   └── failing/        # Probes that should fail
└── docs/               # Documentation
```

## Key Concepts

### Executions Block

Define multiple execution contexts:

```yaml
executions:
  - name: "Context 1"
    vars:
      - VAR1: "value1"
      - VAR2: "${FROM_ENV}"  # Get from environment
  
  - vars:  # No name - auto-generated like "awesome-paris"
      - VAR1: "value2"
```

**Rules:**
1. Each execution runs all probes independently
2. Variables are isolated between executions
3. Execution vars override environment vars
4. Use `${VAR}` in execution vars to reference environment
5. If no name provided, generates like "elegant-london"

### No Executions Block

If `executions:` is not present, runs once with environment variables:

```yaml
# No executions block
probes:
  - endpoint: "${API_URL}/test"
```

```bash
export API_URL="https://api.example.com"
./run.sh config.yaml  # Single run
```

### Variable Substitution

Works in:
- ✓ Endpoints
- ✓ Headers (keys and values)
- ✓ Request bodies
- ✓ GraphQL queries and variables
- ✓ **Validation values** (NEW!)

```yaml
validation:
  body:
    equals:
      user_id: "${USER_ID}"      # Validates against variable value
      region: "${REGION}"
    matches:
      email: "^${USER_ID}@.*"    # In regex patterns too
```

## Next Steps

- See [Schema Specification](SCHEMA_SPECIFICATION.md) for complete YAML reference
- Check `examples/passing/` for more config samples
- Read [DOCKER.md](DOCKER.md) for container usage

## Docker (Production)

```bash
# Build
docker build -t api-probe .

# Run with environment variables
docker run --rm \
  -v $(pwd)/configs:/configs \
  -e PROD_API_KEY="secret123" \
  -e STAGING_API_KEY="secret456" \
  api-probe /configs/test.yaml
```

## Development

After editing code in `src/api_probe/`:
```bash
# Changes are immediately active (editable install)
./run.sh examples/passing/simple.yaml

# No need to reinstall
```
