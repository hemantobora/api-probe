"""Main probe executor - orchestrates entire execution flow."""

import io
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

        Multiple executions run concurrently. Progress output per execution
        is buffered and flushed atomically in run-index order so lines never
        interleave.

        Args:
            config: Parsed configuration

        Returns:
            Execution result with all probe results
        """
        execution_result = ExecutionResult()

        if config.executions:
            self._execute_concurrent(config, execution_result)
        else:
            # Single run with env vars - no concurrency needed
            env_vars = get_env_variables()
            context = ExecutionContext(env_vars)

            buf = io.StringIO()
            buf.write(f"\n▶ Executing probes...\n")
            buf.write("=" * 60 + "\n")

            run_result = self._execute_run(config, context, 0, buf)
            execution_result.run_results.append(run_result)

            sys.stderr.write(buf.getvalue())

        return execution_result

    def _execute_concurrent(self, config: Config, execution_result: ExecutionResult) -> None:
        """Run all executions concurrently, flush output in order.

        Each execution writes progress into its own StringIO buffer.
        Results arrive via a dict keyed by run_index; the main thread
        flushes them in ascending order so output is never interleaved.

        Args:
            config: Parsed configuration
            execution_result: Accumulator for RunResults (mutated in place)
        """
        num = len(config.executions)

        # Pre-build contexts so name generation is deterministic
        contexts = [
            (i, self._create_context_from_execution(ex))
            for i, ex in enumerate(config.executions)
        ]

        # Collect (run_index, buffer, run_result) from each thread
        completed: Dict[int, tuple] = {}
        lock = threading.Lock()

        def run_one(run_index: int, context: ExecutionContext):
            buf = io.StringIO()
            buf.write(f"\n▶ Executing: {context.execution_name}\n")
            buf.write("=" * 60 + "\n")
            run_result = self._execute_run(config, context, run_index, buf)
            with lock:
                completed[run_index] = (buf.getvalue(), run_result)

        with ThreadPoolExecutor(max_workers=num) as pool:
            futures = [pool.submit(run_one, i, ctx) for i, ctx in contexts]
            # Wait for all futures; exceptions propagate here
            for f in as_completed(futures):
                f.result()

        # Flush output and collect results in original order
        for i in range(num):
            output_text, run_result = completed[i]
            sys.stderr.write(output_text)
            execution_result.run_results.append(run_result)

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
        buf: io.StringIO,
    ) -> RunResult:
        """Execute all probes in a single run context.

        Args:
            config: Configuration
            context: Execution context with variables
            run_index: Index of this run (for reporting)
            buf: Output buffer - all progress lines written here

        Returns:
            Run result with all probe results
        """
        run_name = getattr(context, 'execution_name', f"Run {run_index + 1}")
        run_result = RunResult(run_index=run_index, run_name=run_name)

        for item in config.probes:
            if isinstance(item, Probe):
                if self._should_ignore(item, context):
                    continue
                probe_result = self._execute_probe(item, context, buf=buf)
                run_result.probe_results.append(probe_result)
            elif isinstance(item, Group):
                if self._should_ignore(item, context):
                    continue
                group_results = self._execute_group(item, context, buf=buf)
                run_result.probe_results.extend(group_results)

        return run_result

    # ------------------------------------------------------------------
    # Group execution (probes within a group run in parallel)
    # ------------------------------------------------------------------

    def _execute_group(
        self,
        group: Group,
        context: ExecutionContext,
        buf: io.StringIO,
    ) -> List[ProbeResult]:
        """Execute probes in a group in parallel, collecting output safely.

        Each probe gets its own sub-buffer; results are appended to buf
        in original probe order after all finish.

        Args:
            group: Group of probes to execute in parallel
            context: Execution context
            buf: Parent output buffer

        Returns:
            List of probe results (order preserved)
        """
        group_name = group.name if group.name else "Parallel Group"
        buf.write(f"  [{group_name} - {len(group.probes)} probe(s)]:\n")

        probes_to_run = [
            p for p in group.probes if not self._should_ignore(p, context)
        ]

        if not probes_to_run:
            return []

        # Each probe writes into its own sub-buffer
        sub_bufs: Dict[int, io.StringIO] = {i: io.StringIO() for i in range(len(probes_to_run))}
        results: Dict[int, ProbeResult] = {}
        lock = threading.Lock()

        def run_probe(idx: int, probe: Probe):
            sub_buf = sub_bufs[idx]
            result = self._execute_probe(probe, context, in_group=True, buf=sub_buf)
            with lock:
                results[idx] = result

        with ThreadPoolExecutor(max_workers=len(probes_to_run)) as pool:
            futures = {pool.submit(run_probe, i, p): i for i, p in enumerate(probes_to_run)}
            for f in as_completed(futures):
                f.result()

        # Flush sub-buffers and collect results in original order
        ordered_results = []
        for i in range(len(probes_to_run)):
            buf.write(sub_bufs[i].getvalue())
            ordered_results.append(results[i])

        return ordered_results

    # ------------------------------------------------------------------
    # Single probe execution
    # ------------------------------------------------------------------

    def _execute_probe(
        self,
        probe: Probe,
        context: ExecutionContext,
        in_group: bool = False,
        buf: io.StringIO = None,
    ) -> ProbeResult:
        """Execute a single probe.

        All progress lines are written to buf (never directly to stderr).

        Args:
            probe: Probe definition
            context: Execution context
            in_group: Whether this probe is part of a parallel group
            buf: Output buffer

        Returns:
            Probe result
        """
        if buf is None:
            buf = io.StringIO()

        try:
            if not in_group:
                buf.write(f"  → {probe.name}\n")

            if probe.delay is not None and probe.delay > 0:
                import time
                if probe.debug:
                    buf.write(f"[DEBUG] Waiting {probe.delay}s...\n")
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

            response = self.http_client.execute(
                request_params,
                timeout=probe.timeout,
                retry=probe.retry,
                debug=probe.debug,
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

            if len(errors) == 0:
                if in_group:
                    buf.write(f"    ✓ {probe.name}\n")
                else:
                    buf.write(f"    ✓ Passed\n")
            else:
                if in_group:
                    buf.write(f"    ✗ {probe.name} - Failed ({len(errors)} error(s))\n")
                else:
                    buf.write(f"    ✗ Failed ({len(errors)} error(s))\n")

            return ProbeResult(
                probe_name=probe.name,
                success=len(errors) == 0,
                errors=errors,
                endpoint=probe_substituted.endpoint,
            )

        except ValueError as e:
            if in_group:
                buf.write(f"    ⊗ {probe.name} - Skipped: {e}\n")
            else:
                buf.write(f"    ⊗ Skipped: {e}\n")
            return ProbeResult(
                probe_name=probe.name,
                success=False,
                skipped=True,
                skip_reason=str(e),
                endpoint=probe.endpoint,
            )

        except Exception as e:
            if in_group:
                buf.write(f"    ✗ {probe.name} - Failed: {str(e)[:100]}\n")
            else:
                buf.write(f"    ✗ Failed: {str(e)[:100]}\n")

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
            if self.expression_evaluator.is_expression(ignore_value):
                return self.expression_evaluator.evaluate(ignore_value, context.variables)

            if ignore_value.startswith("${") and ignore_value.endswith("}"):
                substitutor = VariableSubstitutor(context.variables)
                try:
                    resolved = substitutor.substitute(ignore_value)
                    if isinstance(resolved, str):
                        return resolved.lower() in ('true', '1', 'yes', 'on')
                    return bool(resolved)
                except Exception:
                    return False

            return ignore_value.lower() in ('true', '1', 'yes', 'on')

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
