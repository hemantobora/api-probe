"""Execution context for a single probe run."""

from threading import Lock
from typing import Any, Dict


class ExecutionContext:
    """Holds variables and state for a single execution run.
    
    Thread-safe for concurrent variable capture in parallel groups.
    """
    
    def __init__(self, env_vars: Dict[str, str], validation_overrides: Dict[str, Any] = None):
        """Initialize execution context.
        
        Args:
            env_vars: Initial environment variables for this run
        """
        self.variables: Dict[str, str] = env_vars.copy()
        self._lock = Lock()
        # Per-execution validation overrides keyed by probe name
        self.validation_overrides: Dict[str, Any] = validation_overrides or {}
    
    def set_variable(self, name: str, value: Any) -> None:
        """Set a variable (from output capture).
        
        Thread-safe for concurrent writes from parallel probes.
        
        Args:
            name: Variable name
            value: Variable value (will be converted to string)
        """
        with self._lock:
            self.variables[name] = str(value)
    
    def get_variable(self, name: str) -> str:
        """Get a variable value.
        
        Thread-safe for concurrent reads.
        
        Args:
            name: Variable name
            
        Returns:
            Variable value
            
        Raises:
            KeyError: If variable doesn't exist
        """
        with self._lock:
            return self.variables[name]
    
    def has_variable(self, name: str) -> bool:
        """Check if variable exists.
        
        Thread-safe for concurrent checks.
        
        Args:
            name: Variable name
            
        Returns:
            True if variable exists
        """
        with self._lock:
            return name in self.variables
