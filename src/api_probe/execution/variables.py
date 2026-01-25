"""Variable substitution engine."""

import os
import re
from typing import Any, Dict, List


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
            String with variables replaced
            
        Raises:
            ValueError: If variable is undefined
        """
        def replacer(match):
            var_name = match.group(1)
            if var_name not in self.variables:
                raise ValueError(f"Undefined variable: ${{{var_name}}}")
            return self.variables[var_name]
        
        return self.PATTERN.sub(replacer, text)


def parse_env_vars() -> Dict[str, List[str]]:
    """Parse environment variables, detecting multi-value vars.
    
    Returns:
        Dictionary mapping var names to list of values
    """
    result = {}
    
    for key, value in os.environ.items():
        # Split by comma (simple approach - no quote handling yet)
        values = [v.strip() for v in value.split(',')]
        result[key] = values
    
    return result


def create_execution_contexts(env_vars: Dict[str, List[str]]) -> List[Dict[str, str]]:
    """Create execution contexts with position-based pairing.
    
    Args:
        env_vars: Environment variables with multi-value support
        
    Returns:
        List of variable dictionaries (one per run)
    """
    # Handle empty env vars
    if not env_vars:
        return [{}]
    
    # Find max value count
    max_count = max(len(values) for values in env_vars.values())
    
    # Create contexts with position-based pairing
    contexts = []
    for i in range(max_count):
        context = {}
        for key, values in env_vars.items():
            # Use index or last value if out of range
            value_index = min(i, len(values) - 1)
            context[key] = values[value_index]
        contexts.append(context)
    
    return contexts
