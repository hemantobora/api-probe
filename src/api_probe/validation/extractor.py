"""Path-based value extractor for response bodies."""

from typing import Any


class PathExtractor:
    """Extracts values from response using path expressions."""
    
    def extract(self, response: Any, path: str) -> Any:
        """Extract value from response body using path.
        
        Args:
            response: HTTP response object
            path: Path expression (JSONPath for JSON)
            
        Returns:
            Extracted value
            
        Raises:
            ValueError: If extraction fails
        """
        # For now, simple dot-notation for JSON
        # Will enhance with jsonpath-ng later
        
        try:
            data = response.json()
        except Exception:
            raise ValueError(f"Response is not JSON")
        
        return self._extract_from_dict(data, path)
    
    def _extract_from_dict(self, data: dict, path: str) -> Any:
        """Extract value from dict using dot notation.
        
        Args:
            data: Dictionary to extract from
            path: Dot-notation path (e.g., 'user.email')
            
        Returns:
            Extracted value
            
        Raises:
            KeyError: If path not found
        """
        parts = path.split('.')
        current = data
        
        for part in parts:
            # Handle array indexing: items[0]
            if '[' in part:
                key, rest = part.split('[', 1)
                index = int(rest.rstrip(']'))
                current = current[key][index]
            else:
                current = current[part]
        
        return current
    
    def extract_header(self, response: Any, header_name: str) -> str:
        """Extract header value from response.
        
        Args:
            response: HTTP response object
            header_name: Header name
            
        Returns:
            Header value
            
        Raises:
            KeyError: If header not found
        """
        # Headers are case-insensitive
        for key, value in response.headers.items():
            if key.lower() == header_name.lower():
                return value
        
        raise KeyError(f"Header '{header_name}' not found")
