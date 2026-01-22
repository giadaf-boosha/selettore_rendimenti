"""
HTTP Configuration Module - Patches requests library globally.

This module must be imported BEFORE any other module that uses requests.
It configures:
- Realistic User-Agent headers to avoid bot detection
- Appropriate timeouts
- Connection pooling for better performance

Import this at the top of app.py before other imports.
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

logger = logging.getLogger(__name__)

# Realistic User-Agent strings (rotates based on request count)
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Chrome on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Safari on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# Default headers to add to all requests
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,it;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

# Request counter for User-Agent rotation
_request_count = 0


def get_user_agent() -> str:
    """Get a User-Agent string, rotating through the list."""
    global _request_count
    ua = USER_AGENTS[_request_count % len(USER_AGENTS)]
    _request_count += 1
    return ua


def create_session_with_retries(
    retries: int = 3,
    backoff_factor: float = 1.0,
    status_forcelist: tuple = (429, 500, 502, 503, 504),
    timeout: int = 30
) -> requests.Session:
    """
    Create a requests Session with retry logic and proper headers.

    Args:
        retries: Number of retries for failed requests
        backoff_factor: Backoff factor for retries (exponential)
        status_forcelist: HTTP status codes to retry
        timeout: Default timeout in seconds

    Returns:
        Configured requests.Session
    """
    session = requests.Session()

    # Configure retry strategy
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
        raise_on_status=False,
    )

    # Mount adapter with retry strategy
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=20,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set default headers
    session.headers.update(DEFAULT_HEADERS)
    session.headers["User-Agent"] = get_user_agent()

    return session


# Store original functions
_original_get = requests.get
_original_post = requests.post
_original_request = requests.request
_original_session_init = requests.Session.__init__


def _patched_get(url, **kwargs):
    """Patched requests.get with default headers and timeout."""
    # Add default timeout if not specified
    if "timeout" not in kwargs:
        kwargs["timeout"] = 30

    # Add headers if not specified
    if "headers" not in kwargs:
        kwargs["headers"] = {}

    # Merge with default headers
    merged_headers = DEFAULT_HEADERS.copy()
    merged_headers["User-Agent"] = get_user_agent()
    merged_headers.update(kwargs["headers"])
    kwargs["headers"] = merged_headers

    return _original_get(url, **kwargs)


def _patched_post(url, **kwargs):
    """Patched requests.post with default headers and timeout."""
    # Add default timeout if not specified
    if "timeout" not in kwargs:
        kwargs["timeout"] = 30

    # Add headers if not specified
    if "headers" not in kwargs:
        kwargs["headers"] = {}

    # Merge with default headers
    merged_headers = DEFAULT_HEADERS.copy()
    merged_headers["User-Agent"] = get_user_agent()
    merged_headers.update(kwargs["headers"])
    kwargs["headers"] = merged_headers

    return _original_post(url, **kwargs)


def _patched_request(method, url, **kwargs):
    """Patched requests.request with default headers and timeout."""
    # Add default timeout if not specified
    if "timeout" not in kwargs:
        kwargs["timeout"] = 30

    # Add headers if not specified
    if "headers" not in kwargs:
        kwargs["headers"] = {}

    # Merge with default headers
    merged_headers = DEFAULT_HEADERS.copy()
    merged_headers["User-Agent"] = get_user_agent()
    merged_headers.update(kwargs["headers"])
    kwargs["headers"] = merged_headers

    return _original_request(method, url, **kwargs)


def _patched_session_init(self, *args, **kwargs):
    """Patched Session.__init__ to add default headers."""
    _original_session_init(self, *args, **kwargs)

    # Add default headers to new sessions
    self.headers.update(DEFAULT_HEADERS)
    self.headers["User-Agent"] = get_user_agent()


def patch_requests():
    """
    Monkey-patch requests library to add default headers and timeouts.

    This function patches:
    - requests.get
    - requests.post
    - requests.request
    - requests.Session.__init__

    Call this once at application startup.
    """
    requests.get = _patched_get
    requests.post = _patched_post
    requests.request = _patched_request
    requests.Session.__init__ = _patched_session_init

    logger.info("HTTP configuration applied: User-Agent headers and timeouts configured")


def unpatch_requests():
    """Restore original requests functions (for testing)."""
    requests.get = _original_get
    requests.post = _original_post
    requests.request = _original_request
    requests.Session.__init__ = _original_session_init

    logger.info("HTTP configuration removed: original requests functions restored")


# Auto-apply patch when module is imported
patch_requests()
