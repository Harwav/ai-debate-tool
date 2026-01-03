"""AI Debate Tool CLI

Command-line interface for running AI-to-AI debates.

Usage:
    ai-debate run <topic> --file <path>    Run a debate on a topic
    ai-debate check <request> --files ...  Check if debate is needed
    ai-debate history --limit N            View debate history
    ai-debate config --init                Initialize configuration
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click

from . import __version__
from .config import DebateConfig, load_config
from .enforcement_gate import check_debate_required


@click.group()
@click.version_option(version=__version__, prog_name="ai-debate")
def main():
    """AI Debate Tool - AI-to-AI debate orchestration for better decisions."""
    pass


@main.command()
@click.argument("topic")
@click.option("--file", "-f", "file_path", required=True, help="Path to file to debate")
@click.option("--focus", "-F", multiple=True, help="Focus areas (can specify multiple)")
@click.option("--target", "-t", default=75, help="Target consensus score (default: 75)")
@click.option("--output", "-o", help="Output file for results (JSON)")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def run(topic: str, file_path: str, focus: tuple, target: int, output: Optional[str], verbose: bool):
    """Run a debate on a topic.

    Example:
        ai-debate run "Review this refactoring plan" --file plans/refactor.md
    """
    from .services.parallel_debate_orchestrator import ParallelDebateOrchestrator

    # Verify file exists
    path = Path(file_path)
    if not path.exists():
        click.echo(f"Error: File not found: {file_path}", err=True)
        sys.exit(1)

    async def run_debate():
        orchestrator = ParallelDebateOrchestrator(
            enable_cache=True,
            enable_intelligence=True
        )

        focus_areas = list(focus) if focus else None

        if verbose:
            click.echo(f"Running debate on: {topic}")
            click.echo(f"File: {file_path}")
            if focus_areas:
                click.echo(f"Focus areas: {', '.join(focus_areas)}")

        result = await orchestrator.run_debate(
            request=topic,
            file_path=str(path.absolute()),
            focus_areas=focus_areas
        )

        return result

    try:
        result = asyncio.run(run_debate())

        # Display results
        debate = result.get("debate_result", {})
        stats = result.get("performance_stats", {})

        click.echo("\n" + "=" * 60)
        click.echo("AI DEBATE RESULTS")
        click.echo("=" * 60)

        consensus = debate.get("consensus_score", 0)
        click.echo(f"\nConsensus Score: {consensus}/100")
        click.echo(f"Interpretation: {debate.get('interpretation', 'N/A')}")
        click.echo(f"Recommendation: {debate.get('recommendation', 'N/A')}")

        # Claude perspective
        claude = debate.get("claude", {})
        click.echo(f"\n--- Claude Perspective ({claude.get('score', 'N/A')}/100) ---")
        if verbose and claude.get("summary"):
            click.echo(claude["summary"][:500])

        # Codex perspective
        codex = debate.get("codex", {})
        click.echo(f"\n--- Codex Perspective ({codex.get('score', 'N/A')}/100) ---")
        if verbose and codex.get("summary"):
            click.echo(codex["summary"][:500])

        # Performance stats
        if verbose:
            click.echo(f"\n--- Performance ---")
            click.echo(f"Total time: {stats.get('total_time', 0):.1f}s")
            click.echo(f"Cache hit: {stats.get('cache_hit', False)}")

        # Save to file if requested
        if output:
            output_path = Path(output)
            with open(output_path, "w") as f:
                json.dump(result, f, indent=2, default=str)
            click.echo(f"\nResults saved to: {output}")

        # Exit with appropriate code
        if consensus >= target:
            click.echo(f"\n[PASS] Consensus ({consensus}) meets target ({target})")
            sys.exit(0)
        else:
            click.echo(f"\n[BELOW TARGET] Consensus ({consensus}) below target ({target})")
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error running debate: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.argument("request")
@click.option("--files", "-f", multiple=True, help="Files to check (can specify multiple)")
@click.option("--threshold", "-t", default=40, help="Complexity threshold (default: 40)")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def check(request: str, files: tuple, threshold: int, json_output: bool):
    """Check if a change requires a debate.

    Returns complexity score and recommendation.

    Example:
        ai-debate check "Add caching layer" --files cache.py db.py
    """
    file_paths = list(files) if files else []

    result = check_debate_required(
        request=request,
        file_paths=file_paths
    )

    if json_output:
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"\nRequest: {request}")
        click.echo(f"Files: {', '.join(file_paths) if file_paths else 'None specified'}")
        click.echo(f"\nComplexity Score: {result.get('complexity_score', 0)}/100")
        click.echo(f"Threshold: {threshold}")

        if result.get("required", False):
            click.echo("\n[DEBATE RECOMMENDED] This change is complex enough to benefit from AI debate.")
        else:
            click.echo("\n[PROCEED] This change is simple enough to proceed without debate.")

        if result.get("reasons"):
            click.echo("\nReasons:")
            for reason in result["reasons"]:
                click.echo(f"  - {reason}")

    # Exit 0 if debate not required, 1 if required
    sys.exit(1 if result.get("required", False) else 0)


@main.command()
@click.option("--limit", "-n", default=10, help="Number of entries to show")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.option("--stats", is_flag=True, help="Show statistics only")
def history(limit: int, json_output: bool, stats: bool):
    """View debate history.

    Example:
        ai-debate history --limit 5
        ai-debate history --stats
    """
    from .services.debate_history_manager import DebateHistoryManager

    try:
        manager = DebateHistoryManager()

        if stats:
            statistics = manager.get_statistics()
            if json_output:
                click.echo(json.dumps(statistics, indent=2))
            else:
                click.echo("\n=== Debate Statistics ===")
                click.echo(f"Total debates: {statistics.get('total_debates', 0)}")
                click.echo(f"Average consensus: {statistics.get('average_consensus', 0):.1f}")
                click.echo(f"Success rate: {statistics.get('success_rate', 0):.1%}")
        else:
            debates = manager.get_recent_debates(limit=limit)

            if json_output:
                click.echo(json.dumps(debates, indent=2, default=str))
            else:
                click.echo(f"\n=== Recent Debates (last {limit}) ===\n")

                if not debates:
                    click.echo("No debates found.")
                else:
                    for debate in debates:
                        click.echo(f"ID: {debate.get('debate_id', 'N/A')}")
                        click.echo(f"  Request: {debate.get('request', 'N/A')[:50]}...")
                        click.echo(f"  Consensus: {debate.get('consensus_score', 'N/A')}/100")
                        click.echo(f"  Time: {debate.get('timestamp', 'N/A')}")
                        click.echo(f"  Outcome: {debate.get('outcome', 'pending')}")
                        click.echo()

    except Exception as e:
        click.echo(f"Error reading history: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--port", "-p", default=None, type=int, help="Port for HTTP mode (default: stdio)")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def server(port: Optional[int], verbose: bool):
    """Start the MCP server.

    By default, runs in stdio mode for Claude Desktop integration.
    Use --port to run in HTTP mode for debugging.

    Example:
        ai-debate server              # Stdio mode (for Claude Desktop)
        ai-debate server --port 8080  # HTTP mode (for debugging)
    """
    from .mcp_server import main as mcp_main

    if port:
        click.echo(f"HTTP mode not yet implemented. Use stdio mode.", err=True)
        sys.exit(1)

    if verbose:
        click.echo("Starting MCP server in stdio mode...", err=True)

    # Run MCP server
    mcp_main()


@main.command()
@click.option("--init", "do_init", is_flag=True, help="Initialize configuration")
@click.option("--show", is_flag=True, help="Show current configuration")
@click.option("--path", is_flag=True, help="Show config file path")
def config(do_init: bool, show: bool, path: bool):
    """Manage configuration.

    Example:
        ai-debate config --init
        ai-debate config --show
    """
    config_path = Path.home() / ".config" / "ai-debate-tool" / "config.json"

    if path:
        click.echo(str(config_path))
        return

    if do_init:
        # Create default configuration
        config_path.parent.mkdir(parents=True, exist_ok=True)

        default_config = {
            "enabled": True,
            "complexity_threshold": 40,
            "target_consensus": 75,
            "max_rounds": 5,
            "enable_cache": True,
            "enable_intelligence": True,
            "log_level": "INFO"
        }

        with open(config_path, "w") as f:
            json.dump(default_config, f, indent=2)

        click.echo(f"Configuration initialized at: {config_path}")
        click.echo("\nDefault settings:")
        for key, value in default_config.items():
            click.echo(f"  {key}: {value}")
        return

    if show:
        if config_path.exists():
            with open(config_path) as f:
                current_config = json.load(f)
            click.echo(json.dumps(current_config, indent=2))
        else:
            click.echo("No configuration file found. Run 'ai-debate config --init' to create one.")
            # Show default values
            cfg = DebateConfig()
            click.echo("\nUsing defaults:")
            click.echo(f"  enabled: {cfg.enabled}")
            click.echo(f"  complexity_threshold: {cfg.complexity_threshold}")
            click.echo(f"  target_consensus: {cfg.target_consensus}")
        return

    # Default: show help
    click.echo("Use --init to initialize, --show to display, or --path to show config location.")


if __name__ == "__main__":
    main()
