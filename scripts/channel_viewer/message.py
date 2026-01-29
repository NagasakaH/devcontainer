"""Message data class for channel messages."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Message:
    """Represents a single message in a channel."""

    content: str
    channel_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    message_id: Optional[str] = None
    sender: str = "system"

    def __post_init__(self) -> None:
        """Generate message_id if not provided."""
        if self.message_id is None:
            self.message_id = f"{self.channel_id}-{self.timestamp.timestamp()}"

    def formatted(self) -> str:
        """Return formatted message string for display."""
        time_str = self.timestamp.strftime("%H:%M:%S")
        return f"[{time_str}] {self.sender}: {self.content}"

    def __str__(self) -> str:
        return self.formatted()
