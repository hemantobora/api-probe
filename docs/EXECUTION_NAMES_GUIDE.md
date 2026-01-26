# Execution Names in Reports - Visual Guide

## Overview

When using the `executions` block, each execution's failures are grouped under its name in the failure report.

## Report Structure

```
============================================================
VALIDATION FAILURES
============================================================

<Execution Name 1>
------------------------------------------------------------
Probe: <Probe Name>
  Endpoint: <URL>
  ✗ <Error details>

Probe: <Another Probe Name>
  ✗ <Error details>

<Execution Name 2>
------------------------------------------------------------
Probe: <Probe Name>
  ✗ <Error details>

============================================================
SUMMARY
  Total Runs: <number of executions>
  Failed Runs: <how many failed>/<total>
  Total Probes: <total probes across all executions>
  Failed Probes: <failed>/<total>
============================================================
```

## Execution Name Types

### 1. Explicit Names

**Config:**
```yaml
executions:
  - name: "Production User A"
    vars:
      - USER_ID: "12345"
```

**Report Output:**
```
Production User A
------------------------------------------------------------
Probe: My Test
  ✗ Validation error...
```

### 2. Auto-Generated Names

**Config:**
```yaml
executions:
  - vars:  # No name provided
      - USER_ID: "12345"
```

**Report Output:**
```
awesome-paris
------------------------------------------------------------
Probe: My Test
  ✗ Validation error...
```

**Auto-generated formats:**
- `awesome-paris`
- `beautiful-tokyo`
- `elegant-switzerland`
- `magnificent-venice`
- etc.

### 3. No Executions Block

**Config:**
```yaml
# No executions block
probes:
  - name: "My Test"
```

**Report Output:**
```
Run 1
------------------------------------------------------------
Probe: My Test
  ✗ Validation error...
```

## Complete Example

### Config: execution-names-in-reports.yaml

```yaml
executions:
  - name: "Production User"
    vars:
      - EXPECTED_VALUE: "wrong-A"
  
  - name: "Staging User"
    vars:
      - EXPECTED_VALUE: "wrong-B"
  
  - vars:  # Auto-generated name
      - EXPECTED_VALUE: "wrong-C"

probes:
  - name: "Validation Test"
    endpoint: "https://httpbin.org/post"
    method: POST
    body:
      actual: "correct"
    validation:
      body:
        equals:
          json.actual: "${EXPECTED_VALUE}"
```

### Output:

```
============================================================
VALIDATION FAILURES
============================================================

Production User
------------------------------------------------------------
Probe: Validation Test
  Endpoint: https://httpbin.org/post
  ✗ Field 'json.actual': expected 'wrong-A', got 'correct'
    Field: json.actual
    Expected: wrong-A
    Got: correct

Staging User
------------------------------------------------------------
Probe: Validation Test
  Endpoint: https://httpbin.org/post
  ✗ Field 'json.actual': expected 'wrong-B', got 'correct'
    Field: json.actual
    Expected: wrong-B
    Got: correct

beautiful-london
------------------------------------------------------------
Probe: Validation Test
  Endpoint: https://httpbin.org/post
  ✗ Field 'json.actual': expected 'wrong-C', got 'correct'
    Field: json.actual
    Expected: wrong-C
    Got: correct

============================================================
SUMMARY
  Total Runs: 3
  Failed Runs: 3/3
  Total Probes: 3
  Failed Probes: 3/3
============================================================
```

## Key Points

1. **Execution names help identify context** - You immediately know which user/environment failed
2. **Only failed executions appear** - If an execution passes all probes, it's not shown
3. **Auto-generated names are unique** - Each run gets a different random name
4. **Summary shows totals** - Total runs, failed runs, and probes counts

## Benefits

✅ **Clear Context** - "Production User A failed" vs "Run 2 failed"  
✅ **Easy Debugging** - Know exactly which context needs attention  
✅ **Multiple Failures** - See which contexts have issues  
✅ **Professional Reports** - Descriptive names in CI/CD logs  

## Test It

Run these examples to see execution names in action:

```bash
# Explicit names
./run.sh examples/failing/execution-names-in-reports.yaml

# Multiple failures across executions
./run.sh examples/failing/multiple-execution-failures.yaml

# Auto-generated names
./run.sh examples/failing/auto-generated-names-failures.yaml
```
