"""Type validator - asserts field types."""

from typing import Any, Dict

from .base import Validator, ValidationError


class TypeValidator(Validator):
    """Validates that fields have expected types."""
    
    # Map config type names to Python type checks
    TYPE_CHECKS = {
        'string': lambda x: isinstance(x, str),
        'integer': lambda x: isinstance(x, int) and not isinstance(x, bool),
        'number': lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
        'boolean': lambda x: isinstance(x, bool),
        'array': lambda x: isinstance(x, list),
        'object': lambda x: isinstance(x, dict),
        'null': lambda x: x is None,
        'None': lambda x: x is None,
    }
    
    def __init__(self, extractor):
        """Initialize with path extractor.
        
        Args:
            extractor: PathExtractor instance for value extraction
        """
        self.extractor = extractor
    
    def validate(self, test_name: str, response: Any, type_specs: Dict[str, str]) -> list[ValidationError]:
        """Validate that fields have expected types.
        
        Args:
            test_name: Name of the test
            response: HTTP response object
            type_specs: Dict mapping paths to expected type names
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        for path, expected_type in type_specs.items():
            # Validate type name
            if expected_type not in self.TYPE_CHECKS:
                errors.append(ValidationError(
                    test_name=test_name,
                    validator="type",
                    field=path,
                    expected=expected_type,
                    actual="<invalid type>",
                    message=f"Unknown type '{expected_type}'. Valid types: {', '.join(self.TYPE_CHECKS.keys())}"
                ))
                continue
            
            try:
                actual = self.extractor.extract(response, path)
                
                # Check type
                type_check = self.TYPE_CHECKS[expected_type]
                if not type_check(actual):
                    actual_type = self._get_type_name(actual)
                    errors.append(ValidationError(
                        test_name=test_name,
                        validator="type",
                        field=path,
                        expected=expected_type,
                        actual=actual_type,
                        message=f"Field '{path}': expected type '{expected_type}', got '{actual_type}'"
                    ))
            except (KeyError, IndexError, ValueError) as e:
                errors.append(ValidationError(
                    test_name=test_name,
                    validator="type",
                    field=path,
                    expected=expected_type,
                    actual="<field absent>",
                    message=f"Field '{path}' not found in response"
                ))
        
        return errors
    
    def _get_type_name(self, value: Any) -> str:
        """Get type name for a value.
        
        Args:
            value: Value to check
            
        Returns:
            Type name string
        """
        if value is None:
            return 'null'
        elif isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'number'
        elif isinstance(value, str):
            return 'string'
        elif isinstance(value, list):
            return 'array'
        elif isinstance(value, dict):
            return 'object'
        else:
            return type(value).__name__
