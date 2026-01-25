# Getting Started with api-probe

## Installation

### Quick Start (Recommended)

```bash
# Make run script executable
chmod +x run.sh

# Run - auto-creates venv and installs everything
./run.sh examples/simple.yaml
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
api-probe examples/simple.yaml
```

## Basic Usage

### Simple REST API Test

```yaml
# config.yaml
tests:
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

### With Variables

```yaml
tests:
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

### Chaining Tests (Output Variables)

```yaml
tests:
  # First test - login
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
  
  # Second test - uses captured token
  - name: "Get Profile"
    type: rest
    endpoint: "https://api.example.com/profile"
    headers:
      Authorization: "Bearer ${ACCESS_TOKEN}"
    validation:
      status: 200
```

### Multi-Value Variables (Parallel Runs)

Test multiple contexts in one run:

```bash
export CLIENT_ID="client1,client2,client3"
export ACCOUNT="acc1,acc2"
./run.sh config.yaml
```

This creates 3 parallel execution runs:
- Run 1: `CLIENT_ID=client1, ACCOUNT=acc1`
- Run 2: `CLIENT_ID=client2, ACCOUNT=acc2`  
- Run 3: `CLIENT_ID=client3, ACCOUNT=acc2` (last value repeats)

## Exit Codes

- `0` - All tests passed (silent, no output)
- `1` - One or more tests failed (verbose output)
- `2` - Configuration error

## Project Structure

```
api-probe/
├── run.sh              # Local dev runner
├── src/api_probe/      # Source code
│   ├── cli.py          # Entry point
│   ├── config/         # Config loading
│   ├── execution/      # Test execution
│   ├── validation/     # Validators
│   ├── http/           # HTTP client
│   └── reporting/      # Output formatting
├── examples/           # Example configs
└── docs/               # Documentation
```

## Next Steps

- See [Schema Specification](docs/schema-specification.md) for complete YAML reference
- Check `examples/` for more config samples

## Docker (Production)

```bash
# Build
docker build -t api-probe .

# Run
docker run --rm \
  -v $(pwd)/configs:/configs \
  -e CLIENT_ID="abc123" \
  api-probe /configs/test.yaml
```

## Development

After editing code in `src/api_probe/`:
```bash
# Changes are immediately active (editable install)
./run.sh examples/simple.yaml

# No need to reinstall
```
