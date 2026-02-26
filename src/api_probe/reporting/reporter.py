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
        print("=" * 60, file=sys.stderr)
        print("VALIDATION PASSED", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(file=sys.stderr)

        for run_result in result.run_results:
            self._report_run_success(run_result)

        self._print_summary(result)

    def _report_run_success(self, run_result: RunResult) -> None:
        """Print passed probes for a single run."""
        if run_result.run_name:
            print(f"{run_result.run_name}", file=sys.stderr)
        else:
            print(f"Run {run_result.run_index + 1}", file=sys.stderr)
        print("-" * 60, file=sys.stderr)

        for probe_result in run_result.probe_results:
            self._report_probe_success(probe_result)

        print(file=sys.stderr)

    def _report_probe_success(self, probe_result: ProbeResult) -> None:
        """Print a single passed probe."""
        print(f"Probe: {probe_result.probe_name}", file=sys.stderr)

        if probe_result.endpoint:
            print(f"  Endpoint: {probe_result.endpoint}", file=sys.stderr)

        if probe_result.skipped:
            print(f"  ⊗ Skipped: {probe_result.skip_reason}", file=sys.stderr)
        else:
            print(f"  ✓ Passed", file=sys.stderr)

        print(file=sys.stderr)

    # ------------------------------------------------------------------
    # Failure reporting
    # ------------------------------------------------------------------

    def _report_failures(self, result: ExecutionResult) -> None:
        """Report failures in detail."""
        print("=" * 60, file=sys.stderr)
        print("VALIDATION FAILURES", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(file=sys.stderr)

        for run_result in result.run_results:
            if not run_result.success:
                self._report_run_failures(run_result)

        self._print_summary(result)

    def _report_run_failures(self, run_result: RunResult) -> None:
        """Report failures for a single run."""
        if run_result.run_name:
            print(f"{run_result.run_name}", file=sys.stderr)
        else:
            print(f"Run {run_result.run_index + 1}", file=sys.stderr)
        print("-" * 60, file=sys.stderr)

        for probe_result in run_result.probe_results:
            if not probe_result.success:
                self._report_probe_failure(probe_result)

        print(file=sys.stderr)

    def _report_probe_failure(self, probe_result: ProbeResult) -> None:
        """Report failure for a single probe."""
        print(f"Probe: {probe_result.probe_name}", file=sys.stderr)

        if probe_result.endpoint:
            print(f"  Endpoint: {probe_result.endpoint}", file=sys.stderr)

        if probe_result.skipped:
            print(f"  ✗ Probe skipped", file=sys.stderr)
            print(f"    Reason: {probe_result.skip_reason}", file=sys.stderr)
        else:
            for error in probe_result.errors:
                print(f"  ✗ {error.message}", file=sys.stderr)
                if error.validator != "execution":
                    print(f"    Field: {error.field}", file=sys.stderr)
                    print(f"    Expected: {error.expected}", file=sys.stderr)
                    print(f"    Got: {error.actual}", file=sys.stderr)

        print(file=sys.stderr)

    # ------------------------------------------------------------------
    # Shared summary
    # ------------------------------------------------------------------

    def _print_summary(self, result: ExecutionResult) -> None:
        """Print the final counts summary."""
        passed_runs   = result.total_runs  - result.failed_runs
        passed_probes = result.total_probes - result.failed_probes

        print("=" * 60, file=sys.stderr)
        print("SUMMARY", file=sys.stderr)
        print(f"  Runs:   {passed_runs}/{result.total_runs} passed", file=sys.stderr)
        print(f"  Probes: {passed_probes}/{result.total_probes} passed", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
