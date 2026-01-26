# Validate Command - Updated Summary

## Changes Made

### Output Changes ✅
1. **All output to stderr** - CI/CD tools can capture separately
2. **No value printing** - Only shows defined/not defined
3. **Exit codes unchanged** - 0=valid, 1=invalid, 2=error

## Usage

```bash
./run.sh validate config.yaml
```

## Example Output (stderr)

```
Validating: config.yaml
============================================================

📋 ENVIRONMENT VARIABLES REFERENCED:

  ✓ Defined:
    • BASE_URL
    • API_KEY
    • CLIENT_ID

  ✗ Not defined:
    • REGION
    • USER_ID

Parsing configuration...
✓ Successfully parsed 5 probe(s)
✓ Found 3 execution context(s)

============================================================
✅ Configuration is valid!
```

**Note:** No values are shown - only variable names.

## With Errors

```
Validating: config.yaml
============================================================

❌ VALIDATION ERRORS:
  • Probe 1: missing required 'endpoint' field
  • Probe 2: REST probe with body must have Content-Type header

⚠️  WARNINGS:
  • Probe 3: negative delay will be ignored

📋 ENVIRONMENT VARIABLES REFERENCED:

  ✓ Defined:
    • BASE_URL

  ✗ Not defined:
    • API_KEY
    • CLIENT_ID

Parsing configuration...
✗ Parse error: Probe 'Test' must have 'endpoint' field

============================================================
❌ Configuration has errors
```

## CI/CD Integration

### Capture stderr

```bash
# Capture validation output
./run.sh validate config.yaml 2>validation.log

# Check exit code
if [ $? -eq 0 ]; then
  echo "Valid"
else
  echo "Invalid"
  cat validation.log
fi
```

### GitHub Actions

```yaml
- name: Validate Config
  run: |
    docker run --rm \
      -v ${{ github.workspace }}:/workspace \
      api-probe:latest validate /workspace/config.yaml
  # Validation output goes to stderr (visible in logs)
  # Exit code determines success/failure
```

### GitLab CI

```yaml
validate:
  script:
    - docker run --rm \
        -v $(pwd):/workspace \
        api-probe:latest validate /workspace/config.yaml
  # stderr output captured in job logs
```

### Extract Variable Lists

```bash
# Get undefined variables
./run.sh validate config.yaml 2>&1 | \
  grep -A 100 "Not defined" | \
  grep "•" | \
  sed 's/.*• //'

# Output:
# REGION
# USER_ID
```

```bash
# Get defined variables
./run.sh validate config.yaml 2>&1 | \
  grep -A 100 "Defined:" | \
  grep "•" | \
  sed 's/.*• //'

# Output:
# BASE_URL
# API_KEY
# CLIENT_ID
```

## Benefits of stderr Output

1. **CI/CD Friendly** - Logs go to stderr, scripts can process separately
2. **Security** - No values exposed in logs
3. **Piping** - Can pipe stderr separately from stdout
4. **Standard Practice** - Diagnostic output belongs in stderr

## Exit Codes

| Code | Meaning | CI/CD Action |
|------|---------|--------------|
| 0 | Valid | ✅ Continue pipeline |
| 1 | Invalid | ❌ Block deployment |
| 2 | Error | ❌ Block deployment |

## Example: Complete CI Workflow

```bash
#!/bin/bash
# validate-and-run.sh

CONFIG="tests/api-tests.yaml"

echo "Step 1: Validating configuration..."
./run.sh validate "$CONFIG" 2>validation.log

if [ $? -ne 0 ]; then
  echo "❌ Validation failed:"
  cat validation.log
  exit 1
fi

echo "✅ Validation passed"

echo "Step 2: Checking environment variables..."
UNDEFINED=$(grep -A 100 "Not defined" validation.log | grep "•" | wc -l)

if [ $UNDEFINED -gt 0 ]; then
  echo "⚠️  Some variables not defined:"
  grep -A 100 "Not defined" validation.log | grep "•"
  echo ""
  read -p "Continue anyway? (y/n) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

echo "Step 3: Running probes..."
./run.sh "$CONFIG"
```

## What Changed

### Before ❌
- Mixed stdout/stderr output
- Showed variable values (security risk)
- `• BASE_URL = https://api.example.com`

### After ✅
- All output to stderr
- Only shows variable names
- `• BASE_URL`

## Security Benefit

**Before:**
```
✓ Defined:
  • API_KEY = prod-secret-key-abc123def456...
  • PASSWORD = myP@ssw0rd!
```

**After:**
```
✓ Defined:
  • API_KEY
  • PASSWORD
```

No secrets in logs! 🔒
