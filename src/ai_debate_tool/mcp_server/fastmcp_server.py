"""AI Debate Tool - FastMCP Server

A proper MCP server using the fastmcp library for Claude Code integration.
Provides iterative debate functionality with automatic consensus iteration.

Version: 2.0.0
"""

import re
import sys
import uuid
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP(
    name="ai-debate",
    instructions="AI Debate Tool - Multi-model consensus debates with automatic iteration. Use debate_iterative for plans that need 90+ consensus."
)

# Session storage (in-memory for now)
_sessions: dict = {}


def _extract_score(text: str, default: int = 75) -> int:
    """Extract numerical score from analysis text."""
    patterns = [
        r'(?:score|confidence|challenge_score)[:\s]*(\d{1,3})\s*/\s*100',
        r'(?:score|confidence|challenge_score)[:\s]*(\d{1,3})',
        r'(\d{1,3})\s*/\s*100',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            if 0 <= score <= 100:
                return score
    return default


def _extract_concerns(codex_response: str) -> list[str]:
    """Extract concerns from Codex response."""
    concerns = []
    concerns_match = re.search(
        r'CONCERNS:\s*(.*?)(?=MISSING:|IMPROVEMENTS:|CHALLENGE_SCORE:|$)',
        codex_response,
        re.DOTALL | re.IGNORECASE
    )
    if concerns_match:
        concerns = [
            c.strip().lstrip('- ')
            for c in concerns_match.group(1).strip().split('\n')
            if c.strip() and c.strip() != '-'
        ]
    return concerns[:5]  # Top 5


def _invoke_codex(prompt: str) -> dict:
    """Invoke Codex CLI for counter-analysis."""
    try:
        # Add parent directory to path for imports
        parent_dir = Path(__file__).parent.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))

        from services.codex_cli_invoker import CodexCLIInvoker

        invoker = CodexCLIInvoker()
        result = invoker.invoke(prompt)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def debate_check_codex() -> dict:
    """Check if Codex CLI is installed and available.

    Returns status of Codex CLI installation and version info.
    """
    try:
        parent_dir = Path(__file__).parent.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))

        from services.codex_cli_invoker import CodexCLIInvoker

        invoker = CodexCLIInvoker()
        status = invoker.get_status()

        if status.get("available"):
            return {
                "available": True,
                "version": status.get("version", "unknown"),
                "model": "gpt-5.1-max",
                "message": "Codex CLI is installed and ready."
            }
        else:
            return {
                "available": False,
                "error": status.get("error", "Codex CLI not found"),
                "install_command": "npm install -g @openai/codex",
                "message": "Codex CLI is not installed."
            }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
            "install_command": "npm install -g @openai/codex"
        }


