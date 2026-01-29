#!/usr/bin/env python3
"""
Redis BLPOP Receiver - ブロッキングリストからメッセージを受信するスクリプト

Usage:
    python blpop_receiver.py <list_name> [--host HOST] [--port PORT] [--timeout TIMEOUT] [--count COUNT]

Examples:
    # デフォルト設定で単一メッセージを受信
    python blpop_receiver.py my_queue

    # タイムアウト10秒で最大5件受信
    python blpop_receiver.py my_queue --timeout 10 --count 5

    # カスタムホスト・ポートを指定
    python blpop_receiver.py my_queue --host redis-dev --port 6379
"""

import argparse
import json
import sys
import time

try:
    import redis
except ImportError:
    print("Error: redis-py is not installed.", file=sys.stderr)
    print("Install with: pip install redis", file=sys.stderr)
    sys.exit(1)


def create_redis_client(host: str, port: int) -> redis.Redis:
    """Redisクライアントを作成して接続を確認する"""
    client = redis.Redis(host=host, port=port, decode_responses=True)
    try:
        client.ping()
    except redis.ConnectionError as e:
        print(f"Error: Cannot connect to Redis at {host}:{port}", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        sys.exit(1)
    return client


def blpop_receive(
    client: redis.Redis,
    list_name: str,
    timeout: int = 0,
    count: int = 1,
) -> list[tuple[str, str]]:
    """
    BLPOPを使用してリストからメッセージを受信する

    Args:
        client: Redisクライアント
        list_name: 受信対象のリスト名
        timeout: ブロッキングタイムアウト（秒）。0は無限待機
        count: 受信するメッセージの最大数

    Returns:
        受信したメッセージのリスト [(list_name, message), ...]
    """
    messages = []

    for i in range(count):
        result = client.blpop(list_name, timeout=timeout)

        if result is None:
            # タイムアウト
            if i == 0:
                print(f"Timeout: No message received within {timeout} seconds", file=sys.stderr)
            break

        received_list, message = result
        messages.append((received_list, message))

        # 結果を即座に出力
        output = {
            "index": i + 1,
            "list": received_list,
            "message": message,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        print(json.dumps(output, ensure_ascii=False))

    return messages


def main():
    parser = argparse.ArgumentParser(
        description="Redis BLPOP Receiver - ブロッキングリストからメッセージを受信",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s my_queue                    # 単一メッセージを受信（無限待機）
  %(prog)s my_queue --timeout 10       # 10秒タイムアウトで受信
  %(prog)s my_queue --count 5          # 最大5件受信
  %(prog)s my_queue --host redis-dev   # カスタムホストに接続
        """,
    )

    parser.add_argument(
        "list_name",
        help="受信対象のRedisリスト名",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Redisホスト名 (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=6379,
        help="Redisポート番号 (default: 6379)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=0,
        help="BLPOPタイムアウト秒数。0は無限待機 (default: 0)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="受信するメッセージの最大数 (default: 1)",
    )

    args = parser.parse_args()

    # Redisクライアント作成
    client = create_redis_client(args.host, args.port)

    # メッセージ受信
    print(f"Waiting for messages on '{args.list_name}'...", file=sys.stderr)
    messages = blpop_receive(
        client,
        args.list_name,
        timeout=args.timeout,
        count=args.count,
    )

    # サマリー出力
    print(f"\nReceived {len(messages)} message(s)", file=sys.stderr)

    return 0 if messages else 1


if __name__ == "__main__":
    sys.exit(main())
