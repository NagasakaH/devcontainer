---
name: redis-rpush-sender
description: >-
  Add messages to a Redis Blocked List using the RPUSH command. Use when you need to:
  (1) Send messages to a Redis list for queue processing,
  (2) Push data to workers listening with BLPOP/BRPOP,
  (3) Add multiple messages to a list at once,
  (4) Interact with Redis from a Docker container on the dev-network,
  (5) Notify subscribers via Pub/Sub when messages are added to queue.
  Triggers: "Redis RPUSH", "add to Redis list", "push to queue", "send message to worker",
  "Blocked List", "Redis queue", "メッセージをキューに追加", "Redisリストに追加",
  "PUBLISH", "Pub/Sub通知".
---

# redis-rpush-sender

Send messages to a Redis Blocked List using the bundled `rpush.py` script.

## Quick Start

Add a single message:
```bash
python scripts/rpush.py myqueue "Hello World"
```

Add multiple messages at once:
```bash
python scripts/rpush.py myqueue "msg1" "msg2" "msg3"
```

RPUSH and notify via Pub/Sub:
```bash
python scripts/rpush.py --channel notify:queue myqueue "Hello World"
```

## Script Usage

```bash
python scripts/rpush.py [OPTIONS] <list_name> <message> [<message2> ...]

Options:
  --host HOST        Redis host (default: redis)
  --port PORT        Redis port (default: 6379)
  --stdin            Read messages from stdin (one per line)
  --channel CHANNEL  Pub/Sub channel to publish messages to (in addition to RPUSH)
```

## Common Patterns

### Send to custom host
```bash
python scripts/rpush.py --host redis-dev --port 6379 tasks '{"action":"process"}'
```

### Pipe messages from file
```bash
cat messages.txt | python scripts/rpush.py --stdin jobqueue
```

### Send JSON payload
```bash
python scripts/rpush.py events '{"type":"user_created","id":123}'
```

### RPUSH with Pub/Sub notification
```bash
# Add to queue and notify subscribers on a channel
python scripts/rpush.py --channel summoner:abc123:monitor taskqueue '{"type":"task","task_id":"001"}'
```

When `--channel` is specified, the script performs two operations:
1. **RPUSH**: Adds the message to the specified Redis list
2. **PUBLISH**: Sends a notification to the specified Pub/Sub channel

The published message is a JSON object containing:
```json
{
  "queue": "taskqueue",
  "message": "{\"type\":\"task\",\"task_id\":\"001\"}",
  "timestamp": "2026-01-29T12:00:00+00:00"
}
```

This allows subscribers to know:
- Which queue received the message
- The original message content
- When the message was added

**Note**: If PUBLISH fails, RPUSH is still considered successful (a warning is displayed).

## Environment

- **Default host**: `redis` (Docker network service name)
- **Default port**: `6379`
- **Network**: Requires connection to `dev-network` where Redis runs
- No external dependencies (uses raw socket with RESP protocol)
