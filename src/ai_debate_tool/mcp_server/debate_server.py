"""AI Debate Tool - MCP Server

MCP server that exposes AI debate tools to Claude Code.
Allows triggering debates, checking complexity, and managing debate sessions.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_debate_tool import (
    check_debate_required,
    create_session_directory,
    block_execution_until_consensus,
    mark_user_override,
    write_proposal,
    read_proposal,
    write_metadata,
    read_metadata,
)
from ai_debate_tool.services.ai_orchestrator import AIOrchestrator
from ai_debate_tool.services.copilot_invoker import CopilotInvoker, CopilotConfig


class DebateMCPServer:
    """MCP server for AI debate orchestration."""

    def __init__(self):
        self.tools = {
            "debate_check_complexity": self.check_complexity,
            "debate_start_session": self.start_session,
            "debate_submit_proposal": self.submit_proposal,
            "debate_check_consensus": self.check_consensus,
            "debate_override": self.user_override,
            "debate_get_decision_pack": self.get_decision_pack,
            # Phase 7.1: Manual automation tools
            "debate_start_auto": self.start_auto,
            "debate_submit_codex_response": self.submit_codex_response,
            # Phase 7.2: Full automation tools
            "debate_check_copilot_status": self.check_copilot_status,
            "debate_configure_copilot": self.configure_copilot,
        }

    def check_complexity(self, request: str, file_paths: List[str]) -> Dict[str, Any]:
        """Check if a code change requires debate.

        Args:
            request: Description of the code change
            file_paths: List of file paths that will be modified

        Returns:
            Dictionary with complexity analysis
        """
        result = check_debate_required(request=request, file_paths=file_paths)
        return {
            "success": True,
            "complexity_score": result["complexity_score"],
            "debate_required": result["required"],
            "reason": result["reason"],
            "threshold": 40,  # Default threshold
        }

    def start_session(self, session_id: str, request: str, file_paths: List[str]) -> Dict[str, Any]:
        """Start a new debate session.

        Args:
            session_id: Unique identifier for this debate session
            request: Description of the code change
            file_paths: List of file paths that will be modified

        Returns:
            Dictionary with session information
        """
        try:
            # Create session directory
            result = create_session_directory(session_id)

            if not result["success"]:
                return {
                    "success": False,
                    "error": result.get("error", "Failed to create session"),
                }

            session_path = Path(result["path"])

            # Update metadata with request context
            metadata = read_metadata(session_path)["metadata"]
            metadata["request"] = request
            metadata["file_paths"] = file_paths
            metadata["state"] = "ROUND_1"
            metadata["current_round"] = 1
            write_metadata(session_path, metadata)

            return {
                "success": True,
                "session_id": session_id,
                "session_path": str(session_path),
                "message": "Debate session created. Ready for proposals.",
                "next_steps": [
                    "Claude Code submits proposal (debate_submit_proposal)",
                    "Codex submits proposal (debate_submit_proposal)",
                    "Check consensus (debate_check_consensus)",
                ],
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def submit_proposal(
        self, session_id: str, ai_name: str, round_num: int, proposal: str
    ) -> Dict[str, Any]:
        """Submit a proposal from an AI to the debate session.

        Args:
            session_id: Debate session identifier
            ai_name: Name of AI submitting ("claude" or "codex")
            round_num: Debate round number
            proposal: The proposal text (markdown format)

        Returns:
            Dictionary with submission confirmation
        """
        try:
            # Find session directory
            from ai_debate_tool.file_protocol import get_hashed_user
            from ai_debate_tool.config import load_config

            config = load_config()
            user_hash = get_hashed_user()
            session_dir = config.temp_dir / "ai_debates" / user_hash / session_id

            if not session_dir.exists():
                return {
                    "success": False,
                    "error": f"Session {session_id} not found",
                }

            # Write proposal
            result = write_proposal(session_dir, ai_name, round_num, proposal)

            if result["success"]:
                return {
                    "success": True,
                    "session_id": session_id,
                    "ai_name": ai_name,
                    "round": round_num,
                    "sequence": result["sequence"],
                    "message": f"{ai_name.capitalize()} proposal submitted successfully",
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Failed to write proposal"),
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_consensus(self, session_id: str) -> Dict[str, Any]:
        """Check if consensus has been reached in the debate.

        Args:
            session_id: Debate session identifier

        Returns:
            Dictionary with consensus status
        """
        try:
            from ai_debate_tool.file_protocol import get_hashed_user
            from ai_debate_tool.config import load_config

            config = load_config()
            user_hash = get_hashed_user()
            session_dir = config.temp_dir / "ai_debates" / user_hash / session_id

            gate = block_execution_until_consensus(session_id, session_dir)

            return {
                "success": True,
                "can_execute": gate["can_execute"],
                "consensus_score": gate.get("consensus_score"),
                "user_override": gate.get("user_override", False),
                "decision_pack": gate.get("decision_pack"),
                "error": gate.get("error"),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def user_override(self, session_id: str) -> Dict[str, Any]:
        """User manually overrides debate requirement and allows execution.

        Args:
            session_id: Debate session identifier

        Returns:
            Dictionary with override confirmation
        """
        try:
            from ai_debate_tool.file_protocol import get_hashed_user
            from ai_debate_tool.config import load_config

            config = load_config()
            user_hash = get_hashed_user()
            session_dir = config.temp_dir / "ai_debates" / user_hash / session_id

            result = mark_user_override(session_id, session_dir)

            if result["success"]:
                return {
                    "success": True,
                    "session_id": session_id,
                    "message": "User override marked. Execution allowed.",
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Failed to mark override"),
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_decision_pack(self, session_id: str) -> Dict[str, Any]:
        """Get the decision pack for a debate session.

        Args:
            session_id: Debate session identifier

        Returns:
            Dictionary with decision pack details
        """
        try:
            from ai_debate_tool.file_protocol import get_hashed_user
            from ai_debate_tool.config import load_config

            config = load_config()
            user_hash = get_hashed_user()
            session_dir = config.temp_dir / "ai_debates" / user_hash / session_id

            if not session_dir.exists():
                return {
                    "success": False,
                    "error": f"Session {session_id} not found",
                }

            # Read metadata
            metadata_result = read_metadata(session_dir)
            if not metadata_result["success"]:
                return {
                    "success": False,
                    "error": "Failed to read session metadata",
                }

            metadata = metadata_result["metadata"]

            # Read proposals
            claude_proposal = read_proposal(session_dir, "claude", metadata["current_round"])
            codex_proposal = read_proposal(session_dir, "codex", metadata["current_round"])

            return {
                "success": True,
                "session_id": session_id,
                "request": metadata.get("request", "N/A"),
                "state": metadata.get("state", "UNKNOWN"),
                "consensus_score": metadata.get("consensus_score", 0),
                "rounds": metadata.get("current_round", 0),
                "claude_proposal": claude_proposal.get("content") if claude_proposal["success"] else None,
                "codex_proposal": codex_proposal.get("content") if codex_proposal["success"] else None,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def start_auto(
        self,
        request: str,
        file_paths: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Start automated debate (Phase 7 main entry point).

        This is the one-command automation tool that:
        1. Checks complexity
        2. Creates session
        3. Generates Claude proposal
        4. Generates Codex prompt
        5. Returns everything needed for manual Codex invocation

        Args:
            request: Description of code change
            file_paths: List of files affected (optional)
            context: Additional context dict (optional)

        Returns:
            Dictionary with debate session info and Codex prompt
        """
        try:
            orchestrator = AIOrchestrator()
            result = orchestrator.start_debate_auto(
                request=request,
                file_paths=file_paths,
                context=context
            )
            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to start automated debate: {str(e)}"
            }

    def submit_codex_response(
        self,
        session_id: str,
        codex_response: str
    ) -> Dict[str, Any]:
        """Submit Codex's response after manual invocation.

        After user copies Codex prompt and pastes response from Codex,
        this tool processes the response and calculates consensus.

        Args:
            session_id: Debate session ID (from start_auto)
            codex_response: Codex's counter-proposal text

        Returns:
            Dictionary with consensus analysis and decision pack
        """
        try:
            orchestrator = AIOrchestrator()
            result = orchestrator.submit_codex_response(
                session_id=session_id,
                codex_response=codex_response
            )
            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to submit Codex response: {str(e)}"
            }

    def check_copilot_status(self) -> Dict[str, Any]:
        """Check Copilot bridge availability (Phase 7.2).

        Checks if VS Code Copilot Bridge extension is running and
        accessible for automatic invocation.

        Returns:
            Dictionary with Copilot bridge status
        """
        try:
            copilot = CopilotInvoker()
            status = copilot.get_status()

            return {
                "success": True,
                "available": status['available'],
                "endpoint": status['endpoint'],
                "model": status['model'],
                "error": status['error'],
                "message": "Copilot bridge is available" if status['available']
                          else "Copilot bridge not running. Start VS Code with Copilot Bridge extension.",
                "setup_instructions": [
                    "1. Install Copilot Bridge extension in VS Code",
                    "2. Start VS Code (bridge auto-starts)",
                    "3. Verify GitHub Copilot Pro+ subscription is active",
                    "4. Check this status again to confirm"
                ] if not status['available'] else []
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to check Copilot status: {str(e)}"
            }

    def configure_copilot(
        self,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        enable_auto: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Configure Copilot bridge settings (Phase 7.2).

        Configures endpoint, model preference, and auto-invoke settings.

        Args:
            endpoint: Copilot bridge endpoint (default: http://localhost:8765)
            model: Preferred model (default: gpt-5-codex)
            enable_auto: Enable automatic invocation (default: True)

        Returns:
            Dictionary with configuration confirmation
        """
        try:
            # Build configuration
            config_updates = {}
            if endpoint is not None:
                config_updates['endpoint'] = endpoint
            if model is not None:
                config_updates['model'] = model
            if enable_auto is not None:
                config_updates['enable_auto'] = enable_auto

            # Create config with new settings
            copilot_config = CopilotConfig(
                endpoint=endpoint or "http://localhost:8765",
                model=model or "gpt-5-codex"
            )

            # Test connection
            copilot = CopilotInvoker(copilot_config)
            status = copilot.get_status()

            return {
                "success": True,
                "configuration": {
                    "endpoint": copilot_config.endpoint,
                    "model": copilot_config.model,
                    "timeout": copilot_config.timeout,
                    "max_retries": copilot_config.max_retries,
                    "auto_invoke_enabled": enable_auto if enable_auto is not None else True
                },
                "bridge_available": status['available'],
                "message": "Configuration updated successfully",
                "note": "Configuration is per-session. Set enable_auto_codex=True when creating AIOrchestrator."
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to configure Copilot: {str(e)}"
            }

    def handle_request(self, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP tool request.

        Args:
            tool: Tool name
            params: Tool parameters

        Returns:
            Tool result
        """
        if tool not in self.tools:
            return {
                "success": False,
                "error": f"Unknown tool: {tool}",
                "available_tools": list(self.tools.keys()),
            }

        try:
            handler = self.tools[tool]
            result = handler(**params)
            return result
        except TypeError as e:
            return {
                "success": False,
                "error": f"Invalid parameters for {tool}: {str(e)}",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


def main():
    """MCP server main loop."""
    server = DebateMCPServer()

    # Read requests from stdin (MCP protocol)
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            tool = request.get("tool")
            params = request.get("params", {})

            result = server.handle_request(tool, params)

            # Write response to stdout (MCP protocol)
            print(json.dumps(result))
            sys.stdout.flush()

        except json.JSONDecodeError:
            error_response = {
                "success": False,
                "error": "Invalid JSON request",
            }
            print(json.dumps(error_response))
            sys.stdout.flush()
        except Exception as e:
            error_response = {
                "success": False,
                "error": f"Server error: {str(e)}",
            }
            print(json.dumps(error_response))
            sys.stdout.flush()


if __name__ == "__main__":
    main()
