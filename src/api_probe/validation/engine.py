"""Validation engine that runs all validators."""

from typing import Any, Dict, List

from ..validation.base import ValidationError, Validator
from ..validation.status import StatusValidator
from ..validation.present import PresentValidator
from ..validation.absent import AbsentValidator
from ..validation.equals import EqualsValidator
from ..validation.matches import MatchesValidator
from ..validation.type import TypeValidator
from ..validation.contains import ContainsValidator
from ..validation.range import RangeValidator
from ..validation.extractor import PathExtractor


class ValidationEngine:
    """Orchestrates validation of responses."""
    
    def __init__(self):
        """Initialize validation engine with all validators."""
        self.extractor = PathExtractor()
        
        # Initialize all validators
        self.status_validator = StatusValidator()
        self.present_validator = PresentValidator(self.extractor)
        self.absent_validator = AbsentValidator(self.extractor)
        self.equals_validator = EqualsValidator(self.extractor)
        self.matches_validator = MatchesValidator(self.extractor)
        self.type_validator = TypeValidator(self.extractor)
        self.contains_validator = ContainsValidator(self.extractor)
        self.range_validator = RangeValidator(self.extractor)
    
    def validate(
        self,
        test_name: str,
        response: Any,
        validation_spec: Dict[str, Any]
    ) -> List[ValidationError]:
        """Run all validations on response.
        
        Args:
            test_name: Name of the test being validated
            response: HTTP response object
            validation_spec: Validation specification dict
            
        Returns:
            List of all validation errors (empty if all passed)
        """
        errors = []
        
        # Status validation
        if 'status' in validation_spec:
            errors.extend(
                self.status_validator.validate(test_name, response, validation_spec['status'])
            )
        
        # Header validations
        if 'headers' in validation_spec:
            errors.extend(self._validate_headers(test_name, response, validation_spec['headers']))
        
        # Body validations
        if 'body' in validation_spec:
            errors.extend(self._validate_body(test_name, response, validation_spec['body']))
        
        return errors
    
    def _validate_headers(self, test_name: str, response: Any, header_spec: Dict[str, Any]) -> List[ValidationError]:
        """Validate headers.
        
        Args:
            test_name: Test name
            response: HTTP response
            header_spec: Header validation specification
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if 'present' in header_spec:
            errors.extend(self._validate_headers_present(test_name, response, header_spec['present']))
        
        if 'absent' in header_spec:
            errors.extend(self._validate_headers_absent(test_name, response, header_spec['absent']))
        
        if 'equals' in header_spec:
            errors.extend(self._validate_headers_equals(test_name, response, header_spec['equals']))
        
        if 'matches' in header_spec:
            errors.extend(self._validate_headers_matches(test_name, response, header_spec['matches']))
        
        if 'contains' in header_spec:
            errors.extend(self._validate_headers_contains(test_name, response, header_spec['contains']))
        
        return errors
    
    def _validate_body(self, test_name: str, response: Any, body_spec: Dict[str, Any]) -> List[ValidationError]:
        """Validate response body.
        
        Args:
            test_name: Test name
            response: HTTP response
            body_spec: Body validation specification
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if 'present' in body_spec:
            errors.extend(self.present_validator.validate(test_name, response, body_spec['present']))
        
        if 'absent' in body_spec:
            errors.extend(self.absent_validator.validate(test_name, response, body_spec['absent']))
        
        if 'equals' in body_spec:
            errors.extend(self.equals_validator.validate(test_name, response, body_spec['equals']))
        
        if 'matches' in body_spec:
            errors.extend(self.matches_validator.validate(test_name, response, body_spec['matches']))
        
        if 'type' in body_spec:
            errors.extend(self.type_validator.validate(test_name, response, body_spec['type']))
        
        if 'contains' in body_spec:
            errors.extend(self.contains_validator.validate(test_name, response, body_spec['contains']))
        
        if 'range' in body_spec:
            errors.extend(self.range_validator.validate(test_name, response, body_spec['range']))
        
        return errors
    
    # Header-specific validation methods
    
    def _validate_headers_present(self, test_name: str, response: Any, headers: List[str]) -> List[ValidationError]:
        """Validate that headers are present."""
        errors = []
        for header_name in headers:
            try:
                self.extractor.extract_header(response, header_name)
            except KeyError:
                errors.append(ValidationError(
                    test_name=test_name,
                    validator="present",
                    field=f"headers.{header_name}",
                    expected="<header present>",
                    actual="<header absent>",
                    message=f"Header '{header_name}' is absent in response"
                ))
        return errors
    
    def _validate_headers_absent(self, test_name: str, response: Any, headers: List[str]) -> List[ValidationError]:
        """Validate that headers are NOT present."""
        errors = []
        for header_name in headers:
            try:
                value = self.extractor.extract_header(response, header_name)
                errors.append(ValidationError(
                    test_name=test_name,
                    validator="absent",
                    field=f"headers.{header_name}",
                    expected="<header absent>",
                    actual=f"<header present: {value}>",
                    message=f"Header '{header_name}' should not exist but is present"
                ))
            except KeyError:
                # Good - header doesn't exist
                pass
        return errors
    
    def _validate_headers_equals(self, test_name: str, response: Any, expectations: Dict[str, str]) -> List[ValidationError]:
        """Validate header values equal expected."""
        errors = []
        for header_name, expected in expectations.items():
            try:
                actual = self.extractor.extract_header(response, header_name)
                if actual != expected:
                    errors.append(ValidationError(
                        test_name=test_name,
                        validator="equals",
                        field=f"headers.{header_name}",
                        expected=expected,
                        actual=actual,
                        message=f"Header '{header_name}': expected {expected!r}, got {actual!r}"
                    ))
            except KeyError:
                errors.append(ValidationError(
                    test_name=test_name,
                    validator="equals",
                    field=f"headers.{header_name}",
                    expected=expected,
                    actual="<header absent>",
                    message=f"Header '{header_name}' not found in response"
                ))
        return errors
    
    def _validate_headers_matches(self, test_name: str, response: Any, patterns: Dict[str, str]) -> List[ValidationError]:
        """Validate header values match patterns."""
        import re
        errors = []
        for header_name, pattern in patterns.items():
            try:
                actual = self.extractor.extract_header(response, header_name)
                if not re.search(pattern, actual):
                    errors.append(ValidationError(
                        test_name=test_name,
                        validator="matches",
                        field=f"headers.{header_name}",
                        expected=f"/{pattern}/",
                        actual=actual,
                        message=f"Header '{header_name}' does not match pattern /{pattern}/"
                    ))
            except KeyError:
                errors.append(ValidationError(
                    test_name=test_name,
                    validator="matches",
                    field=f"headers.{header_name}",
                    expected=f"/{pattern}/",
                    actual="<header absent>",
                    message=f"Header '{header_name}' not found in response"
                ))
        return errors
    
    def _validate_headers_contains(self, test_name: str, response: Any, expectations: Dict[str, str]) -> List[ValidationError]:
        """Validate header values contain substrings."""
        errors = []
        for header_name, expected in expectations.items():
            try:
                actual = self.extractor.extract_header(response, header_name)
                if expected not in actual:
                    errors.append(ValidationError(
                        test_name=test_name,
                        validator="contains",
                        field=f"headers.{header_name}",
                        expected=f"substring: {expected!r}",
                        actual=actual,
                        message=f"Header '{header_name}' does not contain substring {expected!r}"
                    ))
            except KeyError:
                errors.append(ValidationError(
                    test_name=test_name,
                    validator="contains",
                    field=f"headers.{header_name}",
                    expected=expected,
                    actual="<header absent>",
                    message=f"Header '{header_name}' not found in response"
                ))
        return errors
