"""HTTP transport for the Deplixo MCP server.

Supports optional OAuth authentication: if a Bearer token is present it is
verified and the identity is made available to tools via auth context.
Requests without a token are served normally (zero friction).
"""

import os

import uvicorn
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route

from mcp.server.auth.middleware.auth_context import AuthContextMiddleware
from mcp.server.auth.middleware.bearer_auth import BearerAuthBackend
from mcp.server.transport_security import TransportSecuritySettings

from auth import DeplixoTokenVerifier
from server import mcp

DEPLIXO_API_URL = os.environ.get("DEPLIXO_API_URL", "https://deplixo.com")

# Override settings directly before running
mcp.settings.host = "0.0.0.0"
mcp.settings.port = 8000
mcp.settings.streamable_http_path = "/"
mcp.settings.transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=["mcp.deplixo.com"],
    allowed_origins=[
        "https://mcp.deplixo.com",
        "https://claude.ai",
        "https://*.claude.ai",
    ],
)


def _create_resource_metadata_route() -> Route:
    """Create an RFC 9728 OAuth Protected Resource Metadata endpoint.

    This tells MCP clients that auth is available and where the authorization
    server lives, without requiring auth for normal requests.
    """
    import json

    from starlette.requests import Request
    from starlette.responses import Response

    metadata = {
        "resource": "https://mcp.deplixo.com",
        "authorization_servers": [DEPLIXO_API_URL],
        "bearer_methods_supported": ["header"],
    }
    body = json.dumps(metadata).encode()

    async def handle(request: Request) -> Response:
        return Response(content=body, media_type="application/json")

    return Route(
        "/.well-known/oauth-protected-resource",
        endpoint=handle,
        methods=["GET", "OPTIONS"],
    )


def create_app():
    """Create the Starlette app with CORS and optional auth middleware."""
    app = mcp.streamable_http_app()

    # OAuth Protected Resource Metadata (RFC 9728) — lets clients discover
    # that auth is available and find the authorization server.
    app.routes.insert(0, _create_resource_metadata_route())

    # Optional auth: extract Bearer tokens when present, but never reject
    # requests that lack one.  AuthenticationMiddleware + BearerAuthBackend
    # set scope["user"] to an AuthenticatedUser when a valid token is found,
    # and leave it as UnauthenticatedUser otherwise.  AuthContextMiddleware
    # copies it into a contextvar so tools can call get_access_token().
    token_verifier = DeplixoTokenVerifier()
    app.add_middleware(AuthContextMiddleware)
    app.add_middleware(AuthenticationMiddleware, backend=BearerAuthBackend(token_verifier))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://claude.ai",
            "https://*.claude.ai",
            "https://mcp.deplixo.com",
        ],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=True,
    )
    return app


if __name__ == "__main__":
    app = create_app()
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
    server = uvicorn.Server(config)
    server.run()
