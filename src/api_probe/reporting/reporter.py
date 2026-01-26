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
        print("=" * 60)
        print("VALIDATION FAILURES")
        print("=" * 60)
        print()
        
        # Report each failed run
        for run_result in result.run_results:
            if not run_result.success:
                self._report_run_failures(run_result)
        
        # Summary
        print("=" * 60)
        print("SUMMARY")
        print(f"  Total Runs: {result.total_runs}")
        print(f"  Failed Runs: {result.failed_runs}/{result.total_runs}")
        print(f"  Total Probes: {result.total_probes}")
        print(f"  Failed Probes: {result.failed_probes}/{result.total_probes}")
        print("=" * 60)
    
    def _report_run_failures(self, run_result: RunResult) -> None:
        """Report failures for a single run.
        
        Args:
            run_result: Run result with failures
        """
        # Show run name if available, otherwise show index
        if run_result.run_name:
            print(f"{run_result.run_name}")
        else:
            print(f"Run {run_result.run_index + 1}")
        print("-" * 60)
        
        for probe_result in run_result.probe_results:
            if not probe_result.success:
                self._report_probe_failure(probe_result)
        
        print()
    
    def _report_probe_failure(self, probe_result: ProbeResult) -> None:
        """Report failure for a single probe.
        
        Args:
            probe_result: Probe result with failures
        """
        print(f"Probe: {probe_result.probe_name}")
        
        # Show endpoint (parsed, after variable substitution)
        if probe_result.endpoint:
            print(f"  Endpoint: {probe_result.endpoint}")
        
        if probe_result.skipped:
            print(f"  ✗ Probe skipped")
            print(f"    Reason: {probe_result.skip_reason}")
        else:
            for error in probe_result.errors:
                print(f"  ✗ {error.message}")
                if error.validator != "execution":
                    print(f"    Field: {error.field}")
                    print(f"    Expected: {error.expected}")
                    print(f"    Got: {error.actual}")
        
        print()
