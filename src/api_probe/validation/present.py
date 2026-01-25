"""Present validator - asserts fields exist."""

from typing import Any, List

from .base import Validator, ValidationError


class PresentValidator(Validator):
    """Validates that specified fields are present."""
    
    def __init__(self, extractor):
        """Initialize with path extractor.
        
        Args:
            extractor: PathExtractor instance for value extraction
        """
        self.extractor = extractor
    
    def validate(self, test_name: str, response: Any, paths: List[str]) -> list[ValidationError]:
        """Validate that all paths exist in response.
        
        Args:
            test_name: Name of the test
            response: HTTP response object
            paths: List of paths that must exist
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        for path in paths:
            try:
                value = self.extractor.extract(response, path)
                # If extraction succeeded, field exists (even if None)
            except (KeyError, IndexError, ValueError) as e:
                errors.append(ValidationError(
                    test_name=test_name,
                    validator="present",
                    field=path,
                    expected="<field present>",
                    actual="<field absent>",
                    message=f"Field '{path}' is absent in response"
                ))
        
        return errors
