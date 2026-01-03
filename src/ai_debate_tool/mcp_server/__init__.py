"""AI Debate Tool - MCP Server

MCP server components for Claude Code integration.

Usage:
    # As CLI command
    ai-debate server

    # As Python module
    python -m ai_debate_tool.mcp_server

    # Configure in Claude Desktop (~/.claude/settings.json)
    {
        "mcpServers": {
            "ai-debate-tool": {
                "command": "ai-debate",
                "args": ["server"]
            }
        }
    }
"""

from .debate_server import DebateMCPServer, main
from .codex_mcp_bridge import CodexMCPBridge

__all__ = ["DebateMCPServer", "CodexMCPBridge", "main"]
