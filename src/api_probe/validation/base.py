"""Base validator interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationError:
    """Represents a validation failure."""
    test_name: str
    validator: str
    field: str
    expected: Any
    actual: Any
    message: str


class Validator(ABC):
    """Base class for all validators."""
    
    @abstractmethod
    def validate(self, test_name: str, response: Any, spec: Any) -> list[ValidationError]:
        """Validate response against specification.
        
        Args:
            test_name: Name of the test being validated
            response: HTTP response object
            spec: Validation specification
            
        Returns:
            List of validation errors (empty if valid)
        """
        pass
