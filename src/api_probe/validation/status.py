"""Status code validator."""

from typing import Any, Union

from .base import Validator, ValidationError


class StatusValidator(Validator):
    """Validates HTTP status code."""
    
    def validate(self, test_name: str, response: Any, expected_status: Union[int, str]) -> list[ValidationError]:
        """Validate status code matches expected value.
        
        Args:
            test_name: Name of the test
            response: HTTP response object
            expected_status: Expected status code (int) or pattern (str like "2xx", "3XX")
            
        Returns:
            List of validation errors (empty if valid)
        """
        actual_status = response.status_code
        
        # Handle pattern matching (2xx, 3XX, etc.)
        if isinstance(expected_status, str):
            pattern = expected_status.lower()
            
            # Check if it's a valid pattern (Nxx where N is 1-5)
            if len(pattern) == 3 and pattern[1:] == 'xx' and pattern[0] in '12345':
                expected_range = int(pattern[0]) * 100
                if not (expected_range <= actual_status < expected_range + 100):
                    return [ValidationError(
                        test_name=test_name,
                        validator="status",
                        field="status_code",
                        expected=f"{expected_status} ({expected_range}-{expected_range + 99})",
                        actual=actual_status,
                        message=f"Expected status {expected_status}, got {actual_status}"
                    )]
            else:
                # Invalid pattern
                return [ValidationError(
                    test_name=test_name,
                    validator="status",
                    field="status_code",
                    expected=expected_status,
                    actual=actual_status,
                    message=f"Invalid status pattern '{expected_status}'. Use: 2xx, 3xx, 4xx, 5xx, or exact code"
                )]
        else:
            # Exact match
            if actual_status != expected_status:
                return [ValidationError(
                    test_name=test_name,
                    validator="status",
                    field="status_code",
                    expected=expected_status,
                    actual=actual_status,
                    message=f"Expected status {expected_status}, got {actual_status}"
                )]
        
        return []
