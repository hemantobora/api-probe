"""Reporter for probe results - silent success, verbose failure."""

from ..execution.results import ExecutionResult, RunResult, ProbeResult


class Reporter:
    """Reports probe execution results."""
    
    def report(self, result: ExecutionResult) -> None:
        """Report execution results.
        
        Silent if all passed, verbose if any failed.
        
        Args:
            result: Execution result to report
        """
        if result.success:
            # Silent success - no output
            return
        
        # Verbose failure reporting
        self._report_failures(result)
    
    def _report_failures(self, result: ExecutionResult) -> None:
        """Report failures in detail.
        
        Args:
            result: Execution result with failures
        """
        import sys
        
        print("=" * 60, file=sys.stderr)
        print("VALIDATION FAILURES", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(file=sys.stderr)
        
        # Report each failed run
        for run_result in result.run_results:
            if not run_result.success:
                self._report_run_failures(run_result)
        
        # Summary
        print("=" * 60, file=sys.stderr)
        print("SUMMARY", file=sys.stderr)
        print(f"  Total Runs: {result.total_runs}", file=sys.stderr)
        print(f"  Failed Runs: {result.failed_runs}/{result.total_runs}", file=sys.stderr)
        print(f"  Total Probes: {result.total_probes}", file=sys.stderr)
        print(f"  Failed Probes: {result.failed_probes}/{result.total_probes}", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
    
    def _report_run_failures(self, run_result: RunResult) -> None:
        """Report failures for a single run.
        
        Args:
            run_result: Run result with failures
        """
        import sys
        
        # Show run name if available, otherwise show index
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
        """Report failure for a single probe.
        
        Args:
            probe_result: Probe result with failures
        """
        import sys
        
        print(f"Probe: {probe_result.probe_name}", file=sys.stderr)
        
        # Show endpoint (parsed, after variable substitution)
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
