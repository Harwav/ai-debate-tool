"""Codex CLI MCP Bridge

This MCP server bridges Python ↔ Codex CLI for 100% automated AI debates.

Architecture:
    Python → Codex CLI → Codex AI → Response back to Python

How it works:
1. Python sends prompt via this MCP bridge
2. MCP bridge invokes Codex CLI: `codex ask <prompt>`
3. Codex CLI invokes Codex AI (using user's subscription)
4. Response flows back: Codex → CLI → MCP → Python

Configuration:
    Add to ~/.codex/config.toml:
    [[mcp_servers]]
    name = "debate-bridge"
    command = "python"
    args = ["-m", "ai_debate_tool.mcp_server.codex_mcp_bridge"]

Usage:
    # From Codex CLI
    codex mcp list  # Should show "debate-bridge"

    # From Python
    from ai_debate_tool.services.codex_cli_invoker import CodexCLIInvoker
    invoker = CodexCLIInvoker()
    result = invoker.invoke("Write a Python function...")
"""

import sys
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any


class CodexMCPBridge:
    """MCP bridge for Codex CLI invocation."""

    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "codex_mcp_bridge"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def invoke_codex_cli(self, prompt: str, timeout: int = 120) -> Dict[str, Any]:
        """Invoke Codex CLI with a prompt.

        Args:
            prompt: The prompt to send to Codex
            timeout: Timeout in seconds (default: 120)

        Returns:
            Dictionary with:
                - success (bool): Invocation successful
                - response (str): Codex's response
                - error (str): Error message if failed
        """
        try:
            # Write prompt to temp file (Codex CLI can read from stdin or file)
            prompt_file = self.temp_dir / "prompt.txt"
            prompt_file.write_text(prompt, encoding='utf-8')

            # Invoke Codex CLI
            # Method 1: Try interactive mode with prompt file
            result = subprocess.run(
                ['codex', 'ask', '--prompt-file', str(prompt_file)],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8'
            )

            if result.returncode == 0:
                response = result.stdout.strip()

                # Clean up temp file
                try:
                    prompt_file.unlink()
                except Exception:
                    pass

                return {
                    'success': True,
                    'response': response,
                    'error': None
                }
            else:
                # Try alternative method: pass prompt via stdin
                result = subprocess.run(
                    ['codex', 'ask'],
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding='utf-8'
                )

                if result.returncode == 0:
                    response = result.stdout.strip()

                    # Clean up temp file
                    try:
                        prompt_file.unlink()
                    except Exception:
                        pass

                    return {
                        'success': True,
                        'response': response,
                        'error': None
                    }
                else:
                    return {
                        'success': False,
                        'response': '',
                        'error': f"Codex CLI failed: {result.stderr}"
                    }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'response': '',
                'error': f"Codex CLI timed out after {timeout} seconds"
            }
        except FileNotFoundError:
            return {
                'success': False,
                'response': '',
                'error': "Codex CLI not found. Install with: npm install -g @openai/codex"
            }
        except Exception as e:
            return {
                'success': False,
                'response': '',
                'error': f"Error invoking Codex CLI: {str(e)}"
            }

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP request from Codex CLI.

        Args:
            request: MCP request dictionary with:
                - method (str): "invoke"
                - params (dict): {"prompt": "..."}

        Returns:
            MCP response dictionary
        """
        method = request.get('method')
        params = request.get('params', {})

        if method == 'invoke':
            prompt = params.get('prompt')
            if not prompt:
                return {
                    'success': False,
                    'error': 'Missing prompt parameter'
                }

            result = self.invoke_codex_cli(prompt)
            return result

        elif method == 'health':
            # Health check
            try:
                result = subprocess.run(
                    ['codex', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    version = result.stdout.strip()
                    return {
                        'success': True,
                        'available': True,
                        'version': version
                    }
                else:
                    return {
                        'success': False,
                        'available': False,
                        'error': 'Codex CLI not responding'
                    }
            except Exception as e:
                return {
                    'success': False,
                    'available': False,
                    'error': str(e)
                }

        else:
            return {
                'success': False,
                'error': f'Unknown method: {method}'
            }

    def run(self):
        """Run MCP bridge in stdio mode.

        Listens on stdin for JSON requests, sends responses to stdout.
        This is the standard MCP server protocol.
        """
        print("[Codex MCP Bridge] Starting...", file=sys.stderr)
        print(f"[Codex MCP Bridge] Temp dir: {self.temp_dir}", file=sys.stderr)

        while True:
            try:
                # Read request from stdin (one JSON object per line)
                line = sys.stdin.readline()
                if not line:
                    break

                request = json.loads(line.strip())
                print(f"[Codex MCP Bridge] Request: {request.get('method')}", file=sys.stderr)

                # Handle request
                response = self.handle_request(request)

                # Send response to stdout
                json.dump(response, sys.stdout)
                sys.stdout.write('\n')
                sys.stdout.flush()

                print(f"[Codex MCP Bridge] Response: success={response.get('success')}", file=sys.stderr)

            except json.JSONDecodeError as e:
                error_response = {
                    'success': False,
                    'error': f'Invalid JSON: {str(e)}'
                }
                json.dump(error_response, sys.stdout)
                sys.stdout.write('\n')
                sys.stdout.flush()

            except Exception as e:
                error_response = {
                    'success': False,
                    'error': f'Internal error: {str(e)}'
                }
                json.dump(error_response, sys.stdout)
                sys.stdout.write('\n')
                sys.stdout.flush()
                print(f"[Codex MCP Bridge] Error: {str(e)}", file=sys.stderr)


def main():
    """Entry point for MCP bridge."""
    bridge = CodexMCPBridge()
    bridge.run()


if __name__ == '__main__':
    main()
