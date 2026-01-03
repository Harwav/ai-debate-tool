"""Stream Events Module

Event types for real-time streaming debate output.

Event Flow:
    start → progress* → perspective → perspective → consensus → complete

Usage:
    from ai_debate_tool.services.stream_events import StreamEvent, EventType

    event = StreamEvent.start(request="Review auth module", file="auth.py")
    print(event.to_json())
"""

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, Optional


class EventType(str, Enum):
    """Stream event types."""
    START = "start"
    PROGRESS = "progress"
    PERSPECTIVE = "perspective"
    CONSENSUS = "consensus"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class StreamEvent:
    """A streaming event for debate progress.

    Attributes:
        type: Event type (start, progress, perspective, consensus, complete, error)
        data: Event-specific data dictionary
        timestamp: Unix timestamp when event was created
    """
    type: EventType
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary.

        Returns:
            Dictionary representation of the event
        """
        return {
            "type": self.type.value if isinstance(self.type, EventType) else self.type,
            "timestamp": self.timestamp,
            "data": self.data
        }

    def to_json(self) -> str:
        """Convert event to JSON string.

        Returns:
            JSON string representation (single line)
        """
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StreamEvent":
        """Create event from dictionary.

        Args:
            data: Dictionary with type, timestamp, data keys

        Returns:
            StreamEvent instance
        """
        return cls(
            type=EventType(data["type"]),
            data=data.get("data", {}),
            timestamp=data.get("timestamp", time.time())
        )

    @classmethod
    def from_json(cls, json_str: str) -> "StreamEvent":
        """Create event from JSON string.

        Args:
            json_str: JSON string representation

        Returns:
            StreamEvent instance
        """
        return cls.from_dict(json.loads(json_str))

    # Factory methods for common event types

    @classmethod
    def start(
        cls,
        request: str,
        file_path: str,
        focus_areas: Optional[list] = None
    ) -> "StreamEvent":
        """Create a start event.

        Args:
            request: The debate request
            file_path: Path to file being debated
            focus_areas: Optional list of focus areas

        Returns:
            StreamEvent of type START
        """
        return cls(
            type=EventType.START,
            data={
                "request": request,
                "file": file_path,
                "focus_areas": focus_areas or []
            }
        )

    @classmethod
    def progress(
        cls,
        perspective: str,
        percent: int,
        message: Optional[str] = None
    ) -> "StreamEvent":
        """Create a progress event.

        Args:
            perspective: Name of the perspective (e.g., "Claude", "Codex")
            percent: Progress percentage (0-100)
            message: Optional status message

        Returns:
            StreamEvent of type PROGRESS
        """
        data = {
            "perspective": perspective,
            "percent": percent
        }
        if message:
            data["message"] = message
        return cls(type=EventType.PROGRESS, data=data)

    @classmethod
    def perspective(
        cls,
        name: str,
        score: int,
        elapsed_time: float,
        summary: Optional[str] = None
    ) -> "StreamEvent":
        """Create a perspective completion event.

        Args:
            name: Perspective name (e.g., "Claude", "Codex")
            score: Score given (0-100)
            elapsed_time: Time taken in seconds
            summary: Optional brief summary of the perspective

        Returns:
            StreamEvent of type PERSPECTIVE
        """
        data = {
            "name": name,
            "score": score,
            "time": elapsed_time
        }
        if summary:
            data["summary"] = summary[:200]  # Truncate long summaries
        return cls(type=EventType.PERSPECTIVE, data=data)

    @classmethod
    def consensus(
        cls,
        score: int,
        interpretation: str,
        recommendation: str
    ) -> "StreamEvent":
        """Create a consensus event.

        Args:
            score: Consensus score (0-100)
            interpretation: Human-readable interpretation
            recommendation: Recommended action

        Returns:
            StreamEvent of type CONSENSUS
        """
        return cls(
            type=EventType.CONSENSUS,
            data={
                "score": score,
                "interpretation": interpretation,
                "recommendation": recommendation
            }
        )

    @classmethod
    def complete(
        cls,
        consensus_score: int,
        total_time: float,
        can_proceed: bool,
        debate_id: Optional[str] = None
    ) -> "StreamEvent":
        """Create a completion event.

        Args:
            consensus_score: Final consensus score
            total_time: Total debate time in seconds
            can_proceed: Whether consensus was reached
            debate_id: Optional debate session ID

        Returns:
            StreamEvent of type COMPLETE
        """
        data = {
            "consensus": consensus_score,
            "total_time": total_time,
            "can_proceed": can_proceed
        }
        if debate_id:
            data["debate_id"] = debate_id
        return cls(type=EventType.COMPLETE, data=data)

    @classmethod
    def error(
        cls,
        message: str,
        perspective: Optional[str] = None,
        recoverable: bool = False
    ) -> "StreamEvent":
        """Create an error event.

        Args:
            message: Error message
            perspective: Which perspective failed (if applicable)
            recoverable: Whether the debate can continue

        Returns:
            StreamEvent of type ERROR
        """
        data = {
            "message": message,
            "recoverable": recoverable
        }
        if perspective:
            data["perspective"] = perspective
        return cls(type=EventType.ERROR, data=data)


class StreamEventFormatter:
    """Format stream events for different output modes."""

    @staticmethod
    def format_cli(event: StreamEvent) -> str:
        """Format event for CLI display.

        Args:
            event: StreamEvent to format

        Returns:
            Formatted string for terminal display
        """
        if event.type == EventType.START:
            return (
                f"\nStarting debate: {event.data['request']}\n"
                f"File: {event.data['file']}\n"
            )

        elif event.type == EventType.PROGRESS:
            perspective = event.data['perspective']
            percent = event.data['percent']
            bar = _progress_bar(percent)
            return f"\r[{perspective}] Analyzing... {bar} {percent}%"

        elif event.type == EventType.PERSPECTIVE:
            name = event.data['name']
            score = event.data['score']
            time_s = event.data['time']
            return f"\n[{name}] Complete ({time_s:.1f}s) → Score: {score}/100"

        elif event.type == EventType.CONSENSUS:
            return "\nCalculating consensus..."

        elif event.type == EventType.COMPLETE:
            score = event.data['consensus']
            can_proceed = event.data['can_proceed']
            status = "PROCEED" if can_proceed else "REVIEW NEEDED"
            return (
                f"\n\n{'═' * 45}\n"
                f"RESULT: Consensus {score}/100 - {status}\n"
                f"{'═' * 45}\n"
            )

        elif event.type == EventType.ERROR:
            return f"\n[ERROR] {event.data['message']}"

        return ""

    @staticmethod
    def format_json(event: StreamEvent) -> str:
        """Format event as JSON line.

        Args:
            event: StreamEvent to format

        Returns:
            JSON string (single line, no trailing newline)
        """
        return event.to_json()


def _progress_bar(percent: int, width: int = 16) -> str:
    """Create a progress bar string.

    Args:
        percent: Percentage (0-100)
        width: Bar width in characters

    Returns:
        Progress bar string like "████████░░░░░░░░"
    """
    filled = int(width * percent / 100)
    empty = width - filled
    return "█" * filled + "░" * empty
