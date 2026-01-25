"""HTTP client for executing requests."""

import requests
from typing import Any


class HTTPClient:
    """Executes HTTP requests."""
    
    def __init__(self, timeout: int = 30):
        """Initialize HTTP client.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
    
    def execute(self, request_params: dict) -> requests.Response:
        """Execute HTTP request.
        
        Args:
            request_params: Request parameters (method, url, headers, data)
            
        Returns:
            HTTP response
            
        Raises:
            requests.RequestException: On request failure
        """
        return self.session.request(
            timeout=self.timeout,
            **request_params
        )
