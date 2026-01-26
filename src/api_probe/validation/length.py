"""Array/string length validator."""

from typing import Any, Dict, List

from .base import Validator, ValidationError
from .extractor import PathExtractor


class LengthValidator(Validator):
    """Validates array or string length."""
    
    def __init__(self, extractor: PathExtractor):
        """Initialize validator.
        
        Args:
            extractor: Path extractor for getting values
        """
        self.extractor = extractor
    
    def validate(self, test_name: str, response: Any, spec: Dict[str, Any]) -> List[ValidationError]:
        """Validate array/string lengths.
        
        Spec format:
            length:
              path: expected_length
              path: [min, max]
        
        Examples:
            length:
              items: 5           # Exactly 5 items
              results: [1, 10]   # Between 1 and 10 items
              name: [0, 50]      # String length 0-50
              "$": 5             # Root array with 5 items
        
        Args:
            test_name: Name of the test
            response: HTTP response object
            spec: Length validation spec
            
        Returns:
            List of validation errors (empty if all pass)
        """
        errors = []
        
        for path, expected in spec.items():
            try:
                # For root-level paths starting with $, don't add body. prefix
                if path.startswith('$'):
                    extract_path = path
                else:
                    extract_path = f"body.{path}"
                
                value = self.extractor.extract(response, extract_path)
                
                # Get actual length
                if not isinstance(value, (list, str)):
                    errors.append(ValidationError(
                        test_name=test_name,
                        validator="length",
                        field=path,
                        expected="array or string",
                        actual=type(value).__name__,
                        message=f"Cannot check length of {type(value).__name__}"
                    ))
                    continue
                
                actual_length = len(value)
                
                # Check length
                if isinstance(expected, list):
                    # Range: [min, max]
                    min_len, max_len = expected[0], expected[1]
                    if not (min_len <= actual_length <= max_len):
                        errors.append(ValidationError(
                            test_name=test_name,
                            validator="length",
                            field=path,
                            expected=f"length in range [{min_len}, {max_len}]",
                            actual=f"length {actual_length}",
                            message=f"Length {actual_length} is outside range [{min_len}, {max_len}]"
                        ))
                else:
                    # Exact length
                    if actual_length != expected:
                        errors.append(ValidationError(
                            test_name=test_name,
                            validator="length",
                            field=path,
                            expected=f"length {expected}",
                            actual=f"length {actual_length}",
                            message=f"Expected length {expected}, got {actual_length}"
                        ))
                        
            except Exception as e:
                errors.append(ValidationError(
                    test_name=test_name,
                    validator="length",
                    field=path,
                    expected="valid path",
                    actual="error",
                    message=str(e)
                ))
        
        return errors
