"""Tests for the HTTP server wrapper."""
from http_server import create_app, mcp


def test_create_app_returns_starlette_app():
    app = create_app()
    assert hasattr(app, "router")


def test_create_app_callable():
    """The app returned by create_app is a valid ASGI/Starlette app."""
    app = create_app()
    assert callable(app)


def test_mcp_settings_configured():
    assert mcp.settings.host == "0.0.0.0"
    assert mcp.settings.port == 8000
    assert mcp.settings.streamable_http_path == "/"


def test_transport_security_settings():
    security = mcp.settings.transport_security
    assert security.enable_dns_rebinding_protection is True
    assert "mcp.deplixo.com" in security.allowed_hosts
    assert "https://claude.ai" in security.allowed_origins
    assert "https://mcp.deplixo.com" in security.allowed_origins
