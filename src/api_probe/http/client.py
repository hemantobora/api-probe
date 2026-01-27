"""HTTP client for executing requests."""

import requests
import time
import sys
from typing import Any, Optional


class HTTPClient:
    """Executes HTTP requests."""
    
    def __init__(self, default_timeout: int = 30):
        """Initialize HTTP client.
        
        Args:
            default_timeout: Default request timeout in seconds
        """
        self.default_timeout = default_timeout
        self.session = requests.Session()
    
    def execute(
        self, 
        request_params: dict, 
        timeout: Optional[float] = None,
        retry: Optional[dict] = None,
        debug: bool = False
    ) -> requests.Response:
        """Execute HTTP request with retry support.
        
        Args:
            request_params: Request parameters (method, url, headers, data)
            timeout: Request timeout in seconds (overrides default)
            retry: Retry configuration dict with max_attempts and delay
            debug: If True, print request/response details to stderr
            
        Returns:
            HTTP response
            
        Raises:
            requests.RequestException: On request failure after retries
        """
        effective_timeout = timeout if timeout is not None else self.default_timeout
        
        # Parse retry config
        max_attempts = 1
        retry_delay = 0
        if retry:
            max_attempts = retry.get('max_attempts', 1)
            retry_delay = retry.get('delay', 0)
        
        last_exception = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                if debug:
                    print(f"[DEBUG] Request attempt {attempt}/{max_attempts}", file=sys.stderr)
                    print(f"[DEBUG]   Method: {request_params.get('method')}", file=sys.stderr)
                    print(f"[DEBUG]   URL: {request_params.get('url')}", file=sys.stderr)
                    if request_params.get('headers'):
                        print(f"[DEBUG]   Headers: {request_params.get('headers')}", file=sys.stderr)
                    if request_params.get('data'):
                        data_preview = str(request_params.get('data'))[:200]
                        print(f"[DEBUG]   Body: {data_preview}{'...' if len(str(request_params.get('data'))) > 200 else ''}", file=sys.stderr)
                
                response = self.session.request(
                    timeout=effective_timeout,
                    **request_params
                )
                
                # Calculate response time in milliseconds
                response.elapsed_ms = int(response.elapsed.total_seconds() * 1000)
                
                if debug:
                    print(f"[DEBUG] Response:", file=sys.stderr)
                    print(f"[DEBUG]   Status: {response.status_code}", file=sys.stderr)
                    print(f"[DEBUG]   Headers: {dict(response.headers)}", file=sys.stderr)
                    try:
                        body_preview = response.text[:500]
                        print(f"[DEBUG]   Body: {body_preview}{'...' if len(response.text) > 500 else ''}", file=sys.stderr)
                    except:
                        print(f"[DEBUG]   Body: <binary data>", file=sys.stderr)
                    print(file=sys.stderr)
                
                return response
                
            except requests.RequestException as e:
                last_exception = e
                
                if debug:
                    print(f"[DEBUG] Request failed: {e}", file=sys.stderr)
                
                if attempt < max_attempts:
                    if debug:
                        print(f"[DEBUG] Retrying in {retry_delay}s...", file=sys.stderr)
                    time.sleep(retry_delay)
                else:
                    # Final attempt failed
                    raise
        
        # Should never reach here, but just in case
        if last_exception:
            raise last_exception
        raise RuntimeError("Request failed with no exception")
