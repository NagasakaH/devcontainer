"""Redis Pub/Sub subscription functionality for channel_viewer.

This module provides Redis Pub/Sub subscription capability using raw RESP protocol,
similar to the approach used in rpush.py for consistency.
"""

import json
import socket
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

try:
    from .message import Message
except ImportError:
    from message import Message


@dataclass
class RedisConfig:
    """Redis connection configuration."""

    host: str = "redis"
    port: int = 6379
    timeout: float = 1.0  # Socket timeout for reading


class RespProtocol:
    """RESP (Redis Serialization Protocol) helper for Pub/Sub operations."""

    @staticmethod
    def encode_command(*args: str) -> bytes:
        """Encode a command as RESP protocol.

        Args:
            *args: Command parts (e.g., "SUBSCRIBE", "channel_name")

        Returns:
            Encoded RESP command as bytes.
        """
        cmd_parts = [f"*{len(args)}"]
        for arg in args:
            encoded = arg.encode("utf-8")
            cmd_parts.append(f"${len(encoded)}")
            cmd_parts.append(arg)
        return ("\r\n".join(cmd_parts) + "\r\n").encode("utf-8")

    @staticmethod
    def read_line(sock: socket.socket) -> str:
        """Read a line from socket until CRLF.

        Args:
            sock: Socket to read from.

        Returns:
            Line content without CRLF.
        """
        line = b""
        while True:
            char = sock.recv(1)
            if not char:
                raise ConnectionError("Connection closed")
            if char == b"\r":
                next_char = sock.recv(1)
                if next_char == b"\n":
                    break
                line += char + next_char
            else:
                line += char
        return line.decode("utf-8")

    @staticmethod
    def read_bulk_string(sock: socket.socket, length: int) -> str:
        """Read a bulk string of specified length.

        Args:
            sock: Socket to read from.
            length: Expected length of string.

        Returns:
            The bulk string content.
        """
        data = b""
        remaining = length
        while remaining > 0:
            chunk = sock.recv(min(remaining, 4096))
            if not chunk:
                raise ConnectionError("Connection closed")
            data += chunk
            remaining -= len(chunk)
        # Read trailing CRLF
        sock.recv(2)
        return data.decode("utf-8")

    @classmethod
    def read_response(cls, sock: socket.socket) -> list:
        """Read a RESP response (array format for Pub/Sub messages).

        Args:
            sock: Socket to read from.

        Returns:
            Parsed response as list.

        Raises:
            ValueError: If response format is invalid.
        """
        line = cls.read_line(sock)

        if line.startswith("*"):
            # Array
            count = int(line[1:])
            items = []
            for _ in range(count):
                items.append(cls.read_response(sock))
            return items
        elif line.startswith("$"):
            # Bulk string
            length = int(line[1:])
            if length == -1:
                return None
            return cls.read_bulk_string(sock, length)
        elif line.startswith("+"):
            # Simple string
            return line[1:]
        elif line.startswith("-"):
            # Error
            raise ValueError(f"Redis error: {line[1:]}")
        elif line.startswith(":"):
            # Integer
            return int(line[1:])
        else:
            raise ValueError(f"Unknown response type: {line}")


