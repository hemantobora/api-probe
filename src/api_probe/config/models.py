"""Core data models for api-probe configuration."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


@dataclass
class Validation:
    """Response validation specification."""
    status: Optional[int] = None
    headers: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None


@dataclass
class Test:
    """Single API test definition."""
    name: str
    type: Literal["rest", "graphql"]
    endpoint: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    body: Optional[Any] = None
    query: Optional[str] = None  # GraphQL only
    variables: Optional[Dict[str, Any]] = None  # GraphQL only
    validation: Optional[Validation] = None
    output: Optional[Dict[str, str]] = None


@dataclass
class Group:
    """Parallel test group."""
    tests: List[Test] = field(default_factory=list)


@dataclass
class Config:
    """Root configuration."""
    tests: List[Any] = field(default_factory=list)  # List[Test | Group]
