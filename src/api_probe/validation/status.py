"""Status code validator."""

from typing import Any

from .base import Validator, ValidationError


class StatusValidator(Validator):
    """Validates HTTP status code."""
    
    def validate(self, test_name: str, response: Any, expected_status: int) -> list[ValidationError]:
        """Validate status code matches expected value.
        
        Args:
            test_name: Name of the test
            response: HTTP response object
            expected_status: Expected status code
            
        Returns:
            List of validation errors (empty if valid)
        """
        if response.status_code != expected_status:
            return [ValidationError(
                test_name=test_name,
                validator="status",
                field="status_code",
                expected=expected_status,
                actual=response.status_code,
                message=f"Expected status {expected_status}, got {response.status_code}"
            )]
        
        return []
