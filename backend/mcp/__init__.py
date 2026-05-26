"""OneiroScope MCP server.

Canonical tool surface for the OneiroScope domain (astrology, dreams, lunar,
geo). Consumed by the ADK agent and Claude Code skills. Wraps the internal
FastAPI services (`backend/services/*`) — does not call them over HTTP.

Run:
    python -m backend.mcp.server            # stdio (Claude Desktop, Cursor)
    python -m backend.mcp.server --http     # HTTP transport (remote agents)
"""
