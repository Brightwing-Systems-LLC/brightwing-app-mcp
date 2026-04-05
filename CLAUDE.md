# Deplixo MCP Server

## Overview
MCP server for deploying web apps to Deplixo (deplixo.com). Thin file relay —
receives code from AI clients, stages it on Deplixo, returns a key and a link.
No API key required. No SDK knowledge needed.

## Architecture

The MCP server is a **stateless, thin relay**:

```
AI Client (Claude/GPT) → deplixo-mcp (MCP server at mcp.deplixo.com)
                          → POST https://deplixo.com/api/v1/stage
                            → Deplixo stages files, returns key + link
                          → MCP formats response back to AI client
                            → User clicks link → login → scope select → conversion → workspace
```

The MCP server has ZERO knowledge of the Deplixo SDK. It does not validate
code, recommend primitives, or teach AIs how to write Deplixo code. AIs write
normal code (React, vanilla JS, HTML) and Deplixo handles conversion server-side.

## Tool
- `deplixo_deploy` — Stage files on Deplixo, get a key + intake link

## Configuration
- `DEPLIXO_API_URL` — Backend URL (default: https://deplixo.com)

## Development
```bash
uv sync
uv run python server.py          # stdio transport
uv run python http_server.py     # HTTP transport (for mcp.deplixo.com)
```

## Deployment
Uses docker-compose.bws.yml. Container connects to bws_network, served via
Caddy at mcp.deplixo.com.

**CRITICAL: Do NOT SSH into the prod server to deploy.** Always commit and push
to `main` — GitHub Actions handles deployment automatically.
