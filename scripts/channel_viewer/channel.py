"""Channel management for message receiving."""

import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Deque, Dict, List, Optional

try:
    from .message import Message
    from .simulator import MessageSimulator
    from .redis_channel import (
        RedisSubscriber,
        RedisConfig,
        parse_pubsub_message,
    )
except ImportError:
    from message import Message
    from simulator import MessageSimulator
    from redis_channel import (
        RedisSubscriber,
        RedisConfig,
        parse_pubsub_message,
    )


class ChannelType(Enum):
    """Channel source type."""

    SIMULATION = "simulation"
    REDIS_PUBSUB = "redis_pubsub"


class ChannelStatus(Enum):
    """Channel connection status."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class Channel:
    """Represents a single channel with message buffer."""

    id: str
    name: str
    channel_type: ChannelType = ChannelType.SIMULATION
    status: ChannelStatus = ChannelStatus.DISCONNECTED
    messages: Deque[Message] = field(default_factory=lambda: deque(maxlen=100))
    _thread: Optional[threading.Thread] = field(default=None, repr=False)
    _stop_event: threading.Event = field(
        default_factory=threading.Event, repr=False
    )
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    # Redis-specific fields
    redis_channel_name: Optional[str] = field(default=None, repr=False)
    redis_host: str = field(default="redis", repr=False)
    redis_port: int = field(default=6379, repr=False)
    _subscriber: Optional["RedisSubscriber"] = field(default=None, repr=False)

    def add_message(self, message: Message) -> None:
        """Add a message to the channel buffer (thread-safe)."""
        with self._lock:
            self.messages.append(message)

    def get_messages(self) -> List[Message]:
        """Get all messages (thread-safe)."""
        with self._lock:
            return list(self.messages)

    def message_count(self) -> int:
        """Get the number of messages (thread-safe)."""
        with self._lock:
            return len(self.messages)

    def clear_messages(self) -> None:
        """Clear all messages (thread-safe)."""
        with self._lock:
            self.messages.clear()


class ChannelManager:
    """Manages multiple channels and their background threads."""

    def __init__(
        self,
        on_message_received: Optional[Callable[[str, Message], None]] = None,
        on_status_changed: Optional[Callable[[str, ChannelStatus], None]] = None,
    ) -> None:
        """Initialize the channel manager.

        Args:
            on_message_received: Callback when a message is received (channel_id, message).
            on_status_changed: Callback when channel status changes (channel_id, status).
        """
        self._channels: Dict[str, Channel] = {}
        self._lock = threading.Lock()
        self._simulator = MessageSimulator()
        self._on_message_received = on_message_received
        self._on_status_changed = on_status_changed
        self._channel_counter = 0

    def create_channel(self, name: Optional[str] = None) -> Channel:
        """Create a new simulation channel and start receiving messages.

        Args:
            name: Optional channel name. If not provided, auto-generated.

        Returns:
            The newly created Channel.
        """
        with self._lock:
            self._channel_counter += 1
            channel_id = f"ch-{self._channel_counter:03d}"
            if name is None:
                name = f"Channel {self._channel_counter}"

            channel = Channel(
                id=channel_id,
                name=name,
                channel_type=ChannelType.SIMULATION,
            )
            self._channels[channel_id] = channel

        # Add welcome message
        welcome_msg = self._simulator.generate_welcome_message(channel_id)
        channel.add_message(welcome_msg)

        # Start receiving messages in background
        self._start_receiver(channel)

        return channel

    def create_redis_channel(
        self,
        redis_channel_name: str,
        name: Optional[str] = None,
        redis_host: str = "redis",
        redis_port: int = 6379,
    ) -> Channel:
        """Create a new Redis Pub/Sub channel and start subscribing.

        Args:
            redis_channel_name: The Redis Pub/Sub channel to subscribe to.
            name: Optional display name. If not provided, uses redis_channel_name.
            redis_host: Redis server host.
            redis_port: Redis server port.

        Returns:
            The newly created Channel.
        """
        with self._lock:
            self._channel_counter += 1
            channel_id = f"ch-{self._channel_counter:03d}"
            if name is None:
                # Extract a short name from the channel
                parts = redis_channel_name.split(":")
                if len(parts) > 1:
                    name = f"Redis:{parts[-1]}"
                else:
                    name = f"Redis:{redis_channel_name}"

            channel = Channel(
                id=channel_id,
                name=name,
                channel_type=ChannelType.REDIS_PUBSUB,
                redis_channel_name=redis_channel_name,
                redis_host=redis_host,
                redis_port=redis_port,
            )
            self._channels[channel_id] = channel

        # Add welcome message
        welcome_msg = Message(
            content=f"Subscribing to Redis channel '{redis_channel_name}'...",
            channel_id=channel_id,
            sender="system",
        )
        channel.add_message(welcome_msg)

        # Start Redis subscription
        self._start_redis_receiver(channel)

        return channel

    def delete_channel(self, channel_id: str) -> bool:
        """Delete a channel and stop its receiver thread.

        Args:
            channel_id: The ID of the channel to delete.

        Returns:
            True if the channel was deleted, False if not found.
        """
        with self._lock:
            if channel_id not in self._channels:
                return False

            channel = self._channels[channel_id]

        # Stop the receiver thread
        self._stop_receiver(channel)

        with self._lock:
            del self._channels[channel_id]

        return True

    def get_channel(self, channel_id: str) -> Optional[Channel]:
        """Get a channel by ID.

        Args:
            channel_id: The ID of the channel.

        Returns:
            The Channel if found, None otherwise.
        """
        with self._lock:
            return self._channels.get(channel_id)

    def get_all_channels(self) -> List[Channel]:
        """Get all channels.

        Returns:
            List of all channels.
        """
        with self._lock:
            return list(self._channels.values())

    def get_channel_ids(self) -> List[str]:
        """Get all channel IDs.

        Returns:
            List of channel IDs.
        """
        with self._lock:
            return list(self._channels.keys())

    def _start_receiver(self, channel: Channel) -> None:
        """Start the message receiver thread for a channel."""
        channel._stop_event.clear()
        channel.status = ChannelStatus.CONNECTING

        if self._on_status_changed:
            self._on_status_changed(channel.id, channel.status)

        thread = threading.Thread(
            target=self._receiver_loop,
            args=(channel,),
            daemon=True,
            name=f"receiver-{channel.id}",
        )
        channel._thread = thread
        thread.start()

    def _stop_receiver(self, channel: Channel) -> None:
        """Stop the message receiver thread for a channel."""
        channel._stop_event.set()
        channel.status = ChannelStatus.DISCONNECTED

        if self._on_status_changed:
            self._on_status_changed(channel.id, channel.status)

        # Stop Redis subscriber if it exists
        if channel._subscriber:
            channel._subscriber.stop_listening()
            channel._subscriber = None

        if channel._thread and channel._thread.is_alive():
            channel._thread.join(timeout=2.0)

    def _receiver_loop(self, channel: Channel) -> None:
        """Background loop that receives messages for a channel."""
        # Simulate connection delay
        time.sleep(0.5)

        channel.status = ChannelStatus.CONNECTED
        if self._on_status_changed:
            self._on_status_changed(channel.id, channel.status)

        while not channel._stop_event.is_set():
            # Random interval between messages (1-5 seconds)
            interval = random.uniform(1.0, 5.0)

            # Wait with ability to be interrupted
            if channel._stop_event.wait(timeout=interval):
                break

            # Generate and add a new message
            message = self._simulator.generate_message(channel.id)
            channel.add_message(message)

            if self._on_message_received:
                self._on_message_received(channel.id, message)

    def _start_redis_receiver(self, channel: Channel) -> None:
        """Start the Redis Pub/Sub receiver for a channel."""
        channel._stop_event.clear()
        channel.status = ChannelStatus.CONNECTING

        if self._on_status_changed:
            self._on_status_changed(channel.id, channel.status)

        def on_message(raw_message: str) -> None:
            """Handle incoming Redis message."""
            message = parse_pubsub_message(raw_message, channel.id)
            if message:
                channel.add_message(message)
                if self._on_message_received:
                    self._on_message_received(channel.id, message)

        def on_connected() -> None:
            """Handle successful connection."""
            channel.status = ChannelStatus.CONNECTED
            if self._on_status_changed:
                self._on_status_changed(channel.id, channel.status)

            # Add success message
            success_msg = Message(
                content=f"✓ Connected to Redis channel '{channel.redis_channel_name}'",
                channel_id=channel.id,
                sender="system",
            )
            channel.add_message(success_msg)
            if self._on_message_received:
                self._on_message_received(channel.id, success_msg)

        def on_error(error: Exception) -> None:
            """Handle connection error."""
            channel.status = ChannelStatus.ERROR
            if self._on_status_changed:
                self._on_status_changed(channel.id, channel.status)

            # Add error message
            error_msg = Message(
                content=f"✗ Error: {str(error)}",
                channel_id=channel.id,
                sender="system",
            )
            channel.add_message(error_msg)
            if self._on_message_received:
                self._on_message_received(channel.id, error_msg)

        def on_disconnected() -> None:
            """Handle disconnection."""
            if not channel._stop_event.is_set():
                channel.status = ChannelStatus.DISCONNECTED
                if self._on_status_changed:
                    self._on_status_changed(channel.id, channel.status)

        # Create subscriber
        config = RedisConfig(
            host=channel.redis_host,
            port=channel.redis_port,
        )
        subscriber = RedisSubscriber(
            channel_name=channel.redis_channel_name,
            config=config,
            on_message=on_message,
            on_connected=on_connected,
            on_error=on_error,
            on_disconnected=on_disconnected,
        )
        channel._subscriber = subscriber

        # Start connection in background thread
        thread = threading.Thread(
            target=self._redis_connect_loop,
            args=(channel, subscriber),
            daemon=True,
            name=f"redis-{channel.id}",
        )
        channel._thread = thread
        thread.start()

    def _redis_connect_loop(
        self, channel: Channel, subscriber: RedisSubscriber
    ) -> None:
        """Background thread to connect and run Redis subscriber."""
        if subscriber.connect():
            subscriber.start_listening()
        # Subscriber will handle its own loop

    def shutdown(self) -> None:
        """Stop all receiver threads and clean up."""
        with self._lock:
            channels = list(self._channels.values())

        for channel in channels:
            self._stop_receiver(channel)

        with self._lock:
            self._channels.clear()

    def total_message_count(self) -> int:
        """Get total message count across all channels."""
        with self._lock:
            return sum(ch.message_count() for ch in self._channels.values())

    def connected_count(self) -> int:
        """Get the number of connected channels."""
        with self._lock:
            return sum(
                1
                for ch in self._channels.values()
                if ch.status == ChannelStatus.CONNECTED
            )
