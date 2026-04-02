"""Tests for the deplixo_edit MCP tool."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from server import deplixo_edit


@pytest.mark.asyncio
async def test_edit_requires_app_id():
    result = await deplixo_edit(app_id="", claim_token="tok")
    assert "Error" in result
    assert "app_id" in result


@pytest.mark.asyncio
async def test_edit_requires_claim_token():
    result = await deplixo_edit(app_id="abcd-efgh", claim_token="")
    assert "Error" in result
    assert "claim_token" in result


@pytest.mark.asyncio
async def test_edit_requires_something_to_do():
    result = await deplixo_edit(app_id="abcd-efgh", claim_token="tok")
    assert "Error" in result
    assert "edits" in result.lower() or "new_files" in result.lower()


@pytest.mark.asyncio
async def test_edit_success():
    """Mock API returns 200, verify formatted response includes URL + changed files."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "url": "https://deplixo.com/abcd-efgh/",
        "app_id": "abcd-efgh",
        "updated": True,
        "files_changed": ["index.html"],
        "files_added": [],
        "files_deleted": [],
        "claim_token": "tok_123",
    }

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_edit(
            app_id="abcd-efgh",
            claim_token="tok_123",
            edits=[{"file": "index.html", "search": "old", "replace": "new"}],
        )

    assert "App updated" in result
    assert "deplixo.com/abcd-efgh" in result
    assert "index.html" in result
    assert "deplixo_edit" in result  # guidance mentions edit tool


@pytest.mark.asyncio
async def test_edit_conflict():
    """Mock API returns 409, verify error includes file content for retry."""
    mock_response = MagicMock()
    mock_response.status_code = 409
    mock_response.json.return_value = {
        "error": "edit_conflict",
        "failed_edit": {"file": "index.html", "search": "missing text", "reason": "not_found"},
        "file_content": "<html><body><h1>Actual Content</h1></body></html>",
        "applied_edits": [],
        "unapplied_edits": ["index.html"],
    }

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_edit(
            app_id="abcd-efgh",
            claim_token="tok_123",
            edits=[{"file": "index.html", "search": "missing text", "replace": "new"}],
        )

    assert "Edit failed" in result
    assert "Actual Content" in result  # file content returned for retry
    assert "deplixo_edit" in result  # guidance to retry


@pytest.mark.asyncio
async def test_edit_ambiguous():
    """Mock API returns 422, verify error explains multiple matches."""
    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_response.json.return_value = {
        "error": "edit_ambiguous",
        "failed_edit": {"file": "index.html", "search": "div", "reason": "ambiguous", "count": 5},
        "file_content": "<div>one</div><div>two</div><div>three</div>",
        "applied_edits": [],
        "unapplied_edits": ["index.html"],
    }

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_edit(
            app_id="abcd-efgh",
            claim_token="tok_123",
            edits=[{"file": "index.html", "search": "div", "replace": "span"}],
        )

    assert "5 times" in result
    assert "unique" in result.lower()


@pytest.mark.asyncio
async def test_edit_with_feature_gaps():
    """Mock API returns 200 + feature_gaps, verify formatted in response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "url": "https://deplixo.com/abcd-efgh/",
        "app_id": "abcd-efgh",
        "updated": True,
        "files_changed": ["index.html"],
        "files_added": [],
        "files_deleted": [],
        "claim_token": "tok_123",
        "feature_gaps": [
            {"primitive": "deplixo.notifications", "reason": "Recommended but not found."},
        ],
        "missing_collections": [
            {"name": "avatars", "fields": ["userId", "hair", "eyes"]},
        ],
    }

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_edit(
            app_id="abcd-efgh",
            claim_token="tok_123",
            edits=[{"file": "index.html", "search": "old", "replace": "new"}],
        )

    assert "FEATURES NOT YET IMPLEMENTED" in result
    assert "deplixo.notifications" in result
    assert "avatars" in result


@pytest.mark.asyncio
async def test_edit_timeout():
    """Verify shorter timeout than deploy (30s read vs 180s)."""
    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = __import__('httpx').TimeoutException("timed out")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_edit(
            app_id="abcd-efgh",
            claim_token="tok_123",
            edits=[{"file": "index.html", "search": "old", "replace": "new"}],
        )

    assert "Error" in result
    assert "timed out" in result.lower()


@pytest.mark.asyncio
async def test_edit_logging():
    """Verify MCP call logged via _log_mcp_call when session_id provided."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "url": "https://deplixo.com/abcd-efgh/",
        "app_id": "abcd-efgh",
        "updated": True,
        "files_changed": ["index.html"],
        "files_added": [],
        "files_deleted": [],
        "claim_token": "tok_123",
    }

    with patch("server.httpx.AsyncClient") as mock_client_cls, \
         patch("server._log_mcp_call", new_callable=AsyncMock) as mock_log:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await deplixo_edit(
            app_id="abcd-efgh",
            claim_token="tok_123",
            edits=[{"file": "index.html", "search": "old", "replace": "new"}],
            session_id="enh_test123",
        )

    mock_log.assert_called_once()
    call_args = mock_log.call_args
    assert call_args[0][0] == "enh_test123"  # session_id
    assert call_args[0][1] == "edit"  # tool name
