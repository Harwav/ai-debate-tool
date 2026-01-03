# MCP Server Integration

The AI Debate Tool includes an MCP (Model Context Protocol) server that integrates with Claude Desktop, enabling AI-to-AI debates directly from Claude Code.

## Installation

```bash
pip install ai-debate-tool
```

## Quick Start

### 1. Start the MCP Server

```bash
ai-debate server
```

This starts the server in stdio mode (required for Claude Desktop).

### 2. Configure Claude Desktop

Add to your Claude Desktop settings (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "ai-debate-tool": {
      "command": "ai-debate",
      "args": ["server"]
    }
  }
}
```

### 3. Restart Claude Desktop

After updating settings, restart Claude Desktop to load the MCP server.

## Available Tools

The MCP server exposes 10 tools:

### Core Tools

| Tool | Description |
|------|-------------|
| `debate_check_complexity` | Check if a code change requires debate |
| `debate_start_session` | Start a new debate session |
| `debate_submit_proposal` | Submit a proposal from Claude or Codex |
| `debate_check_consensus` | Check if consensus has been reached |
| `debate_override` | User override to proceed without consensus |
| `debate_get_decision_pack` | Get the full decision pack |

### Automation Tools

| Tool | Description |
|------|-------------|
| `debate_start_auto` | One-command to start automated debate |
| `debate_submit_codex_response` | Submit Codex's response after invocation |
| `debate_check_copilot_status` | Check Copilot bridge availability |
| `debate_configure_copilot` | Configure Copilot bridge settings |

## Usage Examples

### Check Complexity

```
Use debate_check_complexity to check if "Refactor authentication" with files ["auth.py", "users.py"] needs debate
```

### Start Automated Debate

```
Use debate_start_auto to start a debate on "Implement caching layer" affecting files ["cache.py", "db.py"]
```

### Check Consensus

```
Use debate_check_consensus with session_id "abc123" to see if we can proceed
```

## Architecture

```
Claude Code (User)
    ↓
MCP Server (ai-debate server)
    ├─→ Complexity Check
    ├─→ Session Management
    └─→ AIOrchestrator
         ├─→ Claude Analysis
         └─→ Codex Invocation
              ↓
         Consensus Calculation
              ↓
         Decision Pack
```

## Configuration

The MCP server uses the same configuration as the CLI. Initialize with:

```bash
ai-debate config --init
```

Configuration file location: `~/.config/ai-debate-tool/config.json`

## Troubleshooting

### Server Not Found

Make sure `ai-debate` is in your PATH:
```bash
which ai-debate
```

### Connection Issues

Check if the server is running:
```bash
ai-debate server -v
```

### Python Version

Requires Python 3.10+. Check with:
```bash
python --version
```
