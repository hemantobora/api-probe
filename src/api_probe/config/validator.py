"""Configuration validator and analyzer."""

import re
from typing import Any, Dict, List, Set, Tuple


class ConfigValidator:
    """Validates configuration and analyzes variable usage."""
    
    VAR_PATTERN = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}')
    
    def __init__(self):
        """Initialize validator."""
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.variables_found: Set[str] = set()
    
    def validate(self, config_dict: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """Validate configuration structure.
        
        Args:
            config_dict: Raw configuration dictionary
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        # Check root structure
        if 'probes' not in config_dict:
            self.errors.append("Missing required 'probes' field")
            return False, self.errors, self.warnings
        
        if not isinstance(config_dict['probes'], list):
            self.errors.append("'probes' must be an array")
            return False, self.errors, self.warnings
        
        if len(config_dict['probes']) == 0:
            self.warnings.append("'probes' array is empty")
        
        # Validate executions if present
        if 'executions' in config_dict:
            self._validate_executions(config_dict['executions'])
        
        # Validate probes
        self._validate_probes(config_dict['probes'])
        
        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings
    
    def extract_variables(self, config_dict: Dict[str, Any]) -> Set[str]:
        """Extract all variables referenced in configuration.
        
        Args:
            config_dict: Raw configuration dictionary
            
        Returns:
            Set of variable names found
        """
        self.variables_found = set()
        
        # Extract from executions block
        if 'executions' in config_dict:
            for execution in config_dict.get('executions', []):
                for var_dict in execution.get('vars', []):
                    for key, value in var_dict.items():
                        if isinstance(value, str):
                            self._extract_vars_from_string(value)
        
        # Extract from probes
        self._extract_vars_from_value(config_dict.get('probes', []))
        
        return self.variables_found
    
    def _validate_executions(self, executions: List[Dict]) -> None:
        """Validate executions block."""
        if not isinstance(executions, list):
            self.errors.append("'executions' must be an array")
            return
        
        for i, execution in enumerate(executions):
            if not isinstance(execution, dict):
                self.errors.append(f"Execution {i+1}: must be an object")
                continue
            
            if 'vars' not in execution:
                self.errors.append(f"Execution {i+1}: missing required 'vars' field")
                continue
            
            if not isinstance(execution['vars'], list):
                self.errors.append(f"Execution {i+1}: 'vars' must be an array")
    
    def _validate_probes(self, probes: List[Any]) -> None:
        """Validate probes array."""
        for i, item in enumerate(probes):
            if not isinstance(item, dict):
                self.errors.append(f"Probe {i+1}: must be an object")
                continue
            
            if 'group' in item:
                self._validate_group(item['group'], i+1)
            else:
                self._validate_probe(item, i+1)
    
    def _validate_group(self, group: Dict, index: int) -> None:
        """Validate a group."""
        if 'probes' not in group:
            self.errors.append(f"Group {index}: missing required 'probes' field")
            return
        
        if not isinstance(group['probes'], list):
            self.errors.append(f"Group {index}: 'probes' must be an array")
            return
        
        if len(group['probes']) == 0:
            self.warnings.append(f"Group {index}: 'probes' array is empty")
        
        for j, probe in enumerate(group['probes']):
            self._validate_probe(probe, f"{index}.{j+1}")
    
    def _validate_probe(self, probe: Dict, index: Any) -> None:
        """Validate a single probe."""
        # Required fields
        if 'name' not in probe:
            self.errors.append(f"Probe {index}: missing required 'name' field")
        
        if 'type' not in probe:
            self.errors.append(f"Probe {index}: missing required 'type' field")
        elif probe['type'] not in ['rest', 'graphql']:
            self.errors.append(f"Probe {index}: 'type' must be 'rest' or 'graphql'")
        
        if 'endpoint' not in probe:
            self.errors.append(f"Probe {index}: missing required 'endpoint' field")
        
        # Type-specific validation
        if probe.get('type') == 'graphql':
            if 'query' not in probe:
                self.errors.append(f"Probe {index}: GraphQL probe must have 'query' field")
        
        # REST with body requires Content-Type
        if probe.get('type') == 'rest' and 'body' in probe:
            headers = probe.get('headers', {})
            if not any(k.lower() == 'content-type' for k in headers.keys()):
                self.errors.append(
                    f"Probe {index}: REST probe with body must have Content-Type header"
                )
        
        # Validate delay if present
        if 'delay' in probe:
            delay = probe['delay']
            if not isinstance(delay, (int, float)):
                self.errors.append(f"Probe {index}: 'delay' must be a number")
            elif delay < 0:
                self.warnings.append(f"Probe {index}: negative delay will be ignored")
    
    def _extract_vars_from_value(self, value: Any) -> None:
        """Recursively extract variables from any value."""
        if isinstance(value, str):
            self._extract_vars_from_string(value)
        elif isinstance(value, dict):
            for v in value.values():
                self._extract_vars_from_value(v)
        elif isinstance(value, list):
            for item in value:
                self._extract_vars_from_value(item)
    
    def _extract_vars_from_string(self, text: str) -> None:
        """Extract variable names from a string."""
        for match in self.VAR_PATTERN.finditer(text):
            var_name = match.group(1)
            self.variables_found.add(var_name)
