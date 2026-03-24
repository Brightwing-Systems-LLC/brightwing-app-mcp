# Deplixo MCP Server

## Overview
MCP server for deploying web apps to Deplixo (deplixo.com). No API key required — zero friction.

## Tools
- `deplixo_deploy` - Deploy HTML/JS/CSS code and get a live URL instantly

## Configuration
Optional environment variable:
- `DEPLIXO_API_URL` - API URL (default: https://deplixo.com)

## Development
```bash
uv sync
uv run python server.py  # stdio transport
uv run python http_server.py  # HTTP transport (for mcp.deplixo.com)
```

## Deployment
Uses docker-compose.bws.yml for shared infrastructure deployment.
Container connects to bws_network, served via Caddy at mcp.deplixo.com.

**CRITICAL: Do NOT SSH into the prod server to deploy.** Always commit and push to `main` — GitHub Actions handles deployment automatically. Do not run `git pull`, `docker compose`, or any other commands on the production server.

## MCP Instructions — Architecture

The `instructions=` block in `server.py` is intentionally **lean**. It does NOT
contain the full SDK reference. Instead, it tells AIs:

1. Call `deplixo_enhance` first to identify capabilities
2. **Fetch `https://deplixo.com/sdk?format=text`** before writing any code
3. Follow the Critical Quick Reference (top 5 bugs)
4. Follow the IMPORTANT RULES and "How to replace common stubs" lists

The full SDK reference lives in `deplixo/templates/pages/sdk.txt` — that is the
**single source of truth**. The MCP instructions point to it rather than
duplicating it. This means:

- **New SDK features**: Update `sdk.txt` in the main deplixo repo. The MCP server
  picks it up automatically because AIs fetch /sdk before writing code.
- **Only update server.py when** adding:
  - A new "NEVER do X, use deplixo.Y" rule to IMPORTANT RULES
  - A new entry in "How to replace common stubs"
  - A new Critical Quick Reference item (only for top-5 bug-causing mistakes)

**The three files that must stay in sync:**
1. `deplixo/templates/pages/sdk.txt` — Authoritative SDK reference (fetched by AIs)
2. **This repo: `server.py`** — Lean MCP instructions (rules + stubs + quick ref)
3. `deplixo/js/sdk/core.js` + `legos/` — The actual SDK code

See `deplixo/CLAUDE.md` "SDK Documentation — KEEP ALL THREE IN SYNC" for the
full checklist.
