"""MCP server of the farmer advisor (thin wrapper over ``advisor``). Run: uv run python -m mcp_server"""

from mcp_server.server import server

__all__ = ["server"]
