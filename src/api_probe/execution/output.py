"""Output variable capture from responses."""

from typing import Any, Dict

from .context import ExecutionContext
from ..validation.extractor import PathExtractor


class OutputCapture:
    """Captures output variables from responses."""
    
    def __init__(self, extractor: PathExtractor):
        """Initialize output capture.
        
        Args:
            extractor: Path extractor for value extraction
        """
        self.extractor = extractor
    
    def capture(
        self,
        response: Any,
        output_spec: Dict[str, str],
        context: ExecutionContext
    ) -> None:
        """Capture output variables from response.
        
        Args:
            response: HTTP response object
            output_spec: Dict mapping var names to paths (e.g., {"TOKEN": "body.access_token"})
            context: Execution context to store variables in
            
        Raises:
            ValueError: If path is invalid or extraction fails
        """
        for var_name, path in output_spec.items():
            value = self._extract_value(response, path)
            context.set_variable(var_name, value)
    
    def _extract_value(self, response: Any, path: str) -> Any:
        """Extract value using path with prefix.
        
        Args:
            response: HTTP response object
            path: Path with prefix (body.*, headers.*, status)
            
        Returns:
            Extracted value
            
        Raises:
            ValueError: If path format is invalid
        """
        if path == "status":
            return response.status_code
        elif path.startswith("body."):
            # Extract from body
            body_path = path[5:]  # Remove "body." prefix
            return self.extractor.extract(response, body_path)
        elif path.startswith("headers."):
            # Extract from headers
            header_name = path[8:]  # Remove "headers." prefix
            return self.extractor.extract_header(response, header_name)
        else:
            raise ValueError(f"Invalid output path: {path}. Must start with 'body.', 'headers.', or be 'status'")
