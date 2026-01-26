"""Main probe executor - orchestrates entire execution flow."""

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

from .context import ExecutionContext
from .output import OutputCapture
from .results import ProbeResult, RunResult, ExecutionResult
from .variables import VariableSubstitutor, get_env_variables
from .name_generator import generate_name
from ..config.models import Config, Probe, Group
from ..http.builder import RequestBuilder
from ..http.client import HTTPClient
from ..validation.engine import ValidationEngine
from ..validation.extractor import PathExtractor


class ProbeExecutor:
    """Executes probes from configuration."""
    
    def __init__(self):
        """Initialize executor with dependencies."""
        self.request_builder = RequestBuilder()
        self.http_client = HTTPClient()
        self.validation_engine = ValidationEngine()
        self.output_capture = OutputCapture(PathExtractor())
    
    def execute(self, config: Config) -> ExecutionResult:
        """Execute all probes from configuration.
        
        Args:
            config: Parsed configuration
            
        Returns:
            Execution result with all probe results
        """
        execution_result = ExecutionResult()
        
        if config.executions:
            # Multiple executions defined
            for run_index, execution in enumerate(config.executions):
                context = self._create_context_from_execution(execution)
                run_result = self._execute_run(config, context, run_index)
                execution_result.run_results.append(run_result)
        else:
            # No executions block - single run with env vars
            env_vars = get_env_variables()
            context = ExecutionContext(env_vars)
            run_result = self._execute_run(config, context, 0)
            execution_result.run_results.append(run_result)
        
        return execution_result
    
    def _create_context_from_execution(self, execution) -> ExecutionContext:
        """Create execution context from execution definition.
        
        Args:
            execution: Execution object
            
        Returns:
            ExecutionContext with resolved variables
        """
        # Start with environment variables
        env_vars = get_env_variables()
        
        # Get variables from execution definition
        exec_vars = execution.get_variables_dict()
        
        # Merge: execution vars override env vars
        # But if execution var value contains ${...}, resolve from env
        merged_vars = env_vars.copy()
        
        for key, value in exec_vars.items():
            # Only attempt string-based substitution if the value is a string
            if isinstance(value, str) and '${' in value:
                # Value contains variable reference - substitute from env
                substitutor = VariableSubstitutor(env_vars)
                try:
                    resolved_value = substitutor.substitute(value)
                    merged_vars[key] = str(resolved_value)
                except ValueError:
                    # Variable not in env either - keep as is, will fail later
                    merged_vars[key] = value
            else:
                # Direct value - convert to string for storage
                merged_vars[key] = str(value)
        
        # Generate name if not provided
        name = execution.name if execution.name else generate_name()
        
        context = ExecutionContext(merged_vars)
        context.execution_name = name
        
        return context
    
    def _execute_run(self, config: Config, context: ExecutionContext, run_index: int) -> RunResult:
        """Execute all probes in a single run context.
        
        Args:
            config: Configuration
            context: Execution context with variables
            run_index: Index of this run (for reporting)
            
        Returns:
            Run result with all probe results
        """
        # Use execution name if available, otherwise use index
        run_name = getattr(context, 'execution_name', f"Run {run_index + 1}")
        run_result = RunResult(run_index=run_index, run_name=run_name)
        
        # Execute probes sequentially (groups execute in parallel)
        for item in config.probes:
            if isinstance(item, Probe):
                probe_result = self._execute_probe(item, context)
                run_result.probe_results.append(probe_result)
            elif isinstance(item, Group):
                # Parallel execution for groups
                group_results = self._execute_group(item, context)
                run_result.probe_results.extend(group_results)
        
        return run_result
    
    def _execute_group(self, group: Group, context: ExecutionContext) -> List[ProbeResult]:
        """Execute probes in a group in parallel.
        
        Args:
            group: Group of probes to execute in parallel
            context: Execution context
            
        Returns:
            List of probe results (order preserved from group)
        """
        # Use ThreadPoolExecutor for parallel execution
        with ThreadPoolExecutor(max_workers=len(group.probes)) as executor:
            # Submit all probes and maintain order by index - O(n)
            futures = [
                executor.submit(self._execute_probe, probe, context)
                for probe in group.probes
            ]
            
            # Collect results in original order - O(n)
            results = [future.result() for future in futures]
            
            return results
    
    def _execute_probe(self, probe: Probe, context: ExecutionContext) -> ProbeResult:
        """Execute a single probe.
        
        Args:
            probe: Probe definition
            context: Execution context
            
        Returns:
            Probe result
        """
        try:
            # Substitute variables in probe
            substitutor = VariableSubstitutor(context.variables)
            probe_substituted = self._substitute_probe(probe, substitutor)
            
            # Build request
            if probe_substituted.type == "rest":
                request_params = self.request_builder.build_rest_request(
                    endpoint=probe_substituted.endpoint,
                    method=probe_substituted.method,
                    headers=probe_substituted.headers,
                    body=probe_substituted.body
                )
            else:  # graphql
                request_params = self.request_builder.build_graphql_request(
                    endpoint=probe_substituted.endpoint,
                    query=probe_substituted.query,
                    variables=probe_substituted.variables,
                    headers=probe_substituted.headers
                )
            
            # Execute request
            response = self.http_client.execute(request_params)
            
            # Validate response (with variable substitution in validation values)
            errors = []
            if probe_substituted.validation:
                validation_spec = self._validation_to_dict(probe_substituted.validation, substitutor)
                errors = self.validation_engine.validate(
                    probe.name,
                    response,
                    validation_spec
                )
            
            # Capture output variables
            if probe_substituted.output:
                self.output_capture.capture(response, probe_substituted.output, context)
            
            # Build result
            return ProbeResult(
                probe_name=probe.name,
                success=len(errors) == 0,
                errors=errors,
                endpoint=probe_substituted.endpoint
            )
            
        except ValueError as e:
            # Variable substitution error or missing variable
            return ProbeResult(
                probe_name=probe.name,
                success=False,
                skipped=True,
                skip_reason=str(e),
                endpoint=probe.endpoint
            )
        except Exception as e:
            # HTTP or other error
            from ..validation.base import ValidationError
            
            # Try to get substituted endpoint, fall back to original
            try:
                substitutor = VariableSubstitutor(context.variables)
                endpoint = substitutor.substitute(probe.endpoint)
            except:
                endpoint = probe.endpoint
            
            return ProbeResult(
                probe_name=probe.name,
                success=False,
                errors=[ValidationError(
                    test_name=probe.name,
                    validator="execution",
                    field="request",
                    expected="successful execution",
                    actual="error",
                    message=str(e)
                )],
                endpoint=endpoint
            )
    
    def _substitute_probe(self, probe: Probe, substitutor: VariableSubstitutor) -> Probe:
        """Substitute variables in probe definition.
        
        Args:
            probe: Original probe
            substitutor: Variable substitutor
            
        Returns:
            Probe with substituted values
        """
        return Probe(
            name=probe.name,
            type=probe.type,
            endpoint=substitutor.substitute(probe.endpoint),
            method=probe.method,
            headers=substitutor.substitute(probe.headers) if probe.headers else None,
            body=substitutor.substitute(probe.body) if probe.body else None,
            query=substitutor.substitute(probe.query) if probe.query else None,
            variables=substitutor.substitute(probe.variables) if probe.variables else None,
            validation=probe.validation,  # Don't substitute validation spec structure
            output=probe.output
        )
    
    def _validation_to_dict(self, validation: Any, substitutor: VariableSubstitutor) -> Dict[str, Any]:
        """Convert Validation object to dict for engine with variable substitution.
        
        Args:
            validation: Validation object
            substitutor: Variable substitutor for validation values
            
        Returns:
            Dict representation with substituted values
        """
        result = {}
        
        if validation.status is not None:
            result['status'] = validation.status
        
        if validation.headers:
            # Substitute values in headers validation
            result['headers'] = substitutor.substitute(validation.headers)
        
        if validation.body:
            # Substitute values in body validation
            result['body'] = substitutor.substitute(validation.body)
        
        return result
