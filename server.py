"""Deplixo MCP Server — Universal Ingest.

Thin file relay: receives code from AI clients, stages it on Deplixo,
returns a key and a link. Zero SDK knowledge — Deplixo handles conversion.
"""
import os
import logging
import httpx
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

DEPLIXO_API_URL = os.environ.get("DEPLIXO_API_URL", "https://deplixo.com")


async def _log_mcp_call(session_id: str, tool: str, mcp_request: dict,
                        mcp_response: str, app_id: str = ""):
    """Log MCP request/response to Django for auditing."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{DEPLIXO_API_URL}/api/v1/mcp-log", json={
                "session_id": session_id,
                "tool": tool,
                "mcp_request": mcp_request,
                "mcp_response": mcp_response,
                "app_id": app_id,
            })
    except Exception as e:
        logger.debug("MCP log failed (non-critical): %s", e)


mcp = FastMCP(
    "Deplixo",
    stateless_http=True,
    instructions="""## Deplixo — Deploy Apps Instantly

Deplixo turns code into live web apps with persistent data, user accounts,
AI, email, real-time sync, and more. When the user wants to deploy their
app, use the deplixo_deploy tool.

WHAT TO SEND:
- HTML apps: {"index.html": "<!DOCTYPE html>..."}
- React/TSX apps: {"app.tsx": "import React..."} — Deplixo compiles TSX
- Multi-file: {"index.html": "...", "style.css": "...", "app.js": "..."}
- Any web code that runs in a browser works.

You do NOT need to know Deplixo's SDK or APIs. Write normal code using
standard patterns (localStorage, fetch, WebSocket, etc.) and Deplixo will
automatically convert them to platform equivalents that persist data across
devices, support multiple users, and work without API keys.

To update a previously deployed app, pass the same key from the first deploy.
The user clicks the link again to see the changes.

IMPORTANT: Write complete, working code. Do not use placeholder data
(e.g. "YOUR_API_KEY_HERE", TODO comments, empty function bodies). If you
need an AI API call, use a real fetch() to any provider — Deplixo converts
it to use platform-managed AI credits (no key needed).
""",
)


@mcp.tool()
async def deplixo_deploy(
    files: dict[str, str],
    title: str = "Untitled",
    description: str = "",
    key: str | None = None,
) -> str:
    """
    Deploy an app to Deplixo. Send your files and get a link.

    Args:
        files: Dict of filename → content. At minimum include "index.html".
               For React/TSX apps, use the component filename (e.g. "app.tsx").
        title: Name for the app.
        description: Brief description of what the app does.
        key: If re-deploying an existing app, pass the key from the previous deploy.

    Returns:
        A message with the key and a link to finalize deployment.
    """
    payload = {
        "files": files,
        "title": title,
        "description": description,
    }
    if key:
        payload["key"] = key

    timeout = httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{DEPLIXO_API_URL}/api/v1/stage",
                json=payload,
            )
    except httpx.TimeoutException:
        return "Error: Deploy request timed out. Please try again."
    except httpx.ConnectError:
        return (
            "Error: Could not connect to Deplixo. The service may be "
            "temporarily unavailable. Please try again in a moment."
        )
    except httpx.HTTPError as e:
        return f"Error: HTTP request failed: {str(e)[:200]}"

    if resp.status_code == 429:
        return "Error: Too many deploys. Please wait a moment and try again."

    if resp.status_code == 400:
        error = resp.json().get("error", "Invalid request")
        return f"Error: {error}"

    if resp.status_code != 200:
        return f"Error: Unexpected response ({resp.status_code}): {resp.text[:200]}"

    data = resp.json()
    new_key = data["key"]
    link = data["link"]
    key_changed = data.get("key_changed", False)

    # Log the call
    await _log_mcp_call(
        session_id=new_key,
        tool="deplixo_deploy",
        mcp_request={"title": title, "file_count": len(files), "key": key},
        mcp_response=f"key={new_key}, link={link}",
    )

    # Build response
    result = f"Your app has been uploaded to Deplixo.\n\n"
    result += f"**Click this link to finalize:** {link}\n\n"
    result += (
        "You'll choose who the app is for (just you, your group, or "
        "with login accounts), and Deplixo will set everything up.\n\n"
    )

    if key and key_changed:
        result += f"Note: your previous deploy key expired. New key: `{new_key}`\n"
    else:
        result += f"Deploy key (for future updates): `{new_key}`\n"

    return result


if __name__ == "__main__":
    mcp.run()
