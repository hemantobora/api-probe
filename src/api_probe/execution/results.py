"""Result models for probe execution."""

from dataclasses import dataclass, field
from typing import List, Optional

from ..validation.base import ValidationError


@dataclass
class ProbeResult:
    """Result of executing a single probe."""
    probe_name: str
    success: bool
    errors: List[ValidationError] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""
    endpoint: Optional[str] = None  # Parsed endpoint (after variable substitution)


@dataclass
class RunResult:
    """Result of a single execution run (one context)."""
    run_index: int
    run_name: str = ""  # Name of the execution (from executions block or generated)
    probe_results: List[ProbeResult] = field(default_factory=list)
    
    @property
    def success(self) -> bool:
        """Check if all probes in this run succeeded."""
        return all(p.success for p in self.probe_results)
    
    @property
    def failed_probes(self) -> List[ProbeResult]:
        """Get list of failed probes."""
        return [p for p in self.probe_results if not p.success and not p.skipped]


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
    def total_probes(self) -> int:
        """Total number of probes across all runs."""
        return sum(len(r.probe_results) for r in self.run_results)
    
    @property
    def failed_probes(self) -> int:
        """Total number of failed probes across all runs."""
        return sum(len(r.failed_probes) for r in self.run_results)
