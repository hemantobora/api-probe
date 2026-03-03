"""Reporter for probe results - success summary and verbose failure."""

import sys
from ..execution.results import ExecutionResult, RunResult, ProbeResult


class Reporter:
    """Reports probe execution results."""

    def report(self, result: ExecutionResult) -> None:
        """Report execution results.

        Always prints a summary. Verbose failure details printed on failure.

        Args:
            result: Execution result to report
        """
        if result.success:
            self._report_success(result)
        else:
            self._report_failures(result)

    # ------------------------------------------------------------------
    # Success reporting
    # ------------------------------------------------------------------

    def _report_success(self, result: ExecutionResult) -> None:
        """Print a success summary mirroring the failure report layout."""
        has_multiple = len(result.run_results) > 1
        print("=" * 60, file=sys.stderr)
        if has_multiple:
            print("EXECUTION COMPLETE \u2014 FULL REPORT", file=sys.stderr)
            print(file=sys.stderr)
        print("VALIDATION PASSED", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(file=sys.stderr)

        for run_result in result.run_results:
            self._report_run_success(run_result)

        self._print_summary(result)

    def _report_run_success(self, run_result: RunResult) -> None:
        """Print passed probes for a single run."""
        run_name = run_result.run_name or f"Run {run_result.run_index + 1}"
        print(f"\u25b6 Executed: {run_name}", file=sys.stderr)
        print("-" * 60, file=sys.stderr)

        for probe_result in run_result.probe_results:
            self._report_probe_success(probe_result)

        print(file=sys.stderr)

    def _report_probe_success(self, probe_result: ProbeResult) -> None:
        """Print a single passed probe."""
        print(f"Probe: {probe_result.probe_name}", file=sys.stderr)

        if probe_result.endpoint:
            print(f"  Endpoint: {probe_result.endpoint}", file=sys.stderr)
        if probe_result.response_time_ms is not None:
            print(f"  Response time: {probe_result.response_time_ms}ms", file=sys.stderr)

        if probe_result.skipped:
            print(f"  ⊗ Skipped: {probe_result.skip_reason}", file=sys.stderr)
        elif probe_result.validation_state == "validation_skipped":
            print(f"  ✓ Passed (validation skipped)", file=sys.stderr)
        elif probe_result.validation_state == "no_validation":
            print(f"  ✓ Passed (no validation)", file=sys.stderr)
        else:
            print(f"  ✓ Passed", file=sys.stderr)

        print(file=sys.stderr)

    # ------------------------------------------------------------------
    # Failure reporting
    # ------------------------------------------------------------------

    def _report_failures(self, result: ExecutionResult) -> None:
        """Report failures in detail."""
        has_multiple = len(result.run_results) > 1
        print("=" * 60, file=sys.stderr)
        if has_multiple:
            print("EXECUTION COMPLETE \u2014 FULL REPORT", file=sys.stderr)
            print(file=sys.stderr)
        print("VALIDATION FAILURES", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(file=sys.stderr)

        for run_result in result.run_results:
            self._report_run_failures(run_result)

        self._print_summary(result)

    def _report_run_failures(self, run_result: RunResult) -> None:
        """Report failures (and any skipped probes) for a single run."""
        run_name = run_result.run_name or f"Run {run_result.run_index + 1}"
        print(f"\u25b6 Executed: {run_name}", file=sys.stderr)
        print("-" * 60, file=sys.stderr)

        for probe_result in run_result.probe_results:
            if probe_result.skipped:
                self._report_probe_skipped(probe_result)
            elif not probe_result.success:
                self._report_probe_failure(probe_result)
            else:
                self._report_probe_success(probe_result)

        print(file=sys.stderr)

    def _report_probe_failure(self, probe_result: ProbeResult) -> None:
        """Report failure for a single probe."""
        print(f"Probe: {probe_result.probe_name}", file=sys.stderr)

        if probe_result.endpoint:
            print(f"  Endpoint: {probe_result.endpoint}", file=sys.stderr)
        if probe_result.response_time_ms is not None:
            print(f"  Response time: {probe_result.response_time_ms}ms", file=sys.stderr)

        for error in probe_result.errors:
            print(f"  ✗ {error.message}", file=sys.stderr)
            if error.validator != "execution":
                print(f"    Field: {error.field}", file=sys.stderr)
                print(f"    Expected: {error.expected}", file=sys.stderr)
                print(f"    Got: {error.actual}", file=sys.stderr)

        print(file=sys.stderr)

    def _report_probe_skipped(self, probe_result: ProbeResult) -> None:
        """Report a skipped probe."""
        print(f"Probe: {probe_result.probe_name}", file=sys.stderr)

        if probe_result.endpoint:
            print(f"  Endpoint: {probe_result.endpoint}", file=sys.stderr)

        print(f"  ⊗ Skipped: {probe_result.skip_reason}", file=sys.stderr)
        print(file=sys.stderr)

    # ------------------------------------------------------------------
    # Shared summary
    # ------------------------------------------------------------------

    def _print_summary(self, result: ExecutionResult) -> None:
        """Print the final counts summary with per-run breakdown."""
        passed_runs = result.total_runs - result.failed_runs

        print("=" * 60, file=sys.stderr)
        print("SUMMARY", file=sys.stderr)
        print(f"  Runs:   {passed_runs}/{result.total_runs} passed", file=sys.stderr)

        for run_result in result.run_results:
            run_name = run_result.run_name or f"Run {run_result.run_index + 1}"
            total = len(run_result.probe_results)
            skipped = len(run_result.skipped_probes)
            failed = len(run_result.failed_probes)
            passed = total - failed - skipped
            run_status = "✓" if run_result.success else "✗"
            line = f"    {run_status} {run_name}: {passed}/{total} passed"
            if skipped > 0:
                line += f", {skipped} skipped"
            print(line, file=sys.stderr)

        print("=" * 60, file=sys.stderr)
