"""Tests for the Deplixo MCP server."""
import inspect

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from server import deplixo_deploy


@pytest.mark.asyncio
async def test_deploy_files_required():
    """files is a required argument with no default."""
    sig = inspect.signature(deplixo_deploy)
    assert "files" in sig.parameters
    assert sig.parameters["files"].default is inspect.Parameter.empty


@pytest.mark.asyncio
async def test_deploy_success():
    """Successful deploy returns key and link."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "key": "abc123",
        "link": "https://deplixo.com/go/abc123",
    }

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_deploy(
            files={"index.html": "<h1>Hello</h1>"},
            title="Test App",
        )

    assert "abc123" in result
    assert "deplixo.com/go/abc123" in result


@pytest.mark.asyncio
async def test_deploy_with_key_redeploy():
    """Re-deploy with key passes it in payload."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "key": "abc123",
        "link": "https://deplixo.com/go/abc123",
    }

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await deplixo_deploy(
            files={"index.html": "<h1>Updated</h1>"},
            key="abc123",
        )

    # First post call is the deploy, second is the mcp-log
    deploy_call = mock_client.post.call_args_list[0]
    payload = deploy_call.kwargs.get("json") or deploy_call[1].get("json")
    assert payload["key"] == "abc123"
    assert payload["files"] == {"index.html": "<h1>Updated</h1>"}


@pytest.mark.asyncio
async def test_deploy_api_error():
    """API 500 returns error message."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_deploy(files={"index.html": "<h1>Hi</h1>"})

    assert "Error" in result


@pytest.mark.asyncio
async def test_deploy_timeout():
    """Timeout returns friendly error."""
    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("timed out")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_deploy(files={"index.html": "<h1>Hi</h1>"})

    assert "timed out" in result.lower()


@pytest.mark.asyncio
async def test_deploy_rate_limit():
    """429 returns rate limit message."""
    mock_response = MagicMock()
    mock_response.status_code = 429

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_deploy(files={"index.html": "<h1>Hi</h1>"})

    assert "too many" in result.lower()


@pytest.mark.asyncio
async def test_deploy_400_returns_api_error():
    """400 returns the API error message."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {"error": "Files too large"}

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_deploy(files={"index.html": "<h1>Hi</h1>"})

    assert "Files too large" in result