@mcp.tool()
def debate_iterative(
    request: str,
    file_path: str,
    claude_analysis: str,
    target_consensus: int = 90,
    max_iterations: int = 5,
    session_id: Optional[str] = None,
    revised_content: Optional[str] = None
) -> dict:
    """Run an iterative debate until target consensus is reached.

    This tool automatically iterates between Claude (author/reviser) and
    Codex (challenger) until the target consensus score is achieved.

    Args:
        request: Description of the code change or plan to debate
        file_path: Path to the plan/code file being debated
        claude_analysis: Your (Claude's) analysis of the current plan
        target_consensus: Target consensus score to reach (default: 90)
        max_iterations: Maximum revision cycles (default: 5)
        session_id: Session ID from previous call (for iterations 2+)
        revised_content: Your revised plan content (for iterations 2+)

    Returns:
        - If continuing: status="needs_revision", codex_concerns, current_content
        - If done: status="target_reached" or "max_iterations", final results

    Workflow:
        1. First call: Provide request, file_path, claude_analysis
        2. Tool invokes Codex for challenge, returns consensus + concerns
        3. If consensus < target: Revise plan and call again with revised_content
        4. Repeat until target reached or max iterations
    """
    global _sessions

    # Initialize or retrieve session
    if session_id is None:
        session_id = f"iter_{uuid.uuid4().hex[:8]}"

        # Read initial file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
        except FileNotFoundError:
            return {"success": False, "error": f"File not found: {file_path}"}

        _sessions[session_id] = {
            "file_path": file_path,
            "original_content": current_content,
            "target_consensus": target_consensus,
            "max_iterations": max_iterations,
            "current_iteration": 1,
            "iteration_history": [],
            "best_consensus": 0,
            "best_iteration": 0,
        }
    else:
        if session_id not in _sessions:
            return {"success": False, "error": f"Session not found: {session_id}"}

        session = _sessions[session_id]

        # Apply revision if provided
        if revised_content:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(revised_content.strip())
                current_content = revised_content.strip()
                session["current_iteration"] += 1
            except IOError as e:
                return {"success": False, "error": f"Failed to write revision: {e}"}
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                current_content = f.read()

    session = _sessions[session_id]
    current_iteration = session["current_iteration"]

    # Build Codex challenge prompt
    codex_prompt = f"""# Critical Review Request

## Context
A plan/code change has been proposed. The primary analyst (Claude) has provided their analysis.
Your role is to be a critical challenger - find weaknesses, risks, and issues.

## Original Request
{request}

## Current Plan/Code Content
```
{current_content[:4000]}{'...' if len(current_content) > 4000 else ''}
```

## Claude's Analysis
{claude_analysis}

## Your Task (Codex - Critical Challenger)
Critically review this plan. Be constructive but thorough.

Provide:
1. **Concerns**: List specific issues, risks, or weaknesses (bullet points)
2. **Missing Elements**: What's not addressed?
3. **Suggested Improvements**: Concrete recommendations
4. **Challenge Score**: How well does this plan address the requirements? (0-100)
   - 90+: Excellent, ready to proceed
   - 75-89: Good, minor improvements needed
   - 60-74: Acceptable, some concerns
   - <60: Needs significant revision

Respond in this format:
CONCERNS:
- concern 1
- concern 2

MISSING:
- missing element 1

IMPROVEMENTS:
- suggestion 1

CHALLENGE_SCORE: XX/100
"""

    # Invoke Codex
    codex_result = _invoke_codex(codex_prompt)

    if not codex_result.get("success"):
        return {
            "success": False,
            "error": f"Codex challenge failed: {codex_result.get('error')}",
            "session_id": session_id,
        }

    codex_response = codex_result.get("response", "")

    # Parse Codex response
    codex_score = _extract_score(codex_response, default=70)
    concerns = _extract_concerns(codex_response)

    # Extract Claude's score
    claude_score = _extract_score(claude_analysis, default=75)

    # Calculate consensus
    consensus = (claude_score + codex_score) // 2

    # Update session
    session["iteration_history"].append({
        "iteration": current_iteration,
        "claude_score": claude_score,
        "codex_score": codex_score,
        "consensus": consensus,
        "concerns": concerns,
    })

    if consensus > session["best_consensus"]:
        session["best_consensus"] = consensus
        session["best_iteration"] = current_iteration

    # Check if target reached
    if consensus >= target_consensus:
        return {
            "success": True,
            "status": "target_reached",
            "session_id": session_id,
            "consensus_score": consensus,
            "claude_score": claude_score,
            "codex_score": codex_score,
            "target_consensus": target_consensus,
            "total_iterations": current_iteration,
            "iteration_history": session["iteration_history"],
            "codex_response": codex_response[:2000],
            "message": f"Target consensus {target_consensus} reached! Final: {consensus}/100 in {current_iteration} iteration(s)"
        }

    # Check if max iterations reached
    if current_iteration >= max_iterations:
        return {
            "success": True,
            "status": "max_iterations",
            "session_id": session_id,
            "consensus_score": consensus,
            "claude_score": claude_score,
            "codex_score": codex_score,
            "best_consensus": session["best_consensus"],
            "best_iteration": session["best_iteration"],
            "target_consensus": target_consensus,
            "total_iterations": current_iteration,
            "iteration_history": session["iteration_history"],
            "codex_response": codex_response[:2000],
            "message": f"Max iterations ({max_iterations}) reached. Best: {session['best_consensus']}/100 at iteration {session['best_iteration']}"
        }

    # Needs revision
    return {
        "success": True,
        "status": "needs_revision",
        "session_id": session_id,
        "current_iteration": current_iteration,
        "consensus_score": consensus,
        "claude_score": claude_score,
        "codex_score": codex_score,
        "target_consensus": target_consensus,
        "remaining_iterations": max_iterations - current_iteration,
        "codex_concerns": concerns,
        "codex_response": codex_response[:2000],
        "current_content": current_content,
        "instructions": (
            f"Consensus {consensus}/100 is below target {target_consensus}/100.\n\n"
            f"Codex raised these concerns:\n" +
            "\n".join(f"  - {c}" for c in concerns) + "\n\n"
            "Please revise the plan to address these concerns, then call debate_iterative again with:\n"
            f"  - session_id: \"{session_id}\"\n"
            "  - revised_content: <your revised plan>\n"
            "  - claude_analysis: <your analysis of the revision>"
        )
    }


