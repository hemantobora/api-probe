"""Result models for test execution."""

from dataclasses import dataclass, field
from typing import List, Optional

from ..validation.base import ValidationError


@dataclass
class TestResult:
    """Result of executing a single test."""
    test_name: str
    success: bool
    errors: List[ValidationError] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""
    endpoint: Optional[str] = None  # Parsed endpoint (after variable substitution)


@dataclass
class RunResult:
    """Result of a single execution run (one context)."""
    run_index: int
    test_results: List[TestResult] = field(default_factory=list)
    
    @property
    def success(self) -> bool:
        """Check if all tests in this run succeeded."""
        return all(t.success for t in self.test_results)
    
    @property
    def failed_tests(self) -> List[TestResult]:
        """Get list of failed tests."""
        return [t for t in self.test_results if not t.success and not t.skipped]


@dataclass
class ExecutionResult:
    """Overall execution result across all runs."""
    run_results: List[RunResult] = field(default_factory=list)
    
    @property
    def success(self) -> bool:
        """Check if all runs succeeded."""
        return all(r.success for r in self.run_results)
    
    @property
    def total_runs(self) -> int:
        """Total number of runs."""
        return len(self.run_results)
    
    @property
    def failed_runs(self) -> int:
        """Number of runs with failures."""
        return sum(1 for r in self.run_results if not r.success)
    
    @property
    def total_tests(self) -> int:
        """Total number of tests across all runs."""
        return sum(len(r.test_results) for r in self.run_results)
    
    @property
    def failed_tests(self) -> int:
        """Total number of failed tests across all runs."""
        return sum(len(r.failed_tests) for r in self.run_results)
