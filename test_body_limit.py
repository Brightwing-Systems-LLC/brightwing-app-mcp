"""Tests for the request body size limit middleware."""
import pytest
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from http_server import RequestBodyLimitMiddleware, MAX_REQUEST_BODY_BYTES, create_app


def _make_test_app(max_bytes=1024):
    """Create a minimal Starlette app with the body limit middleware."""
    async def echo(request):
        body = await request.body()
        return PlainTextResponse(f"OK: {len(body)} bytes")

    app = Starlette(routes=[Route("/", echo, methods=["POST", "GET"])])
    app.add_middleware(RequestBodyLimitMiddleware, max_bytes=max_bytes)
    return app


class TestRequestBodyLimitMiddleware:
    """Tests for RequestBodyLimitMiddleware."""

    def test_small_request_passes(self):
        app = _make_test_app(max_bytes=1024)
        client = TestClient(app)
        resp = client.post("/", content=b"x" * 100, headers={"content-length": "100"})
        assert resp.status_code == 200
        assert "OK" in resp.text

    def test_exact_limit_passes(self):
        app = _make_test_app(max_bytes=1024)
        client = TestClient(app)
        resp = client.post("/", content=b"x" * 1024, headers={"content-length": "1024"})
        assert resp.status_code == 200

    def test_over_limit_rejected(self):
        app = _make_test_app(max_bytes=1024)
        client = TestClient(app)
        resp = client.post("/", content=b"x" * 1025, headers={"content-length": "1025"})
        assert resp.status_code == 413
        assert "too large" in resp.text.lower()

    def test_way_over_limit_rejected(self):
        app = _make_test_app(max_bytes=1024)
        client = TestClient(app)
        resp = client.post("/", content=b"x" * 10000, headers={"content-length": "10000"})
        assert resp.status_code == 413

    def test_get_requests_pass_through(self):
        app = _make_test_app(max_bytes=1024)
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200

    def test_no_content_length_header_passes(self):
        """Requests without Content-Length are allowed through (chunked transfer)."""
        app = _make_test_app(max_bytes=1024)
        client = TestClient(app)
        # TestClient may add Content-Length automatically, but a request
        # without it should not be rejected
        resp = client.post("/", content=b"small")
        assert resp.status_code == 200

    def test_zero_content_length_passes(self):
        app = _make_test_app(max_bytes=1024)
        client = TestClient(app)
        resp = client.post("/", content=b"", headers={"content-length": "0"})
        assert resp.status_code == 200

    def test_custom_max_bytes(self):
        """Middleware respects custom max_bytes values."""
        app = _make_test_app(max_bytes=50)
        client = TestClient(app)
        resp = client.post("/", content=b"x" * 51, headers={"content-length": "51"})
        assert resp.status_code == 413

        resp = client.post("/", content=b"x" * 50, headers={"content-length": "50"})
        assert resp.status_code == 200

    def test_error_message_includes_limit(self):
        app = _make_test_app(max_bytes=5 * 1024 * 1024)
        client = TestClient(app)
        resp = client.post(
            "/",
            content=b"x" * (5 * 1024 * 1024 + 1),
            headers={"content-length": str(5 * 1024 * 1024 + 1)},
        )
        assert resp.status_code == 413
        assert "5MB" in resp.text


class TestProductionAppBodyLimit:
    """Tests that the production create_app() includes the body limit."""

    def test_create_app_has_body_limit_middleware(self):
        """The production app includes RequestBodyLimitMiddleware (rejects large bodies)."""
        app = create_app()
        client = TestClient(app)
        # Verify the middleware is active by sending an oversized request
        resp = client.post(
            "/",
            content=b"x" * (MAX_REQUEST_BODY_BYTES + 1),
            headers={"content-length": str(MAX_REQUEST_BODY_BYTES + 1)},
        )
        assert resp.status_code == 413

    def test_default_max_is_10mb(self):
        """The default MAX_REQUEST_BODY_BYTES is 10 MB."""
        assert MAX_REQUEST_BODY_BYTES == 10 * 1024 * 1024


class TestBodyLimitWithJsonPayload:
    """Tests with realistic JSON payloads like MCP tool calls."""

    def test_normal_deploy_payload_passes(self):
        """A typical deploy payload (small HTML) should pass."""
        import json
        app = _make_test_app(max_bytes=MAX_REQUEST_BODY_BYTES)
        client = TestClient(app)

        payload = json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "deplixo_deploy",
                "arguments": {
                    "code": "<h1>Hello World</h1>" * 100,
                    "title": "Test App",
                },
            },
        })
        resp = client.post(
            "/",
            content=payload.encode(),
            headers={"content-type": "application/json", "content-length": str(len(payload))},
        )
        assert resp.status_code == 200

    def test_large_code_payload_within_limit(self):
        """A payload under 10MB should pass."""
        import json
        app = _make_test_app(max_bytes=MAX_REQUEST_BODY_BYTES)
        client = TestClient(app)

        # ~5MB of code — well within 10MB limit
        large_code = "x" * (5 * 1024 * 1024)
        payload = json.dumps({"code": large_code})
        resp = client.post(
            "/",
            content=payload.encode(),
            headers={"content-type": "application/json", "content-length": str(len(payload))},
        )
        assert resp.status_code == 200

    def test_oversized_payload_rejected(self):
        """A payload over 10MB should be rejected."""
        import json
        app = _make_test_app(max_bytes=MAX_REQUEST_BODY_BYTES)
        client = TestClient(app)

        # ~11MB of code
        huge_code = "x" * (11 * 1024 * 1024)
        payload = json.dumps({"code": huge_code})
        resp = client.post(
            "/",
            content=payload.encode(),
            headers={"content-type": "application/json", "content-length": str(len(payload))},
        )
        assert resp.status_code == 413
