"""Contains validator - asserts substring or array element presence."""

from typing import Any, Dict

from .base import Validator, ValidationError


class ContainsValidator(Validator):
    """Validates that fields contain expected values."""
    
    def __init__(self, extractor):
        """Initialize with path extractor.
        
        Args:
            extractor: PathExtractor instance for value extraction
        """
        self.extractor = extractor
    
    def validate(self, test_name: str, response: Any, expectations: Dict[str, Any]) -> list[ValidationError]:
        """Validate that fields contain expected values.
        
        For strings: substring match (case-sensitive)
        For arrays: element match (exact equality)
        
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
                
                # String: substring match
                if isinstance(actual, str):
                    if not isinstance(expected, str):
                        errors.append(ValidationError(
                            test_name=test_name,
                            validator="contains",
                            field=path,
                            expected=expected,
                            actual=actual,
                            message=f"Field '{path}' is a string, but expected value is not a string"
                        ))
                    elif expected not in actual:
                        errors.append(ValidationError(
                            test_name=test_name,
                            validator="contains",
                            field=path,
                            expected=f"substring: {expected!r}",
                            actual=actual,
                            message=f"Field '{path}' does not contain substring {expected!r}"
                        ))
                
                # Array: element match
                elif isinstance(actual, list):
                    if expected not in actual:
                        errors.append(ValidationError(
                            test_name=test_name,
                            validator="contains",
                            field=path,
                            expected=f"element: {expected!r}",
                            actual=actual,
                            message=f"Field '{path}' does not contain element {expected!r}"
                        ))
                
                # Other types: not supported
                else:
                    errors.append(ValidationError(
                        test_name=test_name,
                        validator="contains",
                        field=path,
                        expected=expected,
                        actual=f"<type: {type(actual).__name__}>",
                        message=f"Field '{path}' is {type(actual).__name__}, 'contains' only works on strings and arrays"
                    ))
                    
            except (KeyError, IndexError, ValueError) as e:
                errors.append(ValidationError(
                    test_name=test_name,
                    validator="contains",
                    field=path,
                    expected=expected,
                    actual="<field absent>",
                    message=f"Field '{path}' not found in response"
                ))
        
        return errors
