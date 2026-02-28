"""Variable substitution engine."""

import os
import re
from typing import Any, Dict


class VariableSubstitutor:
    """Handles ${VAR} substitution in strings and typed values."""

    PATTERN = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}')

    def __init__(self, variables: Dict[str, Any]):
        """Initialize with variable context.

        Args:
            variables: Available variables for substitution
        """
        self.variables = variables

    def substitute(self, value: Any) -> Any:
        """Recursively substitute variables in value.

        Handles TypedValue markers produced by !int / !bool / !float / !str
        YAML tags: substitutes the inner string first, then coerces to the
        target type (falling back to string on failure).

        Args:
            value: Value to process (TypedValue, str, dict, list, or primitive)

        Returns:
            Value with variables substituted (and coerced when tagged)

        Raises:
            ValueError: If a ${VAR} reference is undefined
        """
        # Import here to avoid a circular import at module load time
        from ..config.loader import TypedValue

        if isinstance(value, TypedValue):
            substituted = self._substitute_string(value.raw)
            return value.coerce(substituted)

        if isinstance(value, str):
            return self._substitute_string(value)

        if isinstance(value, dict):
            return {k: self.substitute(v) for k, v in value.items()}

        if isinstance(value, list):
            return [self.substitute(item) for item in value]

        # int, float, bool, None — return as-is
        return value

    def _substitute_string(self, text: str) -> str:
        """Substitute ${VAR} patterns in a string.

        Args:
            text: String containing ${VAR} patterns

        Returns:
            String with all variables replaced

        Raises:
            ValueError: If a variable is undefined
        """
        def replacer(match):
            var_name = match.group(1)
            if var_name not in self.variables:
                raise ValueError(f"Undefined variable: ${{{var_name}}}")
            # Variables stored in context are always strings; coerce just in case
            return str(self.variables[var_name])

        return self.PATTERN.sub(replacer, text)


def get_env_variables() -> Dict[str, str]:
    """Get all environment variables as a dictionary.

    Returns:
        Dictionary of environment variables
    """
    return dict(os.environ)
