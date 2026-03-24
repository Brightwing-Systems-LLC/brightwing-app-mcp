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

## MCP Instructions & Tool Docstring — KEEP IN SYNC

The `instructions=` block and `deplixo_deploy` tool docstring in `server.py` are
the **single source of truth** for what AI clients (Claude, ChatGPT, etc.) know
about the Deplixo SDK when using the MCP connector. If an AI doesn't know about
a feature, it won't use it.

**CRITICAL: This file is ONE of THREE places that MUST be updated when the SDK
changes.** The other two are in the main deplixo repo — see the "SDK
Documentation — KEEP ALL THREE IN SYNC" section in `deplixo/CLAUDE.md`. A
feature that exists in code but not in docs is invisible to AI builders.

**The three files:**
1. `deplixo/templates/pages/sdk.txt` — Public SDK reference at `deplixo.com/sdk/`
   (what AIs read when users point them at the URL)
2. **This repo: `server.py`** — MCP instructions + tool docstring (what AIs see
   via the MCP connector)
3. `deplixo/js/sdk/core.js` + `legos/` — The actual SDK code

**Whenever a new SDK feature ships in the main deplixo repo**, the MCP server
MUST be updated:

1. Add the new SDK surface to the tool docstring (3-5 lines + one example)
2. Add a "NEVER do X, use deplixo.Y instead" rule if applicable
3. Update the `instructions=` "How to replace common stubs" list if the new
   feature replaces a common stub pattern
4. Test by asking an AI to build an app that would use the new feature
5. Verify the AI generates correct SDK calls

The docstring has these sections that need updating:
- **SDK reference** (Collections, Uploads, Identity, Proxy, AI) — add new APIs here
- **Real-Time Best Practices** — patterns for onChange, reconnect handling, no optimistic rendering
- **Making Apps Functional** (NEVER/ALWAYS rules, examples) — add new patterns
- **IMPORTANT RULES** — add new "NEVER X / ALWAYS Y" rules
- **Two patterns** (Personal vs Multi-User) — update if data model changes

The `instructions=` block has:
- **"How to replace common stubs"** — add new stub→primitive mappings
- **"Before building, ask clarifying questions"** — update if new features change what to ask
