"""Model Provider Interface

Abstract interface for AI model providers, enabling true multi-model debates.

Providers:
- CodexCLIProvider: Uses Codex CLI (subprocess)
- CopilotBridgeProvider: Uses VS Code Copilot Bridge (HTTP)

Usage:
    from ai_debate_tool.services.model_provider import get_available_providers

    primary, counter = get_available_providers()
    result = await primary.invoke(prompt)
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .codex_cli_invoker import CodexCLIInvoker, CodexCLIConfig
from .copilot_invoker import CopilotInvoker, CopilotConfig


@dataclass
class ModelResponse:
    """Response from a model provider."""
    success: bool
    response: str
    score: Optional[int] = None
    model: str = "unknown"
    vendor: str = "unknown"
    error: Optional[str] = None
    elapsed_time: float = 0.0


class ModelProvider(ABC):
    """Abstract interface for AI model providers."""

    @abstractmethod
    async def invoke(self, prompt: str) -> ModelResponse:
        """Invoke model with prompt and return response.

        Args:
            prompt: The prompt to send to the model

        Returns:
            ModelResponse with success status and response text
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available.

        Returns:
            True if provider can be used, False otherwise
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get provider display name.

        Returns:
            Human-readable provider name (e.g., "Claude", "Codex CLI")
        """
        pass

    @abstractmethod
    def get_vendor(self) -> str:
        """Get provider vendor.

        Returns:
            Vendor identifier (e.g., "anthropic", "openai", "copilot")
        """
        pass


class CodexCLIProvider(ModelProvider):
    """Codex CLI provider - invokes Codex via subprocess.

    This is the most reliable provider as it uses the locally installed
    Codex CLI and doesn't require any additional setup.
    """

    def __init__(self, config: Optional[CodexCLIConfig] = None):
        """Initialize Codex CLI provider.

        Args:
            config: Optional Codex CLI configuration
        """
        self.invoker = CodexCLIInvoker(config)
        self._name = "Codex CLI"

    async def invoke(self, prompt: str) -> ModelResponse:
        """Invoke Codex CLI with prompt.

        Args:
            prompt: The prompt to send

        Returns:
            ModelResponse with Codex's response
        """
        import time
        start = time.time()

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.invoker.invoke,
            prompt
        )

        elapsed = time.time() - start

        if result['success']:
            # Extract score if present in response
            score = self._extract_score(result['response'])
            return ModelResponse(
                success=True,
                response=result['response'],
                score=score,
                model=result.get('model', 'codex'),
                vendor='openai',
                elapsed_time=elapsed
            )
        else:
            return ModelResponse(
                success=False,
                response='',
                model=result.get('model', 'codex'),
                vendor='openai',
                error=result.get('error', 'Unknown error'),
                elapsed_time=elapsed
            )

    def is_available(self) -> bool:
        """Check if Codex CLI is available."""
        return self.invoker.is_available()

    def get_name(self) -> str:
        """Get provider name."""
        return self._name

    def get_vendor(self) -> str:
        """Get vendor identifier."""
        return "openai"

    def _extract_score(self, response: str, default: int = 75) -> int:
        """Extract numerical score from response.

        Args:
            response: Response text
            default: Default score if not found

        Returns:
            Extracted score (0-100)
        """
        import re

        patterns = [
            r'(?:score|rating):\s*(\d{1,3})',
            r'(\d{1,3})\s*/\s*100',
            r'(?:give|assign)\s+(?:it\s+)?(?:a\s+)?(\d{1,3})'
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                if 0 <= score <= 100:
                    return score

        return default


class CopilotBridgeProvider(ModelProvider):
    """Copilot Bridge provider - invokes Copilot via VS Code extension.

    Requires the Copilot Bridge VS Code extension to be running.
    Communicates via HTTP on localhost:8765.
    """

    def __init__(self, config: Optional[CopilotConfig] = None):
        """Initialize Copilot Bridge provider.

        Args:
            config: Optional Copilot configuration
        """
        self.invoker = CopilotInvoker(config)
        self._name = "GitHub Copilot"

    async def invoke(self, prompt: str) -> ModelResponse:
        """Invoke Copilot via bridge.

        Args:
            prompt: The prompt to send

        Returns:
            ModelResponse with Copilot's response
        """
        import time
        start = time.time()

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.invoker.invoke,
            prompt
        )

        elapsed = time.time() - start

        if result and result.get('success'):
            score = self._extract_score(result['response'])
            return ModelResponse(
                success=True,
                response=result['response'],
                score=score,
                model=result.get('model', 'copilot'),
                vendor='copilot',
                elapsed_time=elapsed
            )
        else:
            return ModelResponse(
                success=False,
                response='',
                model='copilot',
                vendor='copilot',
                error=result.get('error', 'Copilot bridge not available') if result else 'No response',
                elapsed_time=elapsed
            )

    def is_available(self) -> bool:
        """Check if Copilot Bridge is available."""
        return self.invoker.is_available()

    def get_name(self) -> str:
        """Get provider name."""
        return self._name

    def get_vendor(self) -> str:
        """Get vendor identifier."""
        return "copilot"

    def _extract_score(self, response: str, default: int = 75) -> int:
        """Extract numerical score from response."""
        import re

        patterns = [
            r'(?:score|rating):\s*(\d{1,3})',
            r'(\d{1,3})\s*/\s*100',
            r'(?:give|assign)\s+(?:it\s+)?(?:a\s+)?(\d{1,3})'
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                if 0 <= score <= 100:
                    return score

        return default


def get_available_providers() -> Tuple[ModelProvider, ModelProvider]:
    """Get the best available provider pair for debates.

    Returns tuple of (primary_provider, counter_provider).

    Detection priority:
    1. Copilot Bridge available → (Copilot, Codex CLI)
    2. Codex CLI only → (Codex CLI, Codex CLI)

    Returns:
        Tuple of (primary, counter) ModelProvider instances
    """
    codex = CodexCLIProvider()
    copilot = CopilotBridgeProvider()

    # Priority 1: Copilot Bridge + Codex CLI (true multi-model)
    if copilot.is_available() and codex.is_available():
        return (copilot, codex)

    # Priority 2: Codex CLI only (fallback - same model for both)
    if codex.is_available():
        return (codex, CodexCLIProvider())  # New instance for counter

    # Priority 3: Copilot only (rare - no Codex CLI)
    if copilot.is_available():
        return (copilot, CopilotBridgeProvider())

    # No providers available - return Codex anyway (will fail gracefully)
    return (codex, CodexCLIProvider())


def get_provider_status() -> Dict:
    """Get status of all available providers.

    Returns:
        Dictionary with provider availability info
    """
    codex = CodexCLIProvider()
    copilot = CopilotBridgeProvider()

    return {
        'codex_cli': {
            'available': codex.is_available(),
            'name': codex.get_name(),
            'vendor': codex.get_vendor()
        },
        'copilot_bridge': {
            'available': copilot.is_available(),
            'name': copilot.get_name(),
            'vendor': copilot.get_vendor()
        },
        'recommended_pair': _get_recommended_pair_names(codex, copilot)
    }


def _get_recommended_pair_names(codex: CodexCLIProvider, copilot: CopilotBridgeProvider) -> str:
    """Get human-readable description of recommended provider pair."""
    if copilot.is_available() and codex.is_available():
        return "Copilot (primary) + Codex CLI (counter)"
    elif codex.is_available():
        return "Codex CLI (both perspectives)"
    elif copilot.is_available():
        return "Copilot (both perspectives)"
    else:
        return "No providers available"
