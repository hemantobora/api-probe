# Docker Usage Guide

## Building the Image

```bash
# Build locally
docker build -t api-probe:latest .

# Build with version tag
docker build -t api-probe:0.1.0 .
```

## Running Probes

### Basic Usage

```bash
# Run with local config file
docker run --rm \
  -v $(pwd)/examples:/configs \
  api-probe:latest /configs/passing/simple.yaml
```

### Validate Configs

Validate your configuration and environment variables inside Docker:

```bash
docker run --rm \
  -v $(pwd)/configs:/configs \
  api-probe:latest validate /configs/tests.yaml
```

See [VALIDATION.md](VALIDATION.md) and [VALIDATE_COMMAND.md](VALIDATE_COMMAND.md) for details.

### With Environment Variables

```bash
# Single values
docker run --rm \
  -v $(pwd)/examples:/configs \
  -e BASE_URL="https://api.example.com" \
  -e CLIENT_ID="abc123" \
  api-probe:latest /configs/passing/simple.yaml
```

### Multi-Value Variables (Parallel Runs)

```bash
# Test multiple contexts in one run
docker run --rm \
  -v $(pwd)/examples:/configs \
  -e CLIENT_ID="client1,client2,client3" \
  -e REGION="us-east,eu-west" \
  api-probe:latest /configs/passing/multi-value.yaml
```

### Using Environment File

```bash
# Create .env file
cat > test.env <<EOF
BASE_URL=https://api.example.com
CLIENT_ID=abc123
CLIENT_SECRET=secret456
EOF

# Run with env file
docker run --rm \
  -v $(pwd)/examples:/configs \
  --env-file test.env \
  api-probe:latest /configs/passing/simple.yaml
```

## CI/CD Integration

### GitHub Actions

```yaml
name: API Tests
on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run API Tests
        run: |
          docker run --rm \
            -v ${{ github.workspace }}/configs:/configs \
            -e BASE_URL="${{ secrets.API_URL }}" \
            -e API_KEY="${{ secrets.API_KEY }}" \
            api-probe:latest /configs/tests.yaml
```

### GitLab CI

```yaml
api-tests:
  image: api-probe:latest
  script:
    - api-probe /configs/tests.yaml
  variables:
    BASE_URL: $API_URL
    API_KEY: $API_KEY
```

### Jenkins

```groovy
pipeline {
    agent any
    stages {
        stage('API Tests') {
            steps {
                sh '''
                    docker run --rm \
                      -v ${WORKSPACE}/configs:/configs \
                      -e BASE_URL=${API_URL} \
                      -e API_KEY=${API_KEY} \
                      api-probe:latest /configs/tests.yaml
                '''
            }
        }
    }
}
```

### Concourse

**Simple Two-Job Pipeline:**

```yaml
resources:
  - name: my-api-tests
    type: git
    source:
      uri: https://github.com/mycompany/api-tests.git
      branch: main
  
  - name: api-probe-image
    type: registry-image
    source:
      repository: mycompany/api-probe
      tag: latest

jobs:
  - name: run-tests
    plan:
      # Get code from GitHub
      - get: my-api-tests
        trigger: true
      
      # Get Docker image
      - get: api-probe-image
      
      # Run tests
      - task: execute-tests
        image: api-probe-image
        inputs:
          - name: my-api-tests
        params:
          PROD_API_KEY: ((prod-api-key))
          BASE_URL: https://api.example.com
        run:
          path: api-probe
          args:
            - /tmp/build/*/my-api-tests/configs/api-tests.yaml
```

**Key Points:**
- Place configs in GitHub repo under `configs/` or `probes/` directory
- Mount repo as input: `inputs: [name: my-api-tests]`
- Config path: `/tmp/build/*/repo-name/path/to/config.yaml`
- Use `((credentials))` for secrets (stored in Vault/CredHub)
- Chain jobs with `passed: [previous-job]`

## Exit Codes

- `0` - All probes passed (silent, no output)
- `1` - One or more probes failed (verbose output)
- `2` - Configuration error or runtime exception

## Advanced Usage

### Custom Network

```bash
# Run in custom network
docker run --rm \
  --network my-network \
  -v $(pwd)/examples:/configs \
  api-probe:latest /configs/passing/simple.yaml
```

### Resource Limits

```bash
# Set memory and CPU limits
docker run --rm \
  --memory=512m \
  --cpus=1 \
  -v $(pwd)/examples:/configs \
  api-probe:latest /configs/passing/simple.yaml
```

### Debug Mode

```bash
# See what's happening
docker run --rm \
  -v $(pwd)/examples:/configs \
  api-probe:latest /configs/passing/simple.yaml
echo "Exit code: $?"
```

## Volume Mounting

Mount your config directory to `/configs`:

```bash
# Local configs
docker run --rm \
  -v /path/to/your/configs:/configs \
  api-probe:latest /configs/yourtest.yaml

# Multiple mount points
docker run --rm \
  -v $(pwd)/configs:/configs \
  -v $(pwd)/bodies:/bodies \
  -e CONFIG_DIR=/configs \
  api-probe:latest /configs/test.yaml
```

## Security Best Practices

1. **Never hardcode secrets in configs** - Use environment variables
2. **Use env files for local probing** - Keep them out of git
3. **Use CI/CD secrets** - For production credentials
4. **Run as non-root** - Container already configured
5. **Use readonly volumes** - If configs don't need modification:
   ```bash
   -v $(pwd)/configs:/configs:ro
   ```

## Troubleshooting

### Config file not found
```bash
# Make sure path is absolute inside container
docker run --rm \
  -v $(pwd)/examples:/configs \
  api-probe:latest /configs/passing/simple.yaml  # NOT examples/passing/simple.yaml
```

### Permission denied
```bash
# Container runs as user 1000, ensure files are readable
chmod -R 644 configs/
```

### Variable not substituted
```bash
# Check environment variables are passed correctly
docker run --rm \
  -e DEBUG=1 \
  -v $(pwd)/examples:/configs \
  api-probe:latest /configs/passing/simple.yaml
```

## Examples

See the `examples/` directory for sample configurations:

### Passing Examples (Expected: ✓ Silent Success)
- `passing/simple.yaml` - Basic REST API probes
- `passing/comprehensive.yaml` - All validation keywords
- `passing/graphql.yaml` - GraphQL API probing
- `passing/multi-value.yaml` - Parallel execution with multi-value variables
- `passing/complex-validation.yaml` - Advanced validation patterns
- `passing/advanced-features.yaml` - JSONPath wildcards and parallel groups

### Failing Examples (Expected: ✗ Verbose Errors)
- `failing/test-failures.yaml` - Intentional failures for testing error reporting

## Quick Test

```bash
# Test the setup
docker build -t api-probe:test .

# Run a passing example (should be silent)
docker run --rm \
  -v $(pwd)/examples:/configs \
  api-probe:test /configs/passing/simple.yaml
echo "Exit code: $?"  # Should be 0

# Run a failing example (should show errors)
docker run --rm \
  -v $(pwd)/examples:/configs \
  api-probe:test /configs/failing/test-failures.yaml
echo "Exit code: $?"  # Should be 1
```
