"""Absent validator - asserts fields do NOT exist."""

from typing import Any, List

from .base import Validator, ValidationError


class AbsentValidator(Validator):
    """Validates that specified fields are NOT present."""
    
    def __init__(self, extractor):
        """Initialize with path extractor.
        
        Args:
            extractor: PathExtractor instance for value extraction
        """
        self.extractor = extractor
    
    def validate(self, test_name: str, response: Any, paths: List[str]) -> list[ValidationError]:
        """Validate that all paths do NOT exist in response.
        
        Args:
            test_name: Name of the test
            response: HTTP response object
            paths: List of paths that must NOT exist
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        for path in paths:
            try:
                value = self.extractor.extract(response, path)
                # If extraction succeeded, field exists - that's an error
                errors.append(ValidationError(
                    test_name=test_name,
                    validator="absent",
                    field=path,
                    expected="<field absent>",
                    actual=f"<field present: {value}>",
                    message=f"Field '{path}' should not exist but is present"
                ))
            except (KeyError, IndexError, ValueError):
                # Field doesn't exist - that's what we want
                pass
        
        return errors
