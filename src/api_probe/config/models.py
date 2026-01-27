"""Data models for configuration."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class Validation:
    """Validation specification for a probe."""
    status: Optional[int] = None
    headers: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    response_time: Optional[int] = None  # Max response time in milliseconds


@dataclass
class Probe:
    """Single API probe definition."""
    name: str
    type: str  # "rest" or "graphql"
    endpoint: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    body: Optional[Any] = None
    query: Optional[str] = None  # GraphQL only
    variables: Optional[Dict[str, Any]] = None  # GraphQL only
    validation: Optional[Validation] = None
    output: Optional[Dict[str, str]] = None
    delay: Optional[float] = None  # Delay in seconds before executing probe
    timeout: Optional[float] = None  # Request timeout in seconds
    retry: Optional[Dict[str, Any]] = None  # Retry configuration
    debug: bool = False  # Print request/response details to stderr
    ignore: Optional[Union[bool, str]] = None  # Skip this probe if true or "${VAR}" evaluates to true


@dataclass
class Group:
    """Group of probes that execute in parallel."""
    probes: List[Probe] = field(default_factory=list)
    name: Optional[str] = None  # Optional group name
    ignore: Optional[Union[bool, str]] = None  # Skip entire group if true or "${VAR}" evaluates to true


@dataclass
class Execution:
    """Single execution context definition."""
    name: Optional[str] = None
    vars: List[Dict[str, str]] = field(default_factory=list)
    
    def get_variables_dict(self) -> Dict[str, str]:
        """Convert vars list to dictionary.
        
        Returns:
            Dictionary mapping variable names to values
        """
        result = {}
        for var_dict in self.vars:
            # Each item in vars is a dict with one key-value pair
            for key, value in var_dict.items():
                result[key] = value
        return result


@dataclass
class Config:
    """Root configuration object."""
    probes: List[Union[Probe, Group]] = field(default_factory=list)
    executions: List[Execution] = field(default_factory=list)
