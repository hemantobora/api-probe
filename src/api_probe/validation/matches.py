"""Matches validator - asserts values match regex patterns."""

import re
from typing import Any, Dict

from .base import Validator, ValidationError


class MatchesValidator(Validator):
    """Validates that field values match regex patterns."""
    
    def __init__(self, extractor):
        """Initialize with path extractor.
        
        Args:
            extractor: PathExtractor instance for value extraction
        """
        self.extractor = extractor
    
    def validate(self, test_name: str, response: Any, patterns: Dict[str, str]) -> list[ValidationError]:
        """Validate that fields match regex patterns.
        
        Args:
            test_name: Name of the test
            response: HTTP response object
            patterns: Dict mapping paths to regex patterns
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        for path, pattern in patterns.items():
            try:
                actual = self.extractor.extract(response, path)
                
                # Only works on strings
                if not isinstance(actual, str):
                    errors.append(ValidationError(
                        test_name=test_name,
                        validator="matches",
                        field=path,
                        expected=f"string matching /{pattern}/",
                        actual=f"<non-string: {type(actual).__name__}>",
                        message=f"Field '{path}' is not a string, cannot match pattern"
                    ))
                    continue
                
                # Check if matches
                if not re.search(pattern, actual):
                    errors.append(ValidationError(
                        test_name=test_name,
                        validator="matches",
                        field=path,
                        expected=f"/{pattern}/",
                        actual=actual,
                        message=f"Field '{path}' does not match pattern /{pattern}/"
                    ))
            except (KeyError, IndexError, ValueError) as e:
                errors.append(ValidationError(
                    test_name=test_name,
                    validator="matches",
                    field=path,
                    expected=f"/{pattern}/",
                    actual="<field absent>",
                    message=f"Field '{path}' not found in response"
                ))
        
        return errors
