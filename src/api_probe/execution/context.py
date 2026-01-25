"""Execution context for a single test run."""

from typing import Any, Dict


class ExecutionContext:
    """Holds variables and state for a single execution run."""
    
    def __init__(self, env_vars: Dict[str, str]):
        """Initialize execution context.
        
        Args:
            env_vars: Initial environment variables for this run
        """
        self.variables: Dict[str, str] = env_vars.copy()
    
    def set_variable(self, name: str, value: Any) -> None:
        """Set a variable (from output capture).
        
        Args:
            name: Variable name
            value: Variable value (will be converted to string)
        """
        self.variables[name] = str(value)
    
    def get_variable(self, name: str) -> str:
        """Get a variable value.
        
        Args:
            name: Variable name
            
        Returns:
            Variable value
            
        Raises:
            KeyError: If variable doesn't exist
        """
        return self.variables[name]
    
    def has_variable(self, name: str) -> bool:
        """Check if variable exists.
        
        Args:
            name: Variable name
            
        Returns:
            True if variable exists
        """
        return name in self.variables
