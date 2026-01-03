# AI Debate Tool

**AI-to-AI debate orchestration for better decision-making.**

[![CI](https://github.com/ai-debate-tool/ai-debate-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/ai-debate-tool/ai-debate-tool/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/ai-debate-tool.svg)](https://badge.fury.io/py/ai-debate-tool)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## What is this?

AI Debate Tool orchestrates debates between multiple AI perspectives (Claude + Codex) to help make better decisions on complex code changes, architectural decisions, and implementation plans.

**Key Features:**
- **Dual-AI debates** - Get diverse perspectives from Claude and Codex
- **Consensus scoring** - 0-100 score indicating agreement level
- **Fast execution** - 10-18 seconds per debate
- **Pattern learning** - Improves recommendations over time
- **Zero API costs** - Uses Codex CLI (no ongoing fees)

---

## Installation

```bash
pip install ai-debate-tool
```

### Requirements
- Python 3.10+
- [Codex CLI](https://openai.com/codex) installed and authenticated

---

## Quick Start

### CLI Usage

```bash
# Run a debate on a plan file
ai-debate run "Review this refactoring plan" --file plans/refactor.md

# Check if a change needs debate (complexity scoring)
ai-debate check "Add caching layer" --files cache.py db.py

# View debate history
ai-debate history --limit 5

# Initialize configuration
ai-debate config --init
```

### Python API

```python
import asyncio
from ai_debate_tool import get_orchestrator

async def main():
    # Create orchestrator
    Orchestrator = get_orchestrator()
    orchestrator = Orchestrator(enable_cache=True, enable_intelligence=True)

    # Run a debate
    result = await orchestrator.run_debate(
        request="Review this refactoring plan",
        file_path="plans/refactor.md",
        focus_areas=["architecture", "testing"]
    )

    # Check results
    print(f"Consensus: {result['debate_result']['consensus_score']}/100")
    print(f"Recommendation: {result['debate_result']['recommendation']}")

asyncio.run(main())
```

### Check If Debate Is Needed

```python
from ai_debate_tool import check_debate_required

result = check_debate_required(
    request="Refactor authentication module",
    file_paths=["auth/views.py", "auth/models.py"]
)

if result["required"]:
    print(f"Debate recommended (complexity: {result['complexity_score']})")
else:
    print("Simple change, proceed without debate")
```

---

## CLI Reference

### `ai-debate run`

Run a debate on a topic/file.

```bash
ai-debate run <topic> --file <path> [options]

Options:
  -f, --file PATH      Path to file to debate (required)
  -F, --focus TEXT     Focus areas (can specify multiple)
  -t, --target INT     Target consensus score (default: 75)
  -o, --output PATH    Save results to JSON file
  -v, --verbose        Verbose output
```

**Examples:**
```bash
# Basic debate
ai-debate run "Review this API design" --file api_spec.md

# With focus areas
ai-debate run "Check security implications" --file auth.py -F security -F validation

# Save results
ai-debate run "Architecture review" --file design.md -o results.json -v
```

### `ai-debate check`

Check if a change requires debate (complexity scoring).

```bash
ai-debate check <request> [options]

Options:
  -f, --files TEXT     Files to check (can specify multiple)
  -t, --threshold INT  Complexity threshold (default: 40)
  --json               Output as JSON
```

**Examples:**
```bash
ai-debate check "Add user authentication" --files auth.py models.py
ai-debate check "Fix typo in README" --threshold 20
```

### `ai-debate history`

View debate history.

```bash
ai-debate history [options]

Options:
  -n, --limit INT  Number of entries (default: 10)
  --stats          Show statistics only
  --json           Output as JSON
```

### `ai-debate config`

Manage configuration.

```bash
ai-debate config [options]

Options:
  --init   Initialize configuration file
  --show   Show current configuration
  --path   Show config file path
```

### `ai-debate server`

Start the MCP server for Claude Desktop integration.

```bash
ai-debate server [options]

Options:
  -v, --verbose  Verbose output
```

---

## MCP Server Integration

The AI Debate Tool includes an MCP server for Claude Desktop integration.

### Quick Setup

1. Add to Claude Desktop settings (`~/.claude/settings.json`):
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

2. Restart Claude Desktop

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `debate_check_complexity` | Check if change requires debate |
| `debate_start_auto` | Start automated debate |
| `debate_submit_codex_response` | Submit Codex response |
| `debate_check_consensus` | Check consensus status |
| `debate_get_decision_pack` | Get full decision pack |

See [docs/mcp-server.md](docs/mcp-server.md) for full documentation.

---

## How It Works

```
1. INPUT
   └── Your request + file path + optional focus areas

2. PRE-DEBATE ANALYSIS
   ├── Pattern detection from history
   ├── Risk prediction
   └── Suggested focus areas

3. PARALLEL DEBATE
   ├── Claude perspective (via Codex CLI)
   └── Codex perspective (via Codex CLI)

4. CONSENSUS ANALYSIS
   └── Score agreement, identify disagreements

5. OUTPUT
   └── Consensus score + recommendations + insights
```

---

## Consensus Scores

| Score | Interpretation | Recommendation |
|-------|----------------|----------------|
| 90-100 | Strong Agreement | Proceed confidently |
| 75-89 | Good Agreement | Proceed with minor review |
| 60-74 | Moderate Agreement | Discuss key points first |
| 40-59 | Mixed Views | Significant discussion needed |
| 0-39 | Strong Disagreement | Major concerns to address |

---

## Configuration

Create a config file with `ai-debate config --init`:

```json
{
  "enabled": true,
  "complexity_threshold": 40,
  "target_consensus": 75,
  "max_rounds": 5,
  "enable_cache": true,
  "enable_intelligence": true,
  "log_level": "INFO"
}
```

Or use environment variables:
- `ENABLE_AI_DEBATE` - Enable/disable debates
- `DEBATE_COMPLEXITY_THRESHOLD` - Minimum complexity for debate
- `DEBATE_TARGET_CONSENSUS` - Target consensus score

---

## Roadmap

- **v1.0.0**: Core library + CLI
- **v1.1.0** (Current): MCP server integration
- **v1.2.0** (Planned): VS Code extensions

---

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Clone the repo
git clone https://github.com/ai-debate-tool/ai-debate-tool.git
cd ai-debate-tool

# Install in development mode
pip install -e .[dev]

# Run tests
pytest --cov

# Format code
black src/
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Links

- [GitHub Repository](https://github.com/ai-debate-tool/ai-debate-tool)
- [Issue Tracker](https://github.com/ai-debate-tool/ai-debate-tool/issues)
- [Changelog](CHANGELOG.md)
