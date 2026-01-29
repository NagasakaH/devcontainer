#!/usr/bin/env python3
"""
Redis RPUSH sender - Add messages to a Redis Blocked List using RPUSH command.

Usage:
    python rpush.py <list_name> <message> [<message2> ...]
    python rpush.py --host <host> --port <port> <list_name> <message>
    python rpush.py --channel <channel> <list_name> <message>

Examples:
    # Add single message to list
    python rpush.py myqueue "Hello World"

    # Add multiple messages at once
    python rpush.py myqueue "msg1" "msg2" "msg3"

    # Specify custom Redis host
    python rpush.py --host redis-dev --port 6379 myqueue "Hello"

    # Read messages from stdin (one per line)
    echo -e "msg1\nmsg2" | python rpush.py --stdin myqueue

    # RPUSH and simultaneously publish to a Pub/Sub channel
    python rpush.py --channel summoner:abc123:monitor myqueue '{"type":"task"}'
"""

import argparse
import json
import sys
import socket
from datetime import datetime, timezone


def send_redis_command(host: str, port: int, *args: str) -> str:
    """Send a RESP command to Redis and return the response."""
    # Build RESP protocol command
    cmd_parts = [f"*{len(args)}"]
    for arg in args:
        cmd_parts.append(f"${len(arg.encode('utf-8'))}")
        cmd_parts.append(arg)
    command = "\r\n".join(cmd_parts) + "\r\n"

    # Connect and send
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(10)
        sock.connect((host, port))
        sock.sendall(command.encode("utf-8"))

        # Read response
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
            if b"\r\n" in response:
                break

    return response.decode("utf-8").strip()


def rpush(host: str, port: int, list_name: str, messages: list[str]) -> int:
    """
    Add messages to a Redis list using RPUSH command.

    Args:
        host: Redis host
        port: Redis port
        list_name: Name of the Redis list
        messages: List of messages to add

    Returns:
        New length of the list after RPUSH
    """
    response = send_redis_command(host, port, "RPUSH", list_name, *messages)

    # Parse integer response (format: ":N\r\n")
    if response.startswith(":"):
        return int(response[1:])
    elif response.startswith("-"):
        raise RuntimeError(f"Redis error: {response[1:]}")
    else:
        raise RuntimeError(f"Unexpected response: {response}")


def publish(host: str, port: int, channel: str, message: str) -> int:
    """
    Publish a message to a Redis Pub/Sub channel.

    Args:
        host: Redis host
        port: Redis port
        channel: Pub/Sub channel name
        message: Message to publish

    Returns:
        Number of subscribers that received the message
    """
    response = send_redis_command(host, port, "PUBLISH", channel, message)

    # Parse integer response (format: ":N\r\n")
    if response.startswith(":"):
        return int(response[1:])
    elif response.startswith("-"):
        raise RuntimeError(f"Redis error: {response[1:]}")
    else:
        raise RuntimeError(f"Unexpected response: {response}")


def create_publish_payload(queue_name: str, message: str) -> str:
    """
    Create a JSON payload for publishing to a channel.

    Args:
        queue_name: Name of the queue the message was added to
        message: Original message content

    Returns:
        JSON string with queue, message, and timestamp
    """
    payload = {
        "queue": queue_name,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(payload, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description="Add messages to a Redis Blocked List using RPUSH",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--host",
        default="redis",
        help="Redis host (default: redis for Docker network)",
    )
    parser.add_argument(
        "--port", type=int, default=6379, help="Redis port (default: 6379)"
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read messages from stdin (one per line)",
    )
    parser.add_argument(
        "--channel",
        help="Pub/Sub channel to publish messages to (in addition to RPUSH)",
    )
    parser.add_argument("list_name", help="Name of the Redis list to push to")
    parser.add_argument(
        "messages", nargs="*", help="Messages to add to the list"
    )

    args = parser.parse_args()

    # Collect messages
    messages = list(args.messages)
    if args.stdin:
        for line in sys.stdin:
            line = line.rstrip("\n")
            if line:
                messages.append(line)

    if not messages:
        parser.error("No messages provided. Specify messages as arguments or use --stdin")

    try:
        new_length = rpush(args.host, args.port, args.list_name, messages)
        print(f"✓ Added {len(messages)} message(s) to '{args.list_name}'")
        print(f"  List length: {new_length}")
        for i, msg in enumerate(messages, 1):
            preview = msg[:50] + "..." if len(msg) > 50 else msg
            print(f"  [{i}] {preview}")

        # Publish to channel if specified
        if args.channel:
            publish_errors = []
            for msg in messages:
                try:
                    payload = create_publish_payload(args.list_name, msg)
                    subscribers = publish(args.host, args.port, args.channel, payload)
                    preview = msg[:30] + "..." if len(msg) > 30 else msg
                    print(f"  → Published to '{args.channel}' ({subscribers} subscriber(s)): {preview}")
                except Exception as e:
                    publish_errors.append((msg, str(e)))
            
            if publish_errors:
                print(f"⚠ Warning: {len(publish_errors)} publish operation(s) failed:", file=sys.stderr)
                for msg, err in publish_errors:
                    preview = msg[:30] + "..." if len(msg) > 30 else msg
                    print(f"  - '{preview}': {err}", file=sys.stderr)

    except ConnectionRefusedError:
        print(f"✗ Error: Cannot connect to Redis at {args.host}:{args.port}", file=sys.stderr)
        print("  Ensure Redis is running and accessible.", file=sys.stderr)
        sys.exit(1)
    except socket.gaierror:
        print(f"✗ Error: Cannot resolve hostname '{args.host}'", file=sys.stderr)
        print("  Check if you are on the same Docker network as Redis.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
