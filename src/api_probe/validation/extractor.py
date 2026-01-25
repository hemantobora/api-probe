"""Path-based value extractor for response bodies."""

from typing import Any

try:
    from jsonpath_ng import parse as jsonpath_parse
    JSONPATH_AVAILABLE = True
except ImportError:
    JSONPATH_AVAILABLE = False

try:
    from lxml import etree
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False


class PathExtractor:
    """Extracts values from response using path expressions."""
    
    def extract(self, response: Any, path: str) -> Any:
        """Extract value from response body using path.
        
        Args:
            response: HTTP response object
            path: Path expression (JSONPath for JSON, XPath for XML)
            
        Returns:
            Extracted value
            
        Raises:
            ValueError: If extraction fails
        """
        content_type = response.headers.get('Content-Type', '').lower()
        
        # Detect response type
        if 'xml' in content_type or 'soap' in content_type:
            return self._extract_from_xml(response, path)
        else:
            # Default to JSON
            return self._extract_from_json(response, path)
    
    def _extract_from_json(self, response: Any, path: str) -> Any:
        """Extract from JSON response."""
        try:
            data = response.json()
        except Exception:
            raise ValueError(f"Response is not JSON")
        
        # Try advanced JSONPath first if available
        if JSONPATH_AVAILABLE and self._is_advanced_jsonpath(path):
            return self._extract_jsonpath(data, path)
        else:
            # Fall back to simple dot notation
            return self._extract_from_dict(data, path)
    
    def _extract_from_xml(self, response: Any, path: str) -> Any:
        """Extract from XML response using XPath.
        
        Args:
            response: HTTP response object
            path: XPath expression
            
        Returns:
            Extracted value(s)
            
        Raises:
            ValueError: If lxml not available or extraction fails
        """
        if not LXML_AVAILABLE:
            raise ValueError("lxml library required for XML/SOAP support. Install with: pip install lxml")
        
        try:
            # Parse XML
            root = etree.fromstring(response.content)
            
            # Extract namespaces from root element
            namespaces = root.nsmap
            
            # Handle default namespace (None key)
            if None in namespaces:
                # Register default namespace with a prefix for XPath
                namespaces['default'] = namespaces.pop(None)
            
            # Execute XPath
            result = root.xpath(path, namespaces=namespaces)
            
            if not result:
                raise KeyError(f"XPath '{path}' not found")
            
            # If single element, return its text
            if len(result) == 1:
                if isinstance(result[0], etree._Element):
                    return result[0].text
                else:
                    # Attribute or text node
                    return result[0]
            
            # Multiple results, return list
            return [
                elem.text if isinstance(elem, etree._Element) else elem
                for elem in result
            ]
            
        except etree.XMLSyntaxError as e:
            raise ValueError(f"Invalid XML: {e}")
        except Exception as e:
            raise ValueError(f"XPath extraction failed: {e}")
    
    def _is_advanced_jsonpath(self, path: str) -> bool:
        """Check if path uses advanced JSONPath features.
        
        Args:
            path: Path expression
            
        Returns:
            True if advanced features detected
        """
        # Advanced features: wildcards, filters, array slicing
        advanced_patterns = ['[*]', '[?', '..', '[:', '@']
        return any(pattern in path for pattern in advanced_patterns)
    
    def _extract_jsonpath(self, data: dict, path: str) -> Any:
        """Extract using advanced JSONPath.
        
        Args:
            data: Dictionary to extract from
            path: JSONPath expression
            
        Returns:
            Extracted value(s)
            
        Raises:
            ValueError: If path not found
        """
        # Add $ prefix if not present
        if not path.startswith('$'):
            path = f'$.{path}'
        
        jsonpath_expr = jsonpath_parse(path)
        matches = jsonpath_expr.find(data)
        
        if not matches:
            raise KeyError(f"Path '{path}' not found")
        
        # If single match, return the value directly
        if len(matches) == 1:
            return matches[0].value
        
        # Multiple matches, return list of values
        return [match.value for match in matches]
    
    def _extract_from_dict(self, data: dict, path: str) -> Any:
        """Extract value from dict using dot notation.
        
        Args:
            data: Dictionary to extract from
            path: Dot-notation path (e.g., 'user.email')
            
        Returns:
            Extracted value
            
        Raises:
            KeyError: If path not found or intermediate value is null
        """
        # Remove leading $ if present (JSONPath style)
        if path.startswith('$.'):
            path = path[2:]
        elif path == '$':
            return data
        
        parts = path.split('.')
        current = data
        
        for i, part in enumerate(parts):
            # Handle array indexing: items[0]
            if '[' in part:
                key, rest = part.split('[', 1)
                index = int(rest.rstrip(']'))
                
                # Get the key first
                if key:
                    current = current[key]
                
                # Check if current is None before indexing
                if current is None:
                    remaining_path = '.'.join(parts[i:])
                    raise KeyError(f"Cannot access '{remaining_path}' - intermediate value is null")
                
                # Now index into array
                current = current[index]
            else:
                # Check if current is None before accessing attribute
                if current is None:
                    remaining_path = '.'.join(parts[i:])
                    raise KeyError(f"Cannot access '{remaining_path}' - intermediate value is null")
                
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
