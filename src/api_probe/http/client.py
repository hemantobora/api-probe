"""HTTP client for executing requests."""

import sys
import time
import warnings
from typing import Any, Optional

import requests
import urllib3


class HTTPClient:
    """Executes HTTP requests."""

    def __init__(self, default_timeout: int = 30):
        """Initialize HTTP client.

        Args:
            default_timeout: Default request timeout in seconds
        """
        self.default_timeout = default_timeout
        # _print_lock is imported lazily from executor to avoid circular imports.
        # Falls back to a no-op if not available (e.g. in tests).
        self._lock = None

    def _print(self, *args, **kwargs):
        """Thread-safe print to stderr using executor's print lock if available."""
        try:
            from ..execution.executor import _print_lock
            with _print_lock:
                print(*args, file=sys.stderr, **kwargs)
        except ImportError:
            print(*args, file=sys.stderr, **kwargs)

    def execute(
        self,
        request_params: dict,
        timeout: Optional[float] = None,
        retry: Optional[dict] = None,
        debug: bool = False,
        verify: bool = True,
    ) -> requests.Response:
        """Execute HTTP request with retry support.

        A new Session is created per call so concurrent executions never
        share connection pool state.

        Args:
            request_params: Request parameters (method, url, headers, data)
            timeout: Request timeout in seconds (overrides default)
            retry: Retry configuration dict with max_attempts and delay
            debug: If True, print request/response details to stderr
            verify: If False, skip SSL certificate verification

        Returns:
            HTTP response

        Raises:
            requests.RequestException: On request failure after retries
        """
        effective_timeout = timeout if timeout is not None else self.default_timeout

        max_attempts = 1
        retry_delay = 0
        if retry:
            max_attempts = retry.get('max_attempts', 1)
            retry_delay = retry.get('delay', 0)

        last_exception = None

        # Fresh session per execution — avoids shared connection pool state
        # across concurrent threads (fix #5)
        session = requests.Session()

        try:
            for attempt in range(1, max_attempts + 1):
                try:
                    if debug:
                        self._print(f"[DEBUG] Request attempt {attempt}/{max_attempts}")
                        self._print(f"[DEBUG]   Method: {request_params.get('method')}")
                        self._print(f"[DEBUG]   URL: {request_params.get('url')}")
                        if request_params.get('headers'):
                            self._print(f"[DEBUG]   Headers: {request_params.get('headers')}")
                        if request_params.get('data'):
                            data_str = str(request_params.get('data'))
                            data_preview = data_str[:200]
                            self._print(f"[DEBUG]   Body: {data_preview}{'...' if len(data_str) > 200 else ''}")

                    # Scope the InsecureRequestWarning suppression to this
                    # request only — never affect other probes (fix #1)
                    with warnings.catch_warnings():
                        if not verify:
                            warnings.simplefilter('ignore', urllib3.exceptions.InsecureRequestWarning)

                        response = session.request(
                            timeout=effective_timeout,
                            verify=verify,
                            **request_params,
                        )

                    # Attach elapsed time in ms for response_time validation
                    response.elapsed_ms = int(response.elapsed.total_seconds() * 1000)

                    if debug:
                        self._print(f"[DEBUG] Response:")
                        self._print(f"[DEBUG]   Status: {response.status_code}")
                        self._print(f"[DEBUG]   Headers: {dict(response.headers)}")
                        try:
                            body_preview = response.text[:500]
                            self._print(f"[DEBUG]   Body: {body_preview}{'...' if len(response.text) > 500 else ''}")
                        except Exception:
                            self._print("[DEBUG]   Body: <binary data>")
                        self._print("")

                    return response

                except requests.RequestException as e:
                    last_exception = e

                    if debug:
                        self._print(f"[DEBUG] Request failed: {e}")

                    if attempt < max_attempts:
                        if debug:
                            self._print(f"[DEBUG] Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                    else:
                        raise

        finally:
            session.close()

        if last_exception:
            raise last_exception
        raise RuntimeError("Request failed with no exception")
