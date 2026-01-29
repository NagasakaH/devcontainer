---
name: redis-rpush-sender
description: >-
  Add messages to a Redis Blocked List using the RPUSH command. Use when you need to:
  (1) Send messages to a Redis list for queue processing,
  (2) Push data to workers listening with BLPOP/BRPOP,
  (3) Add multiple messages to a list at once,
  (4) Interact with Redis from a Docker container on the dev-network.
  Triggers: "Redis RPUSH", "add to Redis list", "push to queue", "send message to worker",
  "Blocked List", "Redis queue", "メッセージをキューに追加", "Redisリストに追加".
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

## Script Usage

```bash
python scripts/rpush.py [OPTIONS] <list_name> <message> [<message2> ...]

Options:
  --host HOST    Redis host (default: redis)
  --port PORT    Redis port (default: 6379)
  --stdin        Read messages from stdin (one per line)
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

## Environment

- **Default host**: `redis` (Docker network service name)
- **Default port**: `6379`
- **Network**: Requires connection to `dev-network` where Redis runs
- No external dependencies (uses raw socket with RESP protocol)
