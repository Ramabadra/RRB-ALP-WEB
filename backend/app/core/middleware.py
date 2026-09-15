"""
Security Middleware — OWASP Headers and request hardening.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses similar to Helmet in Node.js.
    Protects against XSS, clickjacking, MIME sniffing, and enforces HTTPS.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Prevent browsers from MIME-sniffing a response away from the declared content-type
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking by denying rendering in an iframe
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS filtering
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Strict Transport Security (HSTS) - force HTTPS
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy (Basic API configuration)
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
        
        return response
