"""Main test executor - orchestrates entire execution flow."""

from typing import Any, Dict, List

from .context import ExecutionContext
from .output import OutputCapture
from .results import TestResult, RunResult, ExecutionResult
from .variables import VariableSubstitutor, parse_env_vars, create_execution_contexts
from ..config.models import Config, Test, Group
from ..http.builder import RequestBuilder
from ..http.client import HTTPClient
from ..validation.engine import ValidationEngine
from ..validation.extractor import PathExtractor


class TestExecutor:
    """Executes tests from configuration."""
    
    def __init__(self):
        """Initialize executor with dependencies."""
        self.request_builder = RequestBuilder()
        self.http_client = HTTPClient()
        self.validation_engine = ValidationEngine()
        self.output_capture = OutputCapture(PathExtractor())
    
    def execute(self, config: Config) -> ExecutionResult:
        """Execute all tests from configuration.
        
        Args:
            config: Parsed configuration
            
        Returns:
            Execution result with all test results
        """
        # Parse environment variables for multi-value expansion
        env_vars = parse_env_vars()
        
        # Create execution contexts (one per run)
        var_contexts = create_execution_contexts(env_vars)
        
        # Execute tests in each context
        execution_result = ExecutionResult()
        
        for run_index, var_dict in enumerate(var_contexts):
            # Create ExecutionContext from variable dict
            context = ExecutionContext(var_dict)
            run_result = self._execute_run(config, context, run_index)
            execution_result.run_results.append(run_result)
        
        return execution_result
    
    def _execute_run(self, config: Config, context: ExecutionContext, run_index: int) -> RunResult:
        """Execute all tests in a single run context.
        
        Args:
            config: Configuration
            context: Execution context with variables
            run_index: Index of this run (for reporting)
            
        Returns:
            Run result with all test results
        """
        run_result = RunResult(run_index=run_index)
        
        # Execute tests sequentially (groups handled separately)
        for item in config.tests:
            if isinstance(item, Test):
                test_result = self._execute_test(item, context)
                run_result.test_results.append(test_result)
            elif isinstance(item, Group):
                # TODO: Parallel execution for groups
                # For now, execute sequentially
                for test in item.tests:
                    test_result = self._execute_test(test, context)
                    run_result.test_results.append(test_result)
        
        return run_result
    
    def _execute_test(self, test: Test, context: ExecutionContext) -> TestResult:
        """Execute a single test.
        
        Args:
            test: Test definition
            context: Execution context
            
        Returns:
            Test result
        """
        try:
            # Substitute variables in test
            substitutor = VariableSubstitutor(context.variables)
            test_substituted = self._substitute_test(test, substitutor)
            
            # Build request
            if test_substituted.type == "rest":
                request_params = self.request_builder.build_rest_request(
                    endpoint=test_substituted.endpoint,
                    method=test_substituted.method,
                    headers=test_substituted.headers,
                    body=test_substituted.body
                )
            else:  # graphql
                request_params = self.request_builder.build_graphql_request(
                    endpoint=test_substituted.endpoint,
                    query=test_substituted.query,
                    variables=test_substituted.variables,
                    headers=test_substituted.headers
                )
            
            # Execute request
            response = self.http_client.execute(request_params)
            
            # Validate response
            errors = []
            if test_substituted.validation:
                validation_spec = self._validation_to_dict(test_substituted.validation)
                errors = self.validation_engine.validate(
                    test.name,
                    response,
                    validation_spec
                )
            
            # Capture output variables
            if test_substituted.output:
                self.output_capture.capture(response, test_substituted.output, context)
            
            # Build result
            return TestResult(
                test_name=test.name,
                success=len(errors) == 0,
                errors=errors,
                endpoint=test_substituted.endpoint  # Include parsed endpoint
            )
            
        except ValueError as e:
            # Variable substitution error or missing variable
            return TestResult(
                test_name=test.name,
                success=False,
                skipped=True,
                skip_reason=str(e),
                endpoint=test.endpoint  # Original endpoint (variables not substituted)
            )
        except Exception as e:
            # HTTP or other error
            from ..validation.base import ValidationError
            
            # Try to get substituted endpoint, fall back to original
            try:
                substitutor = VariableSubstitutor(context.variables)
                endpoint = substitutor.substitute(test.endpoint)
            except:
                endpoint = test.endpoint
            
            return TestResult(
                test_name=test.name,
                success=False,
                errors=[ValidationError(
                    test_name=test.name,
                    validator="execution",
                    field="request",
                    expected="successful execution",
                    actual="error",
                    message=str(e)
                )],
                endpoint=endpoint
            )
    
    def _substitute_test(self, test: Test, substitutor: VariableSubstitutor) -> Test:
        """Substitute variables in test definition.
        
        Args:
            test: Original test
            substitutor: Variable substitutor
            
        Returns:
            Test with substituted values
        """
        return Test(
            name=test.name,
            type=test.type,
            endpoint=substitutor.substitute(test.endpoint),
            method=test.method,
            headers=substitutor.substitute(test.headers) if test.headers else None,
            body=substitutor.substitute(test.body) if test.body else None,
            query=substitutor.substitute(test.query) if test.query else None,
            variables=substitutor.substitute(test.variables) if test.variables else None,
            validation=test.validation,  # Don't substitute in validation spec
            output=test.output
        )
    
    def _validation_to_dict(self, validation: Any) -> Dict[str, Any]:
        """Convert Validation object to dict for engine.
        
        Args:
            validation: Validation object
            
        Returns:
            Dict representation
        """
        result = {}
        if validation.status is not None:
            result['status'] = validation.status
        if validation.headers:
            result['headers'] = validation.headers
        if validation.body:
            result['body'] = validation.body
        return result
