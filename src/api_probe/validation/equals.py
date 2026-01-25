"""Equals validator - asserts exact values."""

from typing import Any, Dict

from .base import Validator, ValidationError


class EqualsValidator(Validator):
    """Validates that fields equal expected values."""
    
    def __init__(self, extractor):
        """Initialize with path extractor.
        
        Args:
            extractor: PathExtractor instance for value extraction
        """
        self.extractor = extractor
    
    def validate(self, test_name: str, response: Any, expectations: Dict[str, Any]) -> list[ValidationError]:
        """Validate that fields equal expected values.
        
        Args:
            test_name: Name of the test
            response: HTTP response object
            expectations: Dict mapping paths to expected values
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        for path, expected in expectations.items():
            try:
                actual = self.extractor.extract(response, path)
                
                # Type-strict equality
                if actual != expected or type(actual) != type(expected):
                    errors.append(ValidationError(
                        test_name=test_name,
                        validator="equals",
                        field=path,
                        expected=expected,
                        actual=actual,
                        message=f"Field '{path}': expected {expected!r}, got {actual!r}"
                    ))
            except (KeyError, IndexError, ValueError) as e:
                errors.append(ValidationError(
                    test_name=test_name,
                    validator="equals",
                    field=path,
                    expected=expected,
                    actual="<field absent>",
                    message=f"Field '{path}' not found in response"
                ))
        
        return errors
