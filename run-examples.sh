#!/bin/bash
# Run all examples with required environment variables

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Running All Examples${NC}"
echo -e "${BLUE}================================${NC}"
echo

# Set dummy environment variables for examples that need them
export BASE_URL="https://httpbin.org"
export USERNAME="testuser"
export PASSWORD="testpass123"
export API_KEY="dummy-api-key-12345"
export TOKEN="dummy-bearer-token"
export CLIENT_ID="client-test-123"
export REGION="us-east-1"
export ACCOUNT="123456789"
export USER_ID="12345"
export PROD_API_KEY="prod-key-secret"
export STAGING_API_KEY="staging-key-secret"
export PROD_KEY="prod-secret"
export STAGING_KEY="staging-secret"
export STAGING_CLIENT_ID="staging-client-id"
export EXPECTED_EMAIL="test@example.com"

# Counter
PASS=0
FAIL=0

# Test function
run_test() {
    local name="$1"
    local file="$2"
    local expected_exit="$3"
    
    echo -e "${BLUE}Testing: ${name}${NC}"
    echo "  File: $file"
    
    if ./run.sh "$file" > /tmp/test_output.txt 2>&1; then
        actual_exit=0
    else
        actual_exit=$?
    fi
    
    if [ "$actual_exit" -eq "$expected_exit" ]; then
        echo -e "${GREEN}  ✓ PASS${NC} (exit code: $actual_exit)"
        ((PASS++))
    else
        echo -e "${RED}  ✗ FAIL${NC} (expected exit $expected_exit, got $actual_exit)"
        echo "  Output:"
        cat /tmp/test_output.txt | sed 's/^/    /'
        ((FAIL++))
    fi
    echo
}

echo -e "${YELLOW}=== PASSING EXAMPLES (Expected: Exit 0, Silent) ===${NC}"
echo

# Passing tests - should all exit 0 (silent success)
run_test "Simple REST tests" \
    "examples/passing/simple.yaml" \
    0

run_test "Comprehensive validation (all keywords)" \
    "examples/passing/comprehensive.yaml" \
    0

run_test "Complex validation patterns" \
    "examples/passing/complex-validation.yaml" \
    0

run_test "GraphQL API testing" \
    "examples/passing/graphql.yaml" \
    0

run_test "XML/SOAP with XPath" \
    "examples/passing/xml-soap.yaml" \
    0

run_test "Executions block with multiple contexts" \
    "examples/passing/executions-block.yaml" \
    0

run_test "Multi-context execution" \
    "examples/passing/multi-context.yaml" \
    0

run_test "No executions block (backward compat)" \
    "examples/passing/no-executions.yaml" \
    0

run_test "Generated execution names" \
    "examples/passing/generated-names.yaml" \
    0

run_test "Variable isolation test" \
    "examples/passing/isolation-test.yaml" \
    0

run_test "Sequential and parallel execution" \
    "examples/passing/verification-suite.yaml" \
    0

run_test "Advanced features (JSONPath, parallel)" \
    "examples/passing/advanced-features.yaml" \
    0

run_test "Parallel groups" \
    "examples/passing/groups-parallel.yaml" \
    0

run_test "Include directive (!include)" \
    "examples/passing/include-directive.yaml" \
    0

run_test "Include with variable substitution" \
    "examples/passing/include-with-variables.yaml" \
    0

run_test "Extensive example with validation substitutions" \
    "examples/passing/extensive-fields.yml" \
    0    

echo -e "${YELLOW}=== FAILING EXAMPLES (Expected: Exit 1, Verbose) ===${NC}"
echo

# Failing tests - should all exit 1 (verbose failure)
run_test "Intentional basic failures" \
    "examples/failing/test-failures.yaml" \
    1

run_test "Validation failures (all validators)" \
    "examples/failing/validation-failures.yaml" \
    1

run_test "Variable validation failures" \
    "examples/failing/variable-validation-failures.yaml" \
    1

run_test "Group failures (parallel)" \
    "examples/failing/group-failures.yaml" \
    1

run_test "Execution names in reports (explicit)" \
    "examples/failing/execution-names-in-reports.yaml" \
    1

run_test "Multiple execution failures" \
    "examples/failing/multiple-execution-failures.yaml" \
    1

run_test "Auto-generated names in failures" \
    "examples/failing/auto-generated-names-failures.yaml" \
    1

run_test "Validation override in execution context" \
    "examples/failing/execution-overrides-failing.yaml" \
    1    

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}================================${NC}"
echo -e "Tests Passed: ${GREEN}${PASS}${NC}"
echo -e "Tests Failed: ${RED}${FAIL}${NC}"
echo

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ ALL EXAMPLES PASSED${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME EXAMPLES FAILED${NC}"
    exit 1
fi
