"""HTTP transport for the Brightwing MCP server.

FastMCP settings are configured via FASTMCP_ prefixed env vars.
"""
import os

os.environ.setdefault("FASTMCP_HOST", "0.0.0.0")
os.environ.setdefault("FASTMCP_PORT", os.environ.get("PORT", "8000"))

from server import mcp

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
