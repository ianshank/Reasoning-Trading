"""
Security headers middleware for FastAPI application.

Adds security-related HTTP headers to all responses to protect against
common web vulnerabilities (XSS, clickjacking, MIME sniffing, etc.).
"""

from __future__ import annotations

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from enterprise_ui.backend.core.logging import get_logger

logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all HTTP responses.

    Security headers included:
    - Content-Security-Policy: Controls resource loading to prevent XSS
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking attacks
    - X-XSS-Protection: Enables browser XSS filtering
    - Strict-Transport-Security: Enforces HTTPS connections
    - Referrer-Policy: Controls referrer information leakage

    Example:
        app.add_middleware(SecurityHeadersMiddleware)
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        enable_hsts: bool = True,
        hsts_max_age: int = 31536000,
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = True,
        csp_directives: dict[str, str] | None = None,
    ) -> None:
        """
        Initialize security headers middleware.

        Args:
            app: ASGI application
            enable_hsts: Enable Strict-Transport-Security header (HTTPS only)
            hsts_max_age: HSTS max-age in seconds (default: 1 year)
            hsts_include_subdomains: Include subdomains in HSTS
            hsts_preload: Enable HSTS preload
            csp_directives: Custom CSP directives (optional)
        """
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload

        # Default Content Security Policy
        if csp_directives is None:
            self.csp_directives = {
                "default-src": "'self'",
                "script-src": "'self' 'unsafe-inline' 'unsafe-eval'",  # Allow inline scripts for WebSocket/AJAX
                "style-src": "'self' 'unsafe-inline'",  # Allow inline styles
                "img-src": "'self' data: https:",  # Allow data URIs and HTTPS images
                "font-src": "'self' data:",
                "connect-src": "'self' ws: wss:",  # Allow WebSocket connections
                "frame-ancestors": "'none'",  # Equivalent to X-Frame-Options: DENY
                "base-uri": "'self'",
                "form-action": "'self'",
                "upgrade-insecure-requests": "",  # Upgrade HTTP to HTTPS
            }
        else:
            self.csp_directives = csp_directives

        logger.info(
            "security_headers_middleware_initialized",
            hsts_enabled=self.enable_hsts,
            hsts_max_age=self.hsts_max_age,
        )

    def _build_csp_header(self) -> str:
        """
        Build Content-Security-Policy header value from directives.

        Returns:
            CSP header string
        """
        csp_parts: list[str] = []
        for directive, value in self.csp_directives.items():
            if value:
                csp_parts.append(f"{directive} {value}")
            else:
                csp_parts.append(directive)
        return "; ".join(csp_parts)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """
        Process request and add security headers to response.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            HTTP response with security headers
        """
        # Process request
        response = await call_next(request)

        # Add security headers
        headers_to_add = {
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",

            # Prevent clickjacking (legacy browsers)
            "X-Frame-Options": "DENY",

            # Enable XSS filtering (legacy browsers)
            "X-XSS-Protection": "1; mode=block",

            # Control referrer information
            "Referrer-Policy": "strict-origin-when-cross-origin",

            # Content Security Policy
            "Content-Security-Policy": self._build_csp_header(),
        }

        # Add HSTS header for HTTPS connections only
        if self.enable_hsts and request.url.scheme == "https":
            hsts_value = f"max-age={self.hsts_max_age}"
            if self.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.hsts_preload:
                hsts_value += "; preload"
            headers_to_add["Strict-Transport-Security"] = hsts_value

        # Apply headers to response
        for header_name, header_value in headers_to_add.items():
            response.headers[header_name] = header_value

        return response


def setup_security_headers(
    app: ASGIApp,
    *,
    enable_hsts: bool = True,
    hsts_max_age: int = 31536000,
    hsts_include_subdomains: bool = True,
    hsts_preload: bool = True,
    csp_directives: dict[str, str] | None = None,
) -> None:
    """
    Add security headers middleware to FastAPI application.

    Args:
        app: FastAPI application instance
        enable_hsts: Enable Strict-Transport-Security header (HTTPS only)
        hsts_max_age: HSTS max-age in seconds (default: 1 year)
        hsts_include_subdomains: Include subdomains in HSTS
        hsts_preload: Enable HSTS preload
        csp_directives: Custom CSP directives (optional)

    Example:
        from fastapi import FastAPI
        from enterprise_ui.backend.middleware.security_headers import setup_security_headers

        app = FastAPI()
        setup_security_headers(app)
    """
    from fastapi import FastAPI

    if isinstance(app, FastAPI):
        app.add_middleware(
            SecurityHeadersMiddleware,
            enable_hsts=enable_hsts,
            hsts_max_age=hsts_max_age,
            hsts_include_subdomains=hsts_include_subdomains,
            hsts_preload=hsts_preload,
            csp_directives=csp_directives,
        )
        logger.info("security_headers_middleware_added_to_app")
    else:
        raise TypeError("app must be a FastAPI instance")
