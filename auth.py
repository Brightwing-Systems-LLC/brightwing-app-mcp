"""Optional OAuth authentication for the Deplixo MCP server.

When configured, the server accepts (but does not require) Bearer tokens.
Authenticated users get their identity forwarded to the Deplixo API;
anonymous users deploy with zero friction as before.
"""

import os

import httpx

from mcp.server.auth.provider import AccessToken, TokenVerifier


DEPLIXO_API_URL = os.environ.get("DEPLIXO_API_URL", "https://deplixo.com")


class DeplixoTokenVerifier(TokenVerifier):
    """Verify Bearer tokens against the Deplixo API.

    Calls GET /api/v1/me with the token to validate it and extract user info.
    Returns None for invalid/expired tokens (the middleware treats this as
    unauthenticated, not as an error).
    """

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{DEPLIXO_API_URL}/api/v1/me",
                    headers={"Authorization": f"Bearer {token}"},
                )
            if response.status_code != 200:
                return None
            data = response.json()
            return AccessToken(
                token=token,
                client_id=str(data.get("id", "")),
                scopes=data.get("scopes", []),
            )
        except Exception:
            return None
