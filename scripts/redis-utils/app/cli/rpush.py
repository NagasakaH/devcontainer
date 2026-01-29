#!/usr/bin/env python3
"""
Redis RPUSH CLI - リストにメッセージを追加するコマンドラインツール

Usage:
    python -m app.cli.rpush <list_name> <message> [<message2> ...]
    python -m app.cli.rpush --host <host> --port <port> <list_name> <message>
    python -m app.cli.rpush --channel <channel> <list_name> <message>

Examples:
    # 単一メッセージをリストに追加
    python -m app.cli.rpush myqueue "Hello World"

    # 複数メッセージを一括追加
    python -m app.cli.rpush myqueue "msg1" "msg2" "msg3"

    # カスタムRedisホストを指定
    python -m app.cli.rpush --host redis-dev --port 6379 myqueue "Hello"

    # 標準入力からメッセージを読み込み（1行1メッセージ）
    echo -e "msg1\\nmsg2" | python -m app.cli.rpush --stdin myqueue

    # RPUSH + Pub/Sub同時送信
    python -m app.cli.rpush --channel summoner:abc123:monitor myqueue '{"type":"task"}'
"""

import argparse
import sys
from typing import Optional

from ..sender import RedisSender, SendResult
from ..redis_client import RedisConnectionError, RedisCommandError
from ..utils import truncate_string


def print_success(result: SendResult, list_name: str, messages: list[str]) -> None:
    """
    成功時の出力を表示
    
    Args:
        result: 送信結果
        list_name: リスト名
        messages: 送信したメッセージ
    """
    print(f"✓ Added {result.message_count} message(s) to '{list_name}'")
    print(f"  List length: {result.list_length}")
    
    for i, msg in enumerate(messages, 1):
        preview = truncate_string(msg, 50)
        print(f"  [{i}] {preview}")


def print_publish_result(channel: str, messages: list[str], errors: list[tuple[str, str]]) -> None:
    """
    Pub/Sub結果の出力を表示
    
    Args:
        channel: チャンネル名
        messages: 送信したメッセージ
        errors: 発生したエラーのリスト
    """
    # 成功したメッセージの表示
    success_count = len(messages) - len(errors)
    if success_count > 0:
        # 注: エラーがないメッセージを表示（簡略化のため最初のメッセージのみ）
        for msg in messages:
            # エラーリストに含まれていないメッセージを表示
            if not any(msg == err[0] for err in errors):
                preview = truncate_string(msg, 30)
                print(f"  → Published to '{channel}': {preview}")
    
    # エラーの表示
    if errors:
        print(f"⚠ Warning: {len(errors)} publish operation(s) failed:", file=sys.stderr)
        for msg, err in errors:
            preview = truncate_string(msg, 30)
            print(f"  - '{preview}': {err}", file=sys.stderr)


def print_error(error_type: str, message: str, hint: Optional[str] = None) -> None:
    """
    エラーメッセージを表示
    
    Args:
        error_type: エラータイプ
        message: エラーメッセージ
        hint: ヒントメッセージ（オプション）
    """
    print(f"✗ {error_type}: {message}", file=sys.stderr)
    if hint:
        print(f"  {hint}", file=sys.stderr)


def main() -> int:
    """
    メインエントリーポイント
    
    Returns:
        終了コード（0=成功、1=エラー）
    """
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
        "--port",
        type=int,
        default=6379,
        help="Redis port (default: 6379)",
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
    parser.add_argument(
        "list_name",
        help="Name of the Redis list to push to",
    )
    parser.add_argument(
        "messages",
        nargs="*",
        help="Messages to add to the list",
    )

    args = parser.parse_args()

    # メッセージを収集
    messages = list(args.messages)
    if args.stdin:
        for line in sys.stdin:
            line = line.rstrip("\n")
            if line:
                messages.append(line)

    if not messages:
        parser.error("No messages provided. Specify messages as arguments or use --stdin")

    # Senderを初期化
    sender = RedisSender(host=args.host, port=args.port)

    try:
        # チャンネル指定がある場合はPub/Sub同時送信
        if args.channel:
            result = sender.send_messages_with_publish(
                args.list_name, messages, args.channel
            )
        else:
            result = sender.send_messages(args.list_name, messages)
        
        if not result.success:
            print_error("Error", result.error or "Unknown error")
            return 1
        
        # 成功出力
        print_success(result, args.list_name, messages)
        
        # Pub/Sub結果の出力
        if args.channel and result.published:
            for msg in messages:
                preview = truncate_string(msg, 30)
                print(f"  → Published to '{args.channel}' ({result.subscribers // len(messages)} subscriber(s)): {preview}")
            
            if result.error:
                print(f"⚠ Warning: {result.error}", file=sys.stderr)
        
        return 0

    except RedisConnectionError as e:
        if "Cannot connect" in str(e):
            print_error(
                "Error",
                f"Cannot connect to Redis at {args.host}:{args.port}",
                "Ensure Redis is running and accessible.",
            )
        elif "Cannot resolve" in str(e):
            print_error(
                "Error",
                f"Cannot resolve hostname '{args.host}'",
                "Check if you are on the same Docker network as Redis.",
            )
        else:
            print_error("Error", str(e))
        return 1
    except RedisCommandError as e:
        print_error("Error", str(e))
        return 1
    except Exception as e:
        print_error("Error", str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
