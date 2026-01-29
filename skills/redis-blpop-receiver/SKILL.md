---
name: redis-blpop-receiver
description: Redis Blocked Listからメッセージをブロッキング受信するスキル。BLPOPコマンドを使用してキューからメッセージを取得する。「Redisからメッセージを受信」「キューからPOP」「BLPOPでメッセージ取得」「Redisリストを監視」「メッセージキューから受信」などのフレーズで発動。
---

# Redis BLPOP Receiver

Redisリストからブロッキング受信でメッセージを取得する。

## 前提条件

- Redisはcompose.ymlで起動済み（ポート6379がマッピング済み）
- `redis` Pythonパッケージがインストール済み（`pip install redis`）

## Quick Start

```bash
# 単一メッセージを受信（無限待機）
python scripts/blpop_receiver.py my_queue

# タイムアウト10秒で受信
python scripts/blpop_receiver.py my_queue --timeout 10

# 最大5件のメッセージを受信
python scripts/blpop_receiver.py my_queue --count 5
```

## 使用方法

### 基本コマンド

```bash
python scripts/blpop_receiver.py <list_name> [options]
```

### オプション

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--host` | `localhost` | Redisホスト名 |
| `--port` | `6379` | Redisポート番号 |
| `--timeout` | `0` | タイムアウト秒数（0=無限待機） |
| `--count` | `1` | 受信するメッセージの最大数 |

### 出力形式

受信したメッセージはJSON形式で標準出力に出力される：

```json
{"index": 1, "list": "my_queue", "message": "Hello", "timestamp": "2025-01-29T09:30:00+0000"}
```

### 使用例

```bash
# 開発環境で10秒待機
python scripts/blpop_receiver.py task_queue --timeout 10

# 複数メッセージを一括受信
python scripts/blpop_receiver.py notifications --count 10 --timeout 5

# 別のRedisインスタンスに接続
python scripts/blpop_receiver.py my_queue --host localhost --port 6380
```

## redis-cliでの動作確認

```bash
# 別ターミナルでメッセージを送信
docker exec redis-dev redis-cli RPUSH my_queue "test message"

# スクリプトで受信
python scripts/blpop_receiver.py my_queue --timeout 5
```

## スクリプト

- `scripts/blpop_receiver.py` - BLPOPによるブロッキング受信スクリプト
