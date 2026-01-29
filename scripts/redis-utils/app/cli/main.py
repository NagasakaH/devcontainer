#!/usr/bin/env python3
"""
redis-util CLI - Redis操作統合コマンドラインツール

Usage:
    redis-util init [options]          - オーケストレーション初期化
    redis-util rpush <list> <msg>      - メッセージ送信
    redis-util blpop <list> [options]  - メッセージ受信

Examples:
    # オーケストレーション初期化
    redis-util init --summoner-mode --max-children 5

    # メッセージ送信
    redis-util rpush my-queue "Hello World"

    # メッセージ受信
    redis-util blpop my-queue --timeout 10
"""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn


def setup_init_parser(subparsers: argparse._SubParsersAction) -> None:
    """initサブコマンドのパーサーを設定"""
    init_parser = subparsers.add_parser(
        "init",
        help="オーケストレーション初期化",
        description="オーケストレーション用Redis Blocked List/ストリームを初期化",
    )

    init_parser.add_argument(
        "--host",
        default="redis",
        help="Redisホスト (default: redis)",
    )
    init_parser.add_argument(
        "--port",
        type=int,
        default=6379,
        help="Redisポート (default: 6379)",
    )
    init_parser.add_argument(
        "--prefix",
        default=None,
        help="リストプレフィックス (default: $PROJECT_NAME-$HOST_NAME) ※通常モードのみ",
    )
    init_parser.add_argument(
        "--max-children",
        type=int,
        default=9,
        help="最大子エージェント数 (default: 9)",
    )
    init_parser.add_argument(
        "--sequence",
        type=int,
        default=None,
        help="シーケンス番号（省略時は自動検索）※通常モードのみ",
    )
    init_parser.add_argument(
        "--ttl",
        type=int,
        default=3600,
        help="設定のTTL秒数 (default: 3600 = 1時間)",
    )
    init_parser.add_argument(
        "--json",
        action="store_true",
        help="JSON形式で出力",
    )
    init_parser.add_argument(
        "--summoner-mode",
        action="store_true",
        help="Summonerモードで初期化（UUID形式セッションID、共有報告キュー、モニターチャンネル付き）",
    )
    init_parser.add_argument(
        "--session-id",
        default=None,
        help="セッションIDを指定（省略時は自動生成）※summonerモードのみ",
    )


def setup_rpush_parser(subparsers: argparse._SubParsersAction) -> None:
    """rpushサブコマンドのパーサーを設定"""
    rpush_parser = subparsers.add_parser(
        "rpush",
        help="Redisリストにメッセージを追加",
        description="Add messages to a Redis Blocked List using RPUSH",
    )

    rpush_parser.add_argument(
        "list_name",
        help="Name of the Redis list to push to",
    )
    rpush_parser.add_argument(
        "messages",
        nargs="*",
        help="Messages to add to the list",
    )
    rpush_parser.add_argument(
        "--host",
        default="redis",
        help="Redis host (default: redis for Docker network)",
    )
    rpush_parser.add_argument(
        "--port",
        type=int,
        default=6379,
        help="Redis port (default: 6379)",
    )
    rpush_parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read messages from stdin (one per line)",
    )
    rpush_parser.add_argument(
        "--channel",
        help="Pub/Sub channel to publish messages to (in addition to RPUSH)",
    )


def setup_blpop_parser(subparsers: argparse._SubParsersAction) -> None:
    """blpopサブコマンドのパーサーを設定"""
    blpop_parser = subparsers.add_parser(
        "blpop",
        help="Redisリストからメッセージを受信",
        description="Redis BLPOP Receiver - ブロッキングリストからメッセージを受信",
    )

    blpop_parser.add_argument(
        "list_name",
        help="受信対象のRedisリスト名",
    )
    blpop_parser.add_argument(
        "--host",
        default="redis",
        help="Redisホスト名 (default: redis)",
    )
    blpop_parser.add_argument(
        "--port",
        type=int,
        default=6379,
        help="Redisポート番号 (default: 6379)",
    )
    blpop_parser.add_argument(
        "--timeout",
        type=int,
        default=0,
        help="BLPOPタイムアウト秒数。0は無限待機 (default: 0)",
    )
    blpop_parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="受信するメッセージの最大数 (default: 1)",
    )
    blpop_parser.add_argument(
        "--parse",
        action="store_true",
        help="メッセージをパースして詳細表示（task/report/shutdown/statusを自動判別）",
    )
    blpop_parser.add_argument(
        "--continuous",
        "-c",
        action="store_true",
        help="連続受信モード（Ctrl+Cで停止）",
    )
    blpop_parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="ステータスメッセージを抑制",
    )


