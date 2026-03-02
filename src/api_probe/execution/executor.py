"""Main probe executor - orchestrates entire execution flow."""

import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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


# Global print lock - ensures no two threads interleave lines on stderr
_print_lock = threading.Lock()


def _println(*args, **kwargs):
    """Thread-safe print to stderr."""
    with _print_lock:
        print(*args, file=sys.stderr, **kwargs)


def _print_block(lines: List[str]):
    """Print multiple lines atomically - no other thread can interleave."""
    with _print_lock:
        for line in lines:
            print(line, file=sys.stderr)


class ProbeExecutor:
    """Executes probes from configuration."""

    def __init__(self):
        """Initialize executor with dependencies."""
        self.request_builder = RequestBuilder()
        self.http_client = HTTPClient()
        self.validation_engine = ValidationEngine()
        self.output_capture = OutputCapture(PathExtractor())
        self.expression_evaluator = ExpressionEvaluator()

    # ------------------------------------------------------------------
    # Top-level entry point
    # ------------------------------------------------------------------

    def execute(self, config: Config) -> ExecutionResult:
        """Execute all probes from configuration.

        Multiple executions run concurrently with live progress output.
        Progress lines are printed immediately under a lock so they never
        interleave. Each probe's start + result lines are printed as a
        single atomic block.

        Args:
            config: Parsed configuration

        Returns:
            Execution result with all probe results
        """
        execution_result = ExecutionResult()

        if config.executions:
            self._execute_concurrent(config, execution_result)
        else:
            env_vars = get_env_variables()
            context = ExecutionContext(env_vars)
            _println(f"\n▶ Executing probes...")
            _println("=" * 60)
            run_result = self._execute_run(config, context, 0)
            execution_result.run_results.append(run_result)

        return execution_result

    # ------------------------------------------------------------------
    # Concurrent executions
    # ------------------------------------------------------------------

    def _execute_concurrent(self, config: Config, execution_result: ExecutionResult) -> None:
        """Run all executions concurrently with live progress.

        Execution headers are printed as they start. Probe lines within
        each execution are printed live but atomically (start + result
        together). RunResults are collected and appended in run-index
        order so ExecutionResult is always deterministic.

        Args:
            config: Parsed configuration
            execution_result: Accumulator mutated in place
        """
        num = len(config.executions)
        contexts = [
            (i, self._create_context_from_execution(ex))
            for i, ex in enumerate(config.executions)
        ]

        run_results: Dict[int, RunResult] = {}
        lock = threading.Lock()

        def run_one(run_index: int, context: ExecutionContext):
            _print_block([
                f"\n▶ Executing: {context.execution_name}",
                "=" * 60,
            ])
            run_result = self._execute_run(config, context, run_index)
            with lock:
                run_results[run_index] = run_result

        with ThreadPoolExecutor(max_workers=num) as pool:
            futures = [pool.submit(run_one, i, ctx) for i, ctx in contexts]
            for f in as_completed(futures):
                f.result()

        # Append results in original execution order
        for i in range(num):
            execution_result.run_results.append(run_results[i])

    # ------------------------------------------------------------------
    # Context creation
    # ------------------------------------------------------------------

    def _create_context_from_execution(self, execution) -> ExecutionContext:
        """Create execution context from execution definition."""
        env_vars = get_env_variables()
        exec_vars = execution.get_variables_dict()
        merged_vars = env_vars.copy()

        for key, value in exec_vars.items():
            if isinstance(value, str) and '${' in value:
                substitutor = VariableSubstitutor(env_vars)
                try:
                    resolved_value = substitutor.substitute(value)
                    merged_vars[key] = str(resolved_value)
                except ValueError:
                    merged_vars[key] = value
            else:
                merged_vars[key] = str(value)

        name = execution.name if execution.name else generate_name()
        context = ExecutionContext(merged_vars, validation_overrides=getattr(execution, 'validations', {}))
        context.execution_name = name
        return context

    # ------------------------------------------------------------------
    # Run execution
    # ------------------------------------------------------------------

    def _execute_run(
        self,
        config: Config,
        context: ExecutionContext,
        run_index: int,
    ) -> RunResult:
        """Execute all probes in a single run context sequentially.

        Args:
            config: Configuration
            context: Execution context with variables
            run_index: Index of this run

        Returns:
            Run result with all probe results
        """
        run_name = getattr(context, 'execution_name', f"Run {run_index + 1}")
        run_result = RunResult(run_index=run_index, run_name=run_name)

        for item in config.probes:
            if isinstance(item, Probe):
                if self._should_ignore(item, context):
                    continue
                probe_result = self._execute_probe(item, context)
                run_result.probe_results.append(probe_result)
            elif isinstance(item, Group):
                if self._should_ignore(item, context):
                    continue
                group_results = self._execute_group(item, context)
                run_result.probe_results.extend(group_results)

        return run_result

    # ------------------------------------------------------------------
    # Group execution
    # ------------------------------------------------------------------

    def _execute_group(
        self,
        group: Group,
        context: ExecutionContext,
    ) -> List[ProbeResult]:
        """Execute probes in a group in parallel with live progress.

        The group header is printed immediately. Each probe prints its
        start + result atomically as it completes. Results are returned
        in original probe order.

        Args:
            group: Group of probes
            context: Execution context

        Returns:
            List of probe results in original order
        """
        group_name = group.name if group.name else "Parallel Group"
        _println(f"  [{group_name} - {len(group.probes)} probe(s)]:")

        probes_to_run = [
            p for p in group.probes if not self._should_ignore(p, context)
        ]

        if not probes_to_run:
            return []

        results: Dict[int, ProbeResult] = {}
        lock = threading.Lock()

        def run_probe(idx: int, probe: Probe):
            result = self._execute_probe(probe, context, in_group=True)
            with lock:
                results[idx] = result

        with ThreadPoolExecutor(max_workers=len(probes_to_run)) as pool:
            futures = {pool.submit(run_probe, i, p): i for i, p in enumerate(probes_to_run)}
            for f in as_completed(futures):
                f.result()

        return [results[i] for i in range(len(probes_to_run))]

    # ------------------------------------------------------------------
    # Single probe execution
    # ------------------------------------------------------------------

    def _execute_probe(
        self,
        probe: Probe,
        context: ExecutionContext,
        in_group: bool = False,
    ) -> ProbeResult:
        """Execute a single probe with live atomic progress output.

        The probe's start line and its pass/fail result line are printed
        together as a single atomic block so no other thread can insert
        a line between them.

        Args:
            probe: Probe definition
            context: Execution context
            in_group: Whether this probe is part of a parallel group

        Returns:
            Probe result
        """
        try:
            if probe.delay is not None and probe.delay > 0:
                import time
                # Print delay notice immediately so user sees the wait
                if not in_group:
                    _println(f"  → {probe.name} (waiting {probe.delay}s...)")
                if probe.debug:
                    _println(f"[DEBUG] Waiting {probe.delay}s...")
                time.sleep(probe.delay)

            substitutor = VariableSubstitutor(context.variables)
            probe_substituted = self._substitute_probe(probe, substitutor)

            if probe_substituted.type == "rest":
                request_params = self.request_builder.build_rest_request(
                    endpoint=probe_substituted.endpoint,
                    method=probe_substituted.method,
                    headers=probe_substituted.headers,
                    body=probe_substituted.body,
                )
            else:
                request_params = self.request_builder.build_graphql_request(
                    endpoint=probe_substituted.endpoint,
                    query=probe_substituted.query,
                    variables=probe_substituted.variables,
                    headers=probe_substituted.headers,
                )

            # Print "starting" line before the HTTP call so the user sees
            # the probe name immediately, not only after the response arrives
            if not in_group:
                _println(f"  → {probe.name}")
            else:
                _println(f"    → {probe.name}")

            response = self.http_client.execute(
                request_params,
                timeout=probe.timeout,
                retry=probe.retry,
                debug=probe.debug,
                verify=probe_substituted.verify,
            )

            errors = []
            validation_spec_dict = None
            if hasattr(context, 'validation_overrides') and probe.name in context.validation_overrides:
                override_raw = context.validation_overrides[probe.name]
                validation_spec_dict = substitutor.substitute(override_raw)
            elif probe_substituted.validation:
                validation_spec_dict = self._validation_to_dict(probe_substituted.validation, substitutor)

            if validation_spec_dict is not None:
                errors = self.validation_engine.validate(probe.name, response, validation_spec_dict)

            if probe_substituted.output:
                self.output_capture.capture(response, probe_substituted.output, context)

            # Print result line immediately after execution completes
            if len(errors) == 0:
                if in_group:
                    _println(f"    ✓ {probe.name}")
                else:
                    _println(f"    ✓ Passed")
            else:
                if in_group:
                    _println(f"    ✗ {probe.name} - Failed ({len(errors)} error(s))")
                else:
                    _println(f"    ✗ Failed ({len(errors)} error(s))")

            return ProbeResult(
                probe_name=probe.name,
                success=len(errors) == 0,
                errors=errors,
                endpoint=probe_substituted.endpoint,
                response_time_ms=getattr(response, 'elapsed_ms', None),
            )

        except ValueError as e:
            if in_group:
                _println(f"    ⊗ {probe.name} - Skipped: {e}")
            else:
                _println(f"    ⊗ Skipped: {e}")
            return ProbeResult(
                probe_name=probe.name,
                success=False,
                skipped=True,
                skip_reason=str(e),
                endpoint=probe.endpoint,
            )

        except Exception as e:
            if in_group:
                _println(f"    ✗ {probe.name} - Failed: {str(e)[:100]}")
            else:
                _println(f"    ✗ Failed: {str(e)[:100]}")

            from ..validation.base import ValidationError

            try:
                substitutor = VariableSubstitutor(context.variables)
                endpoint = substitutor.substitute(probe.endpoint)
            except Exception:
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
                    message=str(e),
                )],
                endpoint=endpoint,
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _should_ignore(self, item: Union[Probe, Group], context: ExecutionContext) -> bool:
        """Check if probe or group should be ignored."""
        ignore_value = item.ignore

        if ignore_value is None:
            return False

        if isinstance(ignore_value, bool):
            return ignore_value

        if isinstance(ignore_value, str):
            # Substitute ${VAR} first so both plain values and expressions work correctly
            substitutor = VariableSubstitutor(context.variables)
            try:
                ignore_value = substitutor.substitute(ignore_value)
            except ValueError:
                return False  # undefined variable — don't ignore

            if self.expression_evaluator.is_expression(ignore_value):
                return self.expression_evaluator.evaluate(ignore_value, context.variables)

            if isinstance(ignore_value, str):
                return ignore_value.lower() in ('true', '1', 'yes', 'on')
            return bool(ignore_value)

        if isinstance(ignore_value, int):
            return bool(ignore_value)

        return False

    def _substitute_probe(self, probe: Probe, substitutor: VariableSubstitutor) -> Probe:
        """Substitute variables in probe definition."""
        return Probe(
            name=probe.name,
            type=probe.type,
            endpoint=substitutor.substitute(probe.endpoint),
            method=probe.method,
            headers=substitutor.substitute(probe.headers) if probe.headers else None,
            body=substitutor.substitute(probe.body) if probe.body else None,
            query=substitutor.substitute(probe.query) if probe.query else None,
            variables=substitutor.substitute(probe.variables) if probe.variables else None,
            validation=probe.validation,
            output=probe.output,
            delay=probe.delay,
            timeout=probe.timeout,
            retry=probe.retry,
            debug=probe.debug,
            ignore=probe.ignore,
            verify=probe.verify,
        )

    def _validation_to_dict(self, validation: Any, substitutor: VariableSubstitutor) -> Dict[str, Any]:
        """Convert Validation object to dict with variable substitution."""
        result = {}

        if validation.status is not None:
            result['status'] = validation.status

        if validation.headers:
            result['headers'] = substitutor.substitute(validation.headers)

        if validation.body:
            result['body'] = substitutor.substitute(validation.body)

        if validation.response_time is not None:
            result['response_time'] = validation.response_time

        return result
