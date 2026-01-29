"""Message simulator for generating random messages."""

import random
from datetime import datetime
from typing import List

try:
    from .message import Message
except ImportError:
    from message import Message


class MessageSimulator:
    """Generates random messages for demonstration purposes."""

    # Sample message templates
    GREETINGS = [
        "Hello everyone!",
        "Hi there!",
        "Good morning!",
        "Hey, what's up?",
        "Greetings!",
    ]

    UPDATES = [
        "Just finished the task.",
        "Working on the new feature.",
        "Code review completed.",
        "Deployment successful!",
        "Tests are passing.",
        "Bug fixed and verified.",
        "Documentation updated.",
        "Meeting in 5 minutes.",
    ]

    QUESTIONS = [
        "Anyone available for a quick call?",
        "Has anyone seen the latest report?",
        "What's the status of the project?",
        "Can someone review my PR?",
        "Is the server running?",
        "Did we merge that fix?",
    ]

    RANDOM_EVENTS = [
        "🎉 Build succeeded!",
        "⚠️ Warning: High CPU usage detected",
        "✅ All tests passed",
        "📊 New metrics available",
        "🔔 Reminder: Daily standup",
        "💡 Tip: Use keyboard shortcuts for efficiency",
        "🚀 New version deployed",
        "📝 Changelog updated",
    ]

    SENDERS = [
        "alice",
        "bob",
        "charlie",
        "diana",
        "eve",
        "frank",
        "system",
        "bot",
        "admin",
        "monitor",
    ]

    def __init__(self) -> None:
        """Initialize the message simulator."""
        self._all_messages: List[str] = (
            self.GREETINGS + self.UPDATES + self.QUESTIONS + self.RANDOM_EVENTS
        )

    def generate_message(self, channel_id: str) -> Message:
        """Generate a random message for the given channel.

        Args:
            channel_id: The ID of the channel to generate a message for.

        Returns:
            A new Message instance with random content.
        """
        content = random.choice(self._all_messages)
        sender = random.choice(self.SENDERS)

        return Message(
            content=content,
            channel_id=channel_id,
            timestamp=datetime.now(),
            sender=sender,
        )

    def generate_welcome_message(self, channel_id: str) -> Message:
        """Generate a welcome message for a new channel.

        Args:
            channel_id: The ID of the new channel.

        Returns:
            A welcome Message instance.
        """
        return Message(
            content=f"Welcome to channel '{channel_id}'! Messages will appear here.",
            channel_id=channel_id,
            timestamp=datetime.now(),
            sender="system",
        )
