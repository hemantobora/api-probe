"""Main probe executor - orchestrates entire execution flow."""

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Union

from .context import ExecutionContext
from .output import OutputCapture
from .results import ProbeResult, RunResult, ExecutionResult
from .variables import VariableSubstitutor, get_env_variables
from .name_generator import generate_name
from .expression import ExpressionEvaluator
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
        self.expression_evaluator = ExpressionEvaluator()
    
    def execute(self, config: Config) -> ExecutionResult:
        """Execute all probes from configuration.
        
        Args:
            config: Parsed configuration
            
        Returns:
            Execution result with all probe results
        """
        import sys
        
        execution_result = ExecutionResult()
        
        if config.executions:
            # Multiple executions defined
            for run_index, execution in enumerate(config.executions):
                context = self._create_context_from_execution(execution)
                
                # Progress: Execution start
                print(f"\n▶ Executing: {context.execution_name}", file=sys.stderr)
                print("=" * 60, file=sys.stderr)
                
                run_result = self._execute_run(config, context, run_index)
                execution_result.run_results.append(run_result)
        else:
            # No executions block - single run with env vars
            env_vars = get_env_variables()
            context = ExecutionContext(env_vars)
            
            print(f"\n▶ Executing probes...", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            
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
        
        # Carry any per-execution validation overrides
        context = ExecutionContext(merged_vars, validation_overrides=getattr(execution, 'validations', {}))
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
                # Check if probe should be ignored
                if self._should_ignore(item, context):
                    continue
                probe_result = self._execute_probe(item, context)
                run_result.probe_results.append(probe_result)
            elif isinstance(item, Group):
                # Check if group should be ignored
                if self._should_ignore(item, context):
                    continue
                # Parallel execution for groups
                group_results = self._execute_group(item, context)
                run_result.probe_results.extend(group_results)
        
        return run_result
    
    def _should_ignore(self, item: Union[Probe, Group], context: ExecutionContext) -> bool:
        """Check if probe or group should be ignored.
        
        Args:
            item: Probe or Group to check
            context: Execution context with variables
            
        Returns:
            True if item should be ignored, False otherwise
        """
        ignore_value = item.ignore
        
        if ignore_value is None:
            return False
        
        # Handle boolean
        if isinstance(ignore_value, bool):
            return ignore_value
        
        # Handle string
        if isinstance(ignore_value, str):
            # Check if it's an expression
            if self.expression_evaluator.is_expression(ignore_value):
                # Evaluate expression with current context variables
                return self.expression_evaluator.evaluate(ignore_value, context.variables)
            
            # Check if it's a variable substitution ${VAR}
            if ignore_value.startswith("${") and ignore_value.endswith("}"):
                substitutor = VariableSubstitutor(context.variables)
                try:
                    resolved = substitutor.substitute(ignore_value)
                    # Convert to boolean
                    if isinstance(resolved, str):
                        resolved_lower = resolved.lower()
                        return resolved_lower in ('true', '1', 'yes', 'on')
                    return bool(resolved)
                except:
                    # If substitution fails, don't ignore
                    return False
            
            # Plain string - check if it's a truthy value
            return ignore_value.lower() in ('true', '1', 'yes', 'on')
        
        # Handle integers (0/1)
        if isinstance(ignore_value, int):
            return bool(ignore_value)
        
        return False
    
    def _execute_group(self, group: Group, context: ExecutionContext) -> List[ProbeResult]:
        """Execute probes in a group in parallel.
        
        Args:
            group: Group of probes to execute in parallel
            context: Execution context
            
        Returns:
            List of probe results (order preserved from group)
        """
        import sys
        
        # Progress: Show group name
        group_name = group.name if group.name else "Parallel Group"
        print(f"  [{group_name} - {len(group.probes)} probe(s)]:", file=sys.stderr)
        
        # Use ThreadPoolExecutor for parallel execution
        with ThreadPoolExecutor(max_workers=len(group.probes)) as executor:
            # Filter probes that should not be ignored
            probes_to_run = [
                probe for probe in group.probes 
                if not self._should_ignore(probe, context)
            ]
            
            if not probes_to_run:
                # All probes in group are ignored
                return []
            
            # Submit all non-ignored probes and maintain order by index
            futures = [
                executor.submit(self._execute_probe, probe, context, in_group=True)
                for probe in probes_to_run
            ]
            
            # Collect results in original order
            results = [future.result() for future in futures]
            
            return results
    
    def _execute_probe(self, probe: Probe, context: ExecutionContext, in_group: bool = False) -> ProbeResult:
        """Execute a single probe.
        
        Args:
            probe: Probe definition
            context: Execution context
            in_group: Whether this probe is part of a parallel group
            
        Returns:
            Probe result
        """
        import sys
        
        try:
            # Progress: Probe start (only if not in group, groups print at end)
            if not in_group:
                print(f"  → {probe.name}", file=sys.stderr)
            
            # Apply delay if specified
            if probe.delay is not None and probe.delay > 0:
                import time
                if probe.debug:
                    print(f"[DEBUG] Waiting {probe.delay}s...", file=sys.stderr)
                time.sleep(probe.delay)
            
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
            
            # Execute request with timeout, retry, and debug
            response = self.http_client.execute(
                request_params,
                timeout=probe.timeout,
                retry=probe.retry,
                debug=probe.debug
            )
            
            # Validate response (with variable substitution in validation values)
            errors = []
            # Determine validation spec: execution-level override or probe-level
            validation_spec_dict = None
            if hasattr(context, 'validation_overrides') and probe.name in context.validation_overrides:
                # Use override and substitute variables inside
                override_raw = context.validation_overrides[probe.name]
                validation_spec_dict = substitutor.substitute(override_raw)
            elif probe_substituted.validation:
                validation_spec_dict = self._validation_to_dict(probe_substituted.validation, substitutor)
            
            if validation_spec_dict is not None:
                errors = self.validation_engine.validate(
                    probe.name,
                    response,
                    validation_spec_dict
                )
            
            # Capture output variables
            if probe_substituted.output:
                self.output_capture.capture(response, probe_substituted.output, context)
            
            # Progress: Probe result
            if len(errors) == 0:
                if in_group:
                    print(f"    ✓ {probe.name}", file=sys.stderr)
                else:
                    print(f"    ✓ Passed", file=sys.stderr)
            else:
                if in_group:
                    print(f"    ✗ {probe.name} - Failed ({len(errors)} error(s))", file=sys.stderr)
                else:
                    print(f"    ✗ Failed ({len(errors)} error(s))", file=sys.stderr)
            
            # Build result
            return ProbeResult(
                probe_name=probe.name,
                success=len(errors) == 0,
                errors=errors,
                endpoint=probe_substituted.endpoint
            )
            
        except ValueError as e:
            # Variable substitution error or missing variable
            if in_group:
                print(f"    ⊗ {probe.name} - Skipped: {e}", file=sys.stderr)
            else:
                print(f"    ⊗ Skipped: {e}", file=sys.stderr)
            return ProbeResult(
                probe_name=probe.name,
                success=False,
                skipped=True,
                skip_reason=str(e),
                endpoint=probe.endpoint
            )
        except Exception as e:
            # HTTP or other error
            if in_group:
                print(f"    ✗ {probe.name} - Failed: {str(e)[:100]}", file=sys.stderr)
            else:
                print(f"    ✗ Failed: {str(e)[:100]}", file=sys.stderr)
            
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
            output=probe.output,
            delay=probe.delay,
            timeout=probe.timeout,
            retry=probe.retry,
            debug=probe.debug,
            ignore=probe.ignore
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
        
        if validation.response_time is not None:
            result['response_time'] = validation.response_time
        
        return result
