"""AI Debate Tool - Standalone Package

Orchestrates debates between multiple AI perspectives before code execution.
Ensures diverse expert AI perspectives review complex changes before they're implemented.

Usage:
    from ai_debate_tool import check_debate_required, block_execution_until_consensus

    # Check if debate needed
    result = check_debate_required(
        request="Refactor authentication",
        file_paths=["auth/views.py"]
    )

    if result["required"]:
        # Start debate and check consensus
        session_id = start_debate(request, file_paths)
        gate = block_execution_until_consensus(session_id)

        if gate["can_execute"]:
            # Proceed with execution
            pass

CLI Usage:
    ai-debate run "Review this plan" --file plans/refactor.md
    ai-debate check "Add caching" --files cache.py db.py
    ai-debate history --limit 5
    ai-debate config --init
"""

__version__ = "1.1.0"
__author__ = "AI Debate Tool Contributors"
__license__ = "MIT"

from .enforcement_gate import (
    check_debate_required,
    block_execution_until_consensus,
    mark_user_override,
)
from .file_protocol import (
    create_session_directory,
    write_proposal,
    read_proposal,
    write_metadata,
    read_metadata,
    cleanup_old_sessions,
)
from .config import load_config, DebateConfig

# Lazy import for heavy services
def get_orchestrator():
    """Get the ParallelDebateOrchestrator (lazy import)."""
    from .services.parallel_debate_orchestrator import ParallelDebateOrchestrator
    return ParallelDebateOrchestrator

def get_ai_orchestrator():
    """Get the AIOrchestrator for automation (lazy import)."""
    from .services.ai_orchestrator import AIOrchestrator
    return AIOrchestrator

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__license__",
    # Enforcement Gate
    "check_debate_required",
    "block_execution_until_consensus",
    "mark_user_override",
    # File Protocol
    "create_session_directory",
    "write_proposal",
    "read_proposal",
    "write_metadata",
    "read_metadata",
    "cleanup_old_sessions",
    # Configuration
    "load_config",
    "DebateConfig",
    # Factory functions
    "get_orchestrator",
    "get_ai_orchestrator",
]
