"""Streaming Debate Orchestrator

Orchestrates debates with real-time streaming output.

Usage:
    from ai_debate_tool.services.streaming_orchestrator import StreamingDebateOrchestrator

    orchestrator = StreamingDebateOrchestrator()

    async for event in orchestrator.run_debate_streaming(
        request="Review auth module",
        file_path="auth.py"
    ):
        print(event.to_json())
"""

import asyncio
import time
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Tuple

from .model_provider import (
    ModelProvider,
    ModelResponse,
    CodexCLIProvider,
    get_available_providers
)
from .stream_events import StreamEvent, EventType
from .prompt_optimizer import PromptOptimizer
from .fast_moderator import FastModerator
from .debate_cache import DebateCache
from .debate_history_manager import DebateHistoryManager


class StreamingDebateOrchestrator:
    """Orchestrates debates with streaming progress updates.

    Yields StreamEvent objects as the debate progresses, allowing
    real-time display of progress and results.
    """

    def __init__(
        self,
        cache_ttl_minutes: int = 5,
        enable_cache: bool = True,
        enable_history: bool = True
    ):
        """Initialize streaming orchestrator.

        Args:
            cache_ttl_minutes: Cache TTL in minutes (default 5)
            enable_cache: Enable response caching (default True)
            enable_history: Enable debate history (default True)
        """
        self.cache = DebateCache(ttl_minutes=cache_ttl_minutes) if enable_cache else None
        self.enable_cache = enable_cache
        self.history = DebateHistoryManager() if enable_history else None
        self.enable_history = enable_history

        # Get available providers
        self.primary_provider, self.counter_provider = get_available_providers()

    async def run_debate_streaming(
        self,
        request: str,
        file_path: str,
        focus_areas: Optional[List[str]] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """Run debate with streaming progress updates.

        Args:
            request: The debate request
            file_path: Path to file to debate
            focus_areas: Optional focus areas (auto-inferred if None)

        Yields:
            StreamEvent objects as debate progresses

        Example:
            async for event in orchestrator.run_debate_streaming(
                "Review auth", "auth.py"
            ):
                if event.type == EventType.COMPLETE:
                    print(f"Consensus: {event.data['consensus']}")
        """
        start_time = time.time()

        # Infer focus areas if not provided
        if not focus_areas:
            focus_areas = PromptOptimizer.infer_focus_areas(request)

        # Yield start event
        yield StreamEvent.start(request, file_path, focus_areas)

        # Extract context
        context = PromptOptimizer.extract_relevant_context(
            file_path,
            focus_areas,
            max_lines=200
        )

        # Create prompts
        primary_prompt = self._create_primary_prompt(request, context, focus_areas)
        counter_prompt = self._create_counter_prompt(request, context, focus_areas)

        # Check cache
        file_hash = DebateCache.hash_file_content(file_path) if self.enable_cache else None
        primary_cached = None
        counter_cached = None

        if self.enable_cache and self.cache:
            primary_cached = self.cache.get(primary_prompt, file_hash)
            counter_cached = self.cache.get(counter_prompt, file_hash)

        # Run providers in parallel, yield events as they complete
        primary_result = None
        counter_result = None

        async for event, result, is_primary in self._run_parallel_with_events(
            primary_prompt,
            counter_prompt,
            primary_cached,
            counter_cached,
            file_hash
        ):
            yield event
            if is_primary:
                primary_result = result
            else:
                counter_result = result

        # Calculate consensus
        yield StreamEvent(type=EventType.CONSENSUS, data={})

        consensus = FastModerator.analyze(
            {"score": primary_result.score, "response": primary_result.response},
            {"score": counter_result.score, "response": counter_result.response}
        )

        yield StreamEvent.consensus(
            score=consensus['consensus_score'],
            interpretation=consensus['interpretation'],
            recommendation=consensus['recommendation']
        )

        # Save to history
        debate_id = None
        if self.enable_history and self.history:
            debate_id = self.history.save_debate(
                request=request,
                file_path=file_path,
                debate_result={
                    'consensus_score': consensus['consensus_score'],
                    'primary': {
                        'score': primary_result.score,
                        'provider': self.primary_provider.get_name()
                    },
                    'counter': {
                        'score': counter_result.score,
                        'provider': self.counter_provider.get_name()
                    }
                },
                performance_stats={
                    'total_time': time.time() - start_time,
                    'primary_time': primary_result.elapsed_time,
                    'counter_time': counter_result.elapsed_time
                },
                focus_areas=focus_areas
            )

        # Yield completion event
        total_time = time.time() - start_time
        can_proceed = consensus['consensus_score'] >= 70

        yield StreamEvent.complete(
            consensus_score=consensus['consensus_score'],
            total_time=total_time,
            can_proceed=can_proceed,
            debate_id=debate_id
        )

    async def _run_parallel_with_events(
        self,
        primary_prompt: str,
        counter_prompt: str,
        primary_cached: Optional[Dict],
        counter_cached: Optional[Dict],
        file_hash: Optional[str]
    ) -> AsyncGenerator[Tuple[StreamEvent, ModelResponse, bool], None]:
        """Run both providers in parallel, yielding events as they complete.

        Args:
            primary_prompt: Prompt for primary provider
            counter_prompt: Prompt for counter provider
            primary_cached: Cached primary result (or None)
            counter_cached: Cached counter result (or None)
            file_hash: File hash for caching

        Yields:
            Tuple of (event, result, is_primary)
        """
        primary_name = self.primary_provider.get_name()
        counter_name = self.counter_provider.get_name()

        # Handle cached results
        if primary_cached is not None:
            result = ModelResponse(
                success=True,
                response=primary_cached.get('response', ''),
                score=primary_cached.get('score', 75),
                model='cached',
                vendor='cache',
                elapsed_time=0.0
            )
            yield (
                StreamEvent.perspective(
                    name=primary_name,
                    score=result.score,
                    elapsed_time=0.0,
                    summary="(cached)"
                ),
                result,
                True
            )
            primary_done = True
        else:
            primary_done = False

        if counter_cached is not None:
            result = ModelResponse(
                success=True,
                response=counter_cached.get('response', ''),
                score=counter_cached.get('score', 75),
                model='cached',
                vendor='cache',
                elapsed_time=0.0
            )
            yield (
                StreamEvent.perspective(
                    name=counter_name,
                    score=result.score,
                    elapsed_time=0.0,
                    summary="(cached)"
                ),
                result,
                False
            )
            counter_done = True
        else:
            counter_done = False

        # If both cached, we're done
        if primary_done and counter_done:
            return

        # Create tasks for non-cached providers
        tasks = []
        task_info = []

        if not primary_done:
            task = asyncio.create_task(
                self._invoke_with_progress(
                    self.primary_provider,
                    primary_prompt,
                    primary_name
                )
            )
            tasks.append(task)
            task_info.append(('primary', primary_name, primary_prompt))

        if not counter_done:
            task = asyncio.create_task(
                self._invoke_with_progress(
                    self.counter_provider,
                    counter_prompt,
                    counter_name
                )
            )
            tasks.append(task)
            task_info.append(('counter', counter_name, counter_prompt))

        # Yield progress events while waiting
        progress_task = asyncio.create_task(self._emit_progress_events(
            [name for _, name, _ in task_info]
        ))

        # Wait for tasks to complete and yield results
        for coro in asyncio.as_completed(tasks):
            result = await coro

            # Find which task completed
            for i, (role, name, prompt) in enumerate(task_info):
                if role == 'primary' and not primary_done:
                    primary_done = True
                    is_primary = True
                    # Cache result
                    if self.enable_cache and self.cache and result.success:
                        self.cache.set(prompt, {
                            'response': result.response,
                            'score': result.score
                        }, file_hash)
                    break
                elif role == 'counter' and not counter_done:
                    counter_done = True
                    is_primary = False
                    if self.enable_cache and self.cache and result.success:
                        self.cache.set(prompt, {
                            'response': result.response,
                            'score': result.score
                        }, file_hash)
                    break

            if result.success:
                yield (
                    StreamEvent.perspective(
                        name=name,
                        score=result.score or 75,
                        elapsed_time=result.elapsed_time,
                        summary=result.response[:100] if result.response else None
                    ),
                    result,
                    is_primary
                )
            else:
                yield (
                    StreamEvent.error(
                        message=result.error or "Unknown error",
                        perspective=name,
                        recoverable=False
                    ),
                    result,
                    is_primary
                )

            # Remove completed task from info
            task_info = [(r, n, p) for r, n, p in task_info if n != name]

        # Cancel progress task
        progress_task.cancel()
        try:
            await progress_task
        except asyncio.CancelledError:
            pass

    async def _invoke_with_progress(
        self,
        provider: ModelProvider,
        prompt: str,
        name: str
    ) -> ModelResponse:
        """Invoke provider (used for task creation).

        Args:
            provider: The model provider
            prompt: The prompt
            name: Provider name

        Returns:
            ModelResponse from provider
        """
        return await provider.invoke(prompt)

    async def _emit_progress_events(self, names: List[str]) -> None:
        """Emit periodic progress events (for visual feedback).

        Note: This is a placeholder. Real progress would require
        streaming from the underlying providers.

        Args:
            names: Names of providers being waited on
        """
        # Simulate progress updates every second
        for i in range(30):  # Max 30 seconds
            await asyncio.sleep(1)
            # Progress events would be yielded here if we had real streaming

    def _create_primary_prompt(
        self,
        request: str,
        context: str,
        focus_areas: List[str]
    ) -> str:
        """Create prompt for primary analysis.

        Args:
            request: The debate request
            context: Extracted file context
            focus_areas: Focus areas

        Returns:
            Formatted prompt string
        """
        base_prompt = PromptOptimizer.create_focused_prompt(
            request,
            context,
            focus_areas
        )
        return base_prompt + "\n\n**IMPORTANT: End your response with a numerical score (0-100) like 'Score: 85/100'**"

    def _create_counter_prompt(
        self,
        request: str,
        context: str,
        focus_areas: List[str]
    ) -> str:
        """Create prompt for counter/critical analysis.

        Args:
            request: The debate request
            context: Extracted file context
            focus_areas: Focus areas

        Returns:
            Formatted prompt string
        """
        return f"""You are a senior software architect providing a COUNTER-PERSPECTIVE on this plan.

USER REQUEST:
{request}

RELEVANT CONTEXT:
{context}

FOCUS AREAS:
{chr(10).join(f'- {area.replace("_", " ").title()}' for area in focus_areas)}

Your task as a CRITICAL REVIEWER:
1. Provide YOUR independent analysis (be skeptical and critical)
2. Identify risks and concerns that others might miss
3. Suggest alternative approaches if the current plan has flaws
4. End with recommendation and numerical score (0-100)

Be specific, actionable, and CRITICAL. Focus on {', '.join(focus_areas)}.

**IMPORTANT: End your response with a score like 'Score: 75/100'**
"""


# Convenience function for synchronous usage
def run_debate_streaming_sync(
    request: str,
    file_path: str,
    focus_areas: Optional[List[str]] = None,
    callback=None
) -> Dict:
    """Run streaming debate synchronously.

    Args:
        request: The debate request
        file_path: Path to file
        focus_areas: Optional focus areas
        callback: Optional callback(event) for each event

    Returns:
        Final result dictionary
    """
    async def _run():
        orchestrator = StreamingDebateOrchestrator()
        result = None

        async for event in orchestrator.run_debate_streaming(
            request, file_path, focus_areas
        ):
            if callback:
                callback(event)
            if event.type == EventType.COMPLETE:
                result = event.data

        return result

    return asyncio.run(_run())
