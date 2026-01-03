# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-01-04

### Added
- **Real-time Streaming Output**: See live progress during debates
  - `ai-debate run --stream` shows progress with updates as each perspective completes
  - `ai-debate run --json-stream` outputs JSON lines for automation/piping
  - Progress bars, timing, and live score updates

- **True Multi-Model Debates (MCP)**: New two-phase workflow using real Claude
  - `debate_start` - Starts debate, returns prompt for Claude's REAL analysis
  - `debate_complete` - Accepts Claude's analysis, invokes Codex, returns consensus
  - Fixes architecture where "Claude" perspective was previously fake/simulated

- **Model Provider Abstraction**: Clean interface for AI providers
  - `ModelProvider` abstract base class
  - `CodexCLIProvider` for Codex CLI subprocess invocation
  - `CopilotBridgeProvider` for VS Code Copilot Bridge
  - Auto-detection of best available provider pair

- **Streaming Event System**: Structured events for progress tracking
  - Event types: START, PROGRESS, PERSPECTIVE, CONSENSUS, COMPLETE, ERROR
  - JSON serialization for automation
  - CLI formatter for terminal display

### New Files
- `services/model_provider.py` - Abstract provider interface
- `services/stream_events.py` - Streaming event types
- `services/streaming_orchestrator.py` - Async streaming debate orchestration
- `.speckit/specs/v1.3.0_streaming_multimodel_spec.md` - Feature specification

### New MCP Tools
- `debate_start` - Phase 1: Start debate, get prompt for Claude
- `debate_complete` - Phase 2: Submit Claude's analysis, get consensus

### CLI Changes
- New flag: `--stream` / `-s` for live progress display
- New flag: `--json-stream` for JSON line output

### Breaking Changes
- None (streaming is opt-in via flags)
- Existing MCP tools continue to work

---

## [1.2.0] - 2025-01-03

### Added
- **VS Code Extensions**: Full automation for AI debates
  - `copilot-bridge/` - GitHub Copilot integration for VS Code
  - `codex-bridge/` - OpenAI Codex/ChatGPT integration for VS Code
  - HTTP bridge server on port 8765 (configurable)
  - Auto-start on VS Code startup
  - Commands for start/stop/status

### VS Code Extension Features
- **Copilot Bridge**:
  - Uses VS Code's built-in Language Model API
  - Supports multiple models (GPT-5-Codex, GPT-5, Claude Opus)
  - No external dependencies

- **Codex Bridge**:
  - Multiple integration modes (command, API, clipboard)
  - Auto-detection of best integration method
  - Requires OpenAI ChatGPT extension

### Installation
```bash
# Copilot Bridge
cd vscode-extensions/copilot-bridge
npm install && npm run compile && npm run package

# Codex Bridge
cd vscode-extensions/codex-bridge
npm install && npm run compile && npm run package
```

---

## [1.1.0] - 2025-01-03

### Added
- **MCP Server Integration**: Full MCP server for Claude Desktop
  - `ai-debate server` command to start MCP server
  - 10 MCP tools for debate orchestration
  - Stdio-based protocol for Claude integration
  - Codex CLI bridge for automated invocation
- New CLI command: `ai-debate server`
- MCP configuration file: `mcp_config.json`

### MCP Tools
- `debate_check_complexity` - Check if change requires debate
- `debate_start_session` - Start new debate session
- `debate_submit_proposal` - Submit AI proposal
- `debate_check_consensus` - Check consensus status
- `debate_override` - User override
- `debate_get_decision_pack` - Get decision pack
- `debate_start_auto` - One-command automation
- `debate_submit_codex_response` - Submit Codex response
- `debate_check_copilot_status` - Check Copilot bridge
- `debate_configure_copilot` - Configure Copilot bridge

### Configuration
Add to Claude Desktop settings (`~/.claude/settings.json`):
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

---

## [1.0.0] - 2025-01-03

### Added
- Initial release of AI Debate Tool as standalone package
- CLI tool with commands: `run`, `check`, `history`, `config`
- ParallelDebateOrchestrator for dual-AI debates
- Consensus scoring (0-100) with interpretations
- Pattern detection and learning from debate history
- Risk prediction based on historical patterns
- Debate caching with 5-minute TTL
- File-based session management
- Comprehensive documentation
- Example scripts

### Features
- **Dual-AI Debates**: Get perspectives from Claude and Codex
- **Fast Execution**: 10-18 seconds per debate
- **Zero API Costs**: Uses Codex CLI (no ongoing fees)
- **Intelligence System**: Pattern detection, risk prediction, learning
- **Caching**: Repeated requests are served from cache

---

## Roadmap

- v1.0.0: Core library + CLI
- v1.1.0: MCP server integration
- v1.2.0: VS Code extensions
- v1.3.0 (Current): Real-time streaming + True multi-model debates

---

## [Unreleased]

### Planned
- Web UI for debate visualization
- Custom debate templates
- GitHub Actions integration
- Team/organization learning from debate outcomes