@mcp.tool()
def debate_single(
    request: str,
    claude_analysis: str,
    context: Optional[str] = None
) -> dict:
    """Run a single-round debate without iteration.

    Use this for quick consensus checks where iteration isn't needed.

    Args:
        request: Description of the code change or decision
        claude_analysis: Your (Claude's) analysis including recommendation and score
        context: Additional context like file contents (optional)

    Returns:
        Consensus score, both analyses, and recommendation.
    """
    # Build Codex prompt
    codex_prompt = f"""# Critical Counter-Analysis Request

You are providing an INDEPENDENT counter-perspective to another AI's analysis.

## Original Request
{request}

## Context
{context or 'No additional context provided.'}

## First Analysis (by Claude)
{claude_analysis}

## Your Task as Critical Reviewer
Provide your INDEPENDENT assessment. Be skeptical and thorough:

1. **Challenge Assumptions**: What did the first analysis assume without justification?
2. **Identify Blind Spots**: What risks or concerns were overlooked?
3. **Alternative Approaches**: Are there better ways to accomplish this?
4. **Devil's Advocate**: What could go wrong that wasn't considered?

End with:
- **Your Recommendation**: PROCEED / REVIEW / REJECT
- **Your Confidence Score**: X/100
"""

    # Invoke Codex
    codex_result = _invoke_codex(codex_prompt)

    if not codex_result.get("success"):
        return {
            "success": False,
            "error": f"Codex invocation failed: {codex_result.get('error')}",
            "claude_analysis_received": True
        }

    codex_response = codex_result.get("response", "")

    # Extract scores
    claude_score = _extract_score(claude_analysis, default=75)
    codex_score = _extract_score(codex_response, default=75)
    consensus = (claude_score + codex_score) // 2

    # Determine recommendation
    if consensus >= 85:
        recommendation = "PROCEED"
        interpretation = "Strong agreement - proceed confidently"
    elif consensus >= 70:
        recommendation = "PROCEED with modifications"
        interpretation = "Moderate agreement - address key concerns"
    elif consensus >= 50:
        recommendation = "REVIEW"
        interpretation = "Significant disagreements - discuss and resolve"
    else:
        recommendation = "REJECT"
        interpretation = "Fundamental disagreements - reconsider approach"

    return {
        "success": True,
        "consensus_score": consensus,
        "interpretation": interpretation,
        "recommendation": recommendation,
        "can_proceed": consensus >= 70,
        "claude": {
            "score": claude_score,
            "excerpt": claude_analysis[:500] + "..." if len(claude_analysis) > 500 else claude_analysis
        },
        "codex": {
            "score": codex_score,
            "response": codex_response[:1500] + "..." if len(codex_response) > 1500 else codex_response
        }
    }


# Run the server
if __name__ == "__main__":
    mcp.run()
