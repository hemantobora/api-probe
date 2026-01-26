"""Variable substitution engine."""

import os
import re
from typing import Any, Dict


class VariableSubstitutor:
    """Handles ${VAR} substitution in strings."""
    
    PATTERN = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}')
    
    def __init__(self, variables: Dict[str, str]):
        """Initialize with variable context.
        
        Args:
            variables: Available variables for substitution
        """
        self.variables = variables
    
    def substitute(self, value: Any) -> Any:
        """Recursively substitute variables in value.
        
        Args:
            value: Value to process (str, dict, list, or primitive)
            
        Returns:
            Value with variables substituted
            
        Raises:
            ValueError: If variable is undefined
        """
        if isinstance(value, str):
            return self._substitute_string(value)
        elif isinstance(value, dict):
            return {k: self.substitute(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.substitute(item) for item in value]
        else:
            return value
    
    def _substitute_string(self, text: str) -> str:
        """Substitute variables in a string.
        
        Args:
            text: String containing ${VAR} patterns
            
        Returns:
            String with variables replaced (always returns string)
            
        Raises:
            ValueError: If variable is undefined
        """
        def replacer(match):
            var_name = match.group(1)
            if var_name not in self.variables:
                raise ValueError(f"Undefined variable: ${{{var_name}}}")
            return self.variables[var_name]
        
        return self.PATTERN.sub(replacer, text)


def get_env_variables() -> Dict[str, str]:
    """Get all environment variables as a dictionary.
    
    Returns:
        Dictionary of environment variables
    """
    return dict(os.environ)
