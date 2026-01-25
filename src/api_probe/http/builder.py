"""HTTP request builder."""

import json
from typing import Any, Dict, Optional
from urllib.parse import urlencode


class RequestBuilder:
    """Builds HTTP requests from test specifications."""
    
    def build_rest_request(
        self,
        endpoint: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None
    ) -> dict:
        """Build REST request parameters.
        
        Args:
            endpoint: Target URL
            method: HTTP method
            headers: HTTP headers
            body: Request body
            
        Returns:
            Dict with request parameters for requests library
            
        Raises:
            ValueError: If body present but Content-Type missing
        """
        params = {
            'method': method.upper(),
            'url': endpoint,
            'headers': headers or {}
        }
        
        if body is not None:
            # CRITICAL: Content-Type is mandatory if body present
            content_type = self._get_content_type(headers or {})
            if not content_type:
                raise ValueError("Content-Type header is required when body is present")
            
            # Serialize body based on Content-Type
            params['data'] = self._serialize_body(body, content_type)
        
        return params
    
    def build_graphql_request(
        self,
        endpoint: str,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> dict:
        """Build GraphQL request parameters.
        
        Args:
            endpoint: GraphQL endpoint URL
            query: GraphQL query/mutation
            variables: Query variables
            headers: HTTP headers
            
        Returns:
            Dict with request parameters for requests library
        """
        headers = headers or {}
        
        # Auto-set Content-Type for GraphQL
        if 'content-type' not in {k.lower() for k in headers.keys()}:
            headers['Content-Type'] = 'application/json'
        
        body = {'query': query}
        if variables:
            body['variables'] = variables
        
        return {
            'method': 'POST',
            'url': endpoint,
            'headers': headers,
            'data': json.dumps(body)
        }
    
    def _get_content_type(self, headers: Dict[str, str]) -> Optional[str]:
        """Get Content-Type from headers (case-insensitive).
        
        Args:
            headers: HTTP headers dict
            
        Returns:
            Content-Type value or None
        """
        for key, value in headers.items():
            if key.lower() == 'content-type':
                return value
        return None
    
    def _serialize_body(self, body: Any, content_type: str) -> str:
        """Serialize request body based on Content-Type.
        
        Args:
            body: Request body
            content_type: Content-Type header value
            
        Returns:
            Serialized body string
        """
        content_type_lower = content_type.lower()
        
        if 'application/json' in content_type_lower:
            return json.dumps(body)
        elif 'application/x-www-form-urlencoded' in content_type_lower:
            return urlencode(body)
        elif 'application/xml' in content_type_lower or 'text/xml' in content_type_lower:
            # For now, assume body is already XML string
            return body if isinstance(body, str) else str(body)
        else:
            # Default to string representation
            return str(body)