class RedisSubscriber:
    """Redis Pub/Sub subscriber using raw socket and RESP protocol."""

    def __init__(
        self,
        channel_name: str,
        config: Optional[RedisConfig] = None,
        on_message: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_connected: Optional[Callable[[], None]] = None,
        on_disconnected: Optional[Callable[[], None]] = None,
    ):
        """Initialize the subscriber.

        Args:
            channel_name: The Pub/Sub channel to subscribe to.
            config: Redis connection configuration.
            on_message: Callback for received messages (raw string).
            on_error: Callback for errors.
            on_connected: Callback when connected and subscribed.
            on_disconnected: Callback when disconnected.
        """
        self.channel_name = channel_name
        self.config = config or RedisConfig()
        self.on_message = on_message
        self.on_error = on_error
        self.on_connected = on_connected
        self.on_disconnected = on_disconnected

        self._socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if the subscriber is connected."""
        return self._connected

    def connect(self) -> bool:
        """Establish connection to Redis and subscribe to channel.

        Returns:
            True if connection and subscription successful.
        """
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(10)  # Connection timeout
            self._socket.connect((self.config.host, self.config.port))

            # Send SUBSCRIBE command
            cmd = RespProtocol.encode_command("SUBSCRIBE", self.channel_name)
            self._socket.sendall(cmd)

            # Read subscription confirmation
            response = RespProtocol.read_response(self._socket)

            # Response should be ['subscribe', 'channel_name', 1]
            if isinstance(response, list) and len(response) >= 3:
                if response[0] == "subscribe":
                    self._connected = True
                    # Set read timeout for message loop
                    self._socket.settimeout(self.config.timeout)
                    if self.on_connected:
                        self.on_connected()
                    return True

            raise ValueError(f"Unexpected subscription response: {response}")

        except Exception as e:
            self._cleanup()
            if self.on_error:
                self.on_error(e)
            return False

    def disconnect(self) -> None:
        """Disconnect from Redis."""
        self._stop_event.set()
        self._cleanup()
        if self.on_disconnected:
            self.on_disconnected()

    def _cleanup(self) -> None:
        """Clean up socket resources."""
        self._connected = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

    def start_listening(self) -> None:
        """Start listening for messages in a background thread."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._listen_loop,
            daemon=True,
            name=f"redis-sub-{self.channel_name}",
        )
        self._thread.start()

    def stop_listening(self) -> None:
        """Stop the listening thread."""
        self._stop_event.set()
        self.disconnect()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _listen_loop(self) -> None:
        """Main loop for receiving messages."""
        while not self._stop_event.is_set():
            try:
                if not self._socket:
                    break

                # Read message (with timeout)
                response = RespProtocol.read_response(self._socket)

                # Pub/Sub message format: ['message', 'channel', 'content']
                if isinstance(response, list) and len(response) >= 3:
                    msg_type = response[0]
                    if msg_type == "message":
                        channel = response[1]
                        content = response[2]
                        if channel == self.channel_name and self.on_message:
                            self.on_message(content)

            except socket.timeout:
                # Normal timeout, continue loop
                continue
            except ConnectionError as e:
                if not self._stop_event.is_set():
                    if self.on_error:
                        self.on_error(e)
                break
            except Exception as e:
                if not self._stop_event.is_set():
                    if self.on_error:
                        self.on_error(e)
                break

        self._cleanup()
        if self.on_disconnected and not self._stop_event.is_set():
            self.on_disconnected()


def parse_pubsub_message(raw_message: str, channel_id: str) -> Optional[Message]:
    """Parse a Pub/Sub message JSON into a Message object.

    Expected JSON format:
    {
        "queue": "summoner:abc123:tasks:1",
        "message": "{\"type\":\"task\",\"content\":...}",
        "timestamp": "2025-01-29T12:00:00+00:00"
    }

    Args:
        raw_message: Raw JSON string from Pub/Sub.
        channel_id: The channel ID for the Message object.

    Returns:
        Parsed Message object, or None if parsing fails.
    """
    try:
        data = json.loads(raw_message)

        queue = data.get("queue", "unknown")
        message_content = data.get("message", raw_message)
        timestamp_str = data.get("timestamp")

        # Parse timestamp
        if timestamp_str:
            try:
                # Handle ISO format with timezone
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                timestamp = datetime.now()
        else:
            timestamp = datetime.now()

        # Try to parse the inner message content as JSON
        sender = "redis"
        try:
            inner_data = json.loads(message_content)
            msg_type = inner_data.get("type", "message")
            content_preview = inner_data.get("content", message_content)

            # Format the display content
            if isinstance(content_preview, dict):
                content_preview = json.dumps(content_preview, ensure_ascii=False)

            # Truncate if too long
            if len(str(content_preview)) > 100:
                content_preview = str(content_preview)[:100] + "..."

            content = f"[{msg_type}] {queue}: {content_preview}"
            sender = inner_data.get("from", "redis")
        except (json.JSONDecodeError, TypeError):
            content = f"{queue}: {message_content}"

        return Message(
            content=content,
            channel_id=channel_id,
            timestamp=timestamp,
            sender=sender,
        )

    except json.JSONDecodeError:
        # If not JSON, return the raw message
        return Message(
            content=raw_message,
            channel_id=channel_id,
            timestamp=datetime.now(),
            sender="redis",
        )
    except Exception:
        return None


# Convenience function for simple subscription
def subscribe_to_channel(
    channel_name: str,
    host: str = "redis",
    port: int = 6379,
    on_message: Optional[Callable[[str], None]] = None,
) -> RedisSubscriber:
    """Create and start a Redis subscriber.

    Args:
        channel_name: The Pub/Sub channel to subscribe to.
        host: Redis host.
        port: Redis port.
        on_message: Callback for received messages.

    Returns:
        The started RedisSubscriber instance.
    """
    config = RedisConfig(host=host, port=port)
    subscriber = RedisSubscriber(
        channel_name=channel_name,
        config=config,
        on_message=on_message,
    )
    if subscriber.connect():
        subscriber.start_listening()
    return subscriber
