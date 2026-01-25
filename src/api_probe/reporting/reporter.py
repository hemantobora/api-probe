"""Reporter for test results - silent success, verbose failure."""

from ..execution.results import ExecutionResult, RunResult, TestResult


class Reporter:
    """Reports test execution results."""
    
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
        print(f"  Total Tests: {result.total_tests}")
        print(f"  Failed Tests: {result.failed_tests}/{result.total_tests}")
        print("=" * 60)
    
    def _report_run_failures(self, run_result: RunResult) -> None:
        """Report failures for a single run.
        
        Args:
            run_result: Run result with failures
        """
        print(f"Run {run_result.run_index + 1}")
        print("-" * 60)
        
        for test_result in run_result.test_results:
            if not test_result.success:
                self._report_test_failure(test_result)
        
        print()
    
    def _report_test_failure(self, test_result: TestResult) -> None:
        """Report failure for a single test.
        
        Args:
            test_result: Test result with failures
        """
        print(f"Test: {test_result.test_name}")
        
        # Show endpoint (parsed, after variable substitution)
        if test_result.endpoint:
            print(f"  Endpoint: {test_result.endpoint}")
        
        if test_result.skipped:
            print(f"  ✗ Test skipped")
            print(f"    Reason: {test_result.skip_reason}")
        else:
            for error in test_result.errors:
                print(f"  ✗ {error.message}")
                if error.validator != "execution":
                    print(f"    Field: {error.field}")
                    print(f"    Expected: {error.expected}")
                    print(f"    Got: {error.actual}")
        
        print()
