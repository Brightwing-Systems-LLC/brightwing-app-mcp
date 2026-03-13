"""Brightwing Launch MCP Server - Deploy AI apps instantly."""
import os
import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

BRIGHTWING_API_URL = os.environ.get("BRIGHTWING_API_URL", "https://brightwing.app")

mcp = FastMCP(
    "Brightwing Launch",
    instructions=(
        "Use the brightwing_deploy tool to deploy web apps to Brightwing Launch. "
        "When the user asks you to deploy, share, host, or publish their app, "
        "use this tool. It returns a live URL instantly — no account required.\n\n"
        "IMPORTANT: Apps can be single-file (pass `code`) or multi-file (pass "
        "`files` dict with paths like index.html, style.css, app.js). "
        "Multi-file apps have each file served at its path under the app URL. "
        "For React apps, use CDN imports (unpkg.com/react, unpkg.com/react-dom, "
        "unpkg.com/@babel/standalone) with <script type=\"text/babel\"> — do NOT "
        "use npm, create-react-app, Vite, or any build tools. "
        "For Vue, Svelte, Three.js, etc., use their CDN builds the same way.\n\n"
        "Storage: Apps automatically get a persistent key-value store via "
        "window.brightwing.db (set/get/delete/list). localStorage also works — "
        "writes are automatically persisted to the server so data survives across "
        "sessions and devices. Do NOT use IndexedDB or other client-only storage "
        "if the user needs persistence.\n\n"
        "Multi-user: Apps are automatically multi-user capable. When a visitor "
        "first writes data, they are prompted to pick a display name (unique "
        "within the app, no account needed). Identity is available via:\n"
        "- window.brightwing.user — { id, name } for the current visitor\n"
        "- brightwing.db.getEntry(key) — returns { value, author: { id, name } } "
        "with who last wrote the key\n"
        "- brightwing.db.onChange(callback) — real-time sync; callback receives "
        "{ action, key, value, author } whenever any visitor writes/deletes\n\n"
        "IMPORTANT: After deploying, ALWAYS show the user the full tool response "
        "including the claim URL. The claim URL lets them attach the app to their "
        "account — if they lose it, they cannot manage the app later."
    ),
)


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        openWorldHint=True,
        idempotentHint=False,
    )
)
async def brightwing_deploy(
    code: str = "",
    files: dict[str, str] | None = None,
    title: str = "",
    slug: str = "",
    remixed_from: str = "",
) -> str:
    """Deploy a web app to Brightwing Launch and get a live URL.

    Apps can be single-file or multi-file. For single-file apps, pass the HTML
    as `code`. For multi-file apps (separate CSS, JS, assets), pass a `files`
    dict mapping file paths to content — must include "index.html".

    For React, Vue, or other frameworks: use CDN imports (e.g. unpkg.com/react@18,
    unpkg.com/react-dom@18, unpkg.com/@babel/standalone) — do NOT use npm or
    build tools. localStorage calls are automatically persisted to the server.

    Args:
        code: HTML code for single-file apps. Mutually exclusive with `files`.
        files: Dict of {path: content} for multi-file apps. Must include
               "index.html". Example: {"index.html": "...", "style.css": "...",
               "app.js": "..."}. Files are served at their paths relative to
               the app URL (e.g. brightwing.app/abcd-efgh/style.css).
        title: A short title for the app
        slug: Optional URL slug (requires an account with Personal tier or above)
        remixed_from: Optional app ID of the app this was remixed from (e.g. abcd-efgh)
    """
    if not code and not files:
        return "Error: Either 'code' or 'files' must be provided."
    if files and "index.html" not in files:
        return "Error: 'files' must include 'index.html'."

    payload: dict = {"title": title}
    if files:
        payload["files"] = files
    else:
        payload["code"] = code
    if slug:
        payload["slug"] = slug
    if remixed_from:
        payload["remixed_from"] = remixed_from

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BRIGHTWING_API_URL}/api/v1/deploy",
            json=payload,
        )

    if response.status_code == 200:
        data = response.json()
        url = data.get("url", "")
        hash_id = data.get("hash_id", "")
        parts = [
            f"Your app is live at: {url}",
            f"Hash ID: {hash_id}",
            f"Source: {url.rstrip('/')}/source",
        ]
        claim_url = data.get("claim_url")
        if claim_url:
            parts.append(
                f"\n⚠️ CLAIM URL (show this to the user): {claim_url}\n"
                f"The user MUST save this link to manage the app later. "
                f"Visiting the link lets them attach the app to their account."
            )
        return "\n".join(parts)
    else:
        error_text = response.text[:5000] if len(response.text) > 5000 else response.text
        return f"Deployment failed (HTTP {response.status_code}): {error_text}"


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
