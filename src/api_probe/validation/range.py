"""Range validator - asserts numeric values within bounds."""

from typing import Any, Dict, List, Optional

from .base import Validator, ValidationError


class RangeValidator(Validator):
    """Validates that numeric fields fall within specified ranges."""
    
    def __init__(self, extractor):
        """Initialize with path extractor.
        
        Args:
            extractor: PathExtractor instance for value extraction
        """
        self.extractor = extractor
    
    def validate(self, test_name: str, response: Any, ranges: Dict[str, List]) -> list[ValidationError]:
        """Validate that fields are within specified ranges.
        
        Args:
            test_name: Name of the test
            response: HTTP response object
            ranges: Dict mapping paths to [min, max] ranges (None = no limit)
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        for path, range_spec in ranges.items():
            # Validate range format
            if not isinstance(range_spec, list) or len(range_spec) != 2:
                errors.append(ValidationError(
                    test_name=test_name,
                    validator="range",
                    field=path,
                    expected="[min, max]",
                    actual=range_spec,
                    message=f"Range must be [min, max], got {range_spec}"
                ))
                continue
            
            min_val, max_val = range_spec
            
            try:
                actual = self.extractor.extract(response, path)
                
                # Must be numeric
                if not isinstance(actual, (int, float)) or isinstance(actual, bool):
                    errors.append(ValidationError(
                        test_name=test_name,
                        validator="range",
                        field=path,
                        expected=f"number in range {self._format_range(min_val, max_val)}",
                        actual=f"<non-numeric: {type(actual).__name__}>",
                        message=f"Field '{path}' is not numeric, cannot check range"
                    ))
                    continue
                
                # Check min bound
                if min_val is not None and actual < min_val:
                    errors.append(ValidationError(
                        test_name=test_name,
                        validator="range",
                        field=path,
                        expected=f">= {min_val}",
                        actual=actual,
                        message=f"Field '{path}' value {actual} is below minimum {min_val}"
                    ))
                
                # Check max bound
                if max_val is not None and actual > max_val:
                    errors.append(ValidationError(
                        test_name=test_name,
                        validator="range",
                        field=path,
                        expected=f"<= {max_val}",
                        actual=actual,
                        message=f"Field '{path}' value {actual} is above maximum {max_val}"
                    ))
                    
            except (KeyError, IndexError, ValueError) as e:
                errors.append(ValidationError(
                    test_name=test_name,
                    validator="range",
                    field=path,
                    expected=f"range {self._format_range(min_val, max_val)}",
                    actual="<field absent>",
                    message=f"Field '{path}' not found in response"
                ))
        
        return errors
    
    def _format_range(self, min_val: Optional[float], max_val: Optional[float]) -> str:
        """Format range for display.
        
        Args:
            min_val: Minimum value or None
            max_val: Maximum value or None
            
        Returns:
            Formatted range string
        """
        if min_val is None and max_val is None:
            return "(-∞, +∞)"
        elif min_val is None:
            return f"(-∞, {max_val}]"
        elif max_val is None:
            return f"[{min_val}, +∞)"
        else:
            return f"[{min_val}, {max_val}]"