def run_init(args: argparse.Namespace) -> int:
    """initサブコマンドの実行"""
    from .init_orch import handle_init
    return handle_init(args)


def run_rpush(args: argparse.Namespace) -> int:
    """rpushサブコマンドの実行"""
    from ..sender import RedisSender
    from ..redis_client import RedisConnectionError, RedisCommandError
    from ..utils import truncate_string

    # メッセージを収集
    messages = list(args.messages) if args.messages else []
    if args.stdin:
        for line in sys.stdin:
            line = line.rstrip("\n")
            if line:
                messages.append(line)

    if not messages:
        print("Error: No messages provided. Specify messages as arguments or use --stdin", file=sys.stderr)
        return 1

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
            print(f"✗ Error: {result.error or 'Unknown error'}", file=sys.stderr)
            return 1

        # 成功出力
        print(f"✓ Added {result.message_count} message(s) to '{args.list_name}'")
        print(f"  List length: {result.list_length}")

        for i, msg in enumerate(messages, 1):
            preview = truncate_string(msg, 50)
            print(f"  [{i}] {preview}")

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
            print(
                f"✗ Error: Cannot connect to Redis at {args.host}:{args.port}",
                file=sys.stderr,
            )
            print("  Ensure Redis is running and accessible.", file=sys.stderr)
        elif "Cannot resolve" in str(e):
            print(
                f"✗ Error: Cannot resolve hostname '{args.host}'",
                file=sys.stderr,
            )
            print("  Check if you are on the same Docker network as Redis.", file=sys.stderr)
        else:
            print(f"✗ Error: {e}", file=sys.stderr)
        return 1
    except RedisCommandError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1


def run_blpop(args: argparse.Namespace) -> int:
    """blpopサブコマンドの実行"""
    from ..receiver import MessageReceiver
    from ..redis_client import RedisConnectionError
    from .blpop import (
        receive_single,
        receive_multiple,
        receive_continuous,
    )

    try:
        # Redisクライアント作成
        receiver = MessageReceiver(host=args.host, port=args.port)

        # 接続確認
        try:
            receiver.ping()
        except RedisConnectionError as e:
            print(f"✗ Error: Cannot connect to Redis at {args.host}:{args.port}", file=sys.stderr)
            print(f"  Details: {e}", file=sys.stderr)
            return 1

        # ステータスメッセージ
        if not args.quiet:
            print(f"Waiting for messages on '{args.list_name}'...", file=sys.stderr)

        # 受信モード選択
        if args.continuous:
            return receive_continuous(
                receiver,
                args.list_name,
                args.timeout,
                args.parse,
            )
        elif args.count > 1:
            return receive_multiple(
                receiver,
                args.list_name,
                args.count,
                args.timeout,
                args.parse,
            )
        else:
            return receive_single(
                receiver,
                args.list_name,
                args.timeout,
                args.parse,
            )

    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """
    メインエントリーポイント

    Returns:
        終了コード（0=成功、1=エラー）
    """
    parser = argparse.ArgumentParser(
        prog="redis-util",
        description="Redis操作CLIツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="サブコマンド",
        description="利用可能なコマンド",
        help="コマンドの説明",
    )

    # サブコマンドのパーサーを設定
    setup_init_parser(subparsers)
    setup_rpush_parser(subparsers)
    setup_blpop_parser(subparsers)

    # 引数をパース
    args = parser.parse_args()

    # コマンドが指定されていない場合はヘルプを表示
    if args.command is None:
        parser.print_help()
        return 1

    # サブコマンドを実行
    if args.command == "init":
        return run_init(args)
    elif args.command == "rpush":
        return run_rpush(args)
    elif args.command == "blpop":
        return run_blpop(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
