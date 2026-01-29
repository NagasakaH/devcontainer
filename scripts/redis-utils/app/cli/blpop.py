#!/usr/bin/env python3
"""
Redis BLPOP Receiver CLI - ブロッキングリストからメッセージを受信するCLI

Usage:
    python -m app.cli.blpop <list_name> [options]

Examples:
    # デフォルト設定で単一メッセージを受信
    python -m app.cli.blpop my_queue

    # タイムアウト10秒で最大5件受信
    python -m app.cli.blpop my_queue --timeout 10 --count 5

    # メッセージをパースして表示
    python -m app.cli.blpop my_queue --parse

    # カスタムホスト・ポートを指定
    python -m app.cli.blpop my_queue --host redis-dev --port 6379

    # 連続受信モード（Ctrl+C で停止）
    python -m app.cli.blpop my_queue --continuous --timeout 5
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import NoReturn, Optional

try:
    from app.receiver import (
        MessageReceiver,
        ReceivedMessage,
        receive_any_message,
    )
    from app.messages import (
        BaseMessage,
        MessageType,
        TaskMessage,
        ReportMessage,
        ShutdownMessage,
    )
    from app.redis_client import RedisConnectionError
except ImportError:
    # 直接実行時のフォールバック
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from app.receiver import (
        MessageReceiver,
        ReceivedMessage,
        receive_any_message,
    )
    from app.messages import (
        BaseMessage,
        MessageType,
        TaskMessage,
        ReportMessage,
        ShutdownMessage,
    )
    from app.redis_client import RedisConnectionError


def print_message(
    received: ReceivedMessage,
    parsed: Optional[BaseMessage] = None,
    show_parsed: bool = False,
) -> None:
    """
    受信したメッセージを出力
    
    Args:
        received: 受信したメッセージ
        parsed: パース済みメッセージ
        show_parsed: パース結果を含めて表示するか
    """
    if show_parsed and parsed:
        output = {
            "index": received.index,
            "list": received.list_name,
            "message": received.raw_data,
            "timestamp": received.timestamp,
            "parsed": {
                "type": parsed.type,
                "data": parsed.to_dict(),
            },
        }
    else:
        output = received.to_dict()
    
    print(json.dumps(output, ensure_ascii=False))


def receive_single(
    receiver: MessageReceiver,
    list_name: str,
    timeout: int,
    parse_messages: bool,
) -> int:
    """
    単一メッセージを受信
    
    Args:
        receiver: MessageReceiverインスタンス
        list_name: リスト名
        timeout: タイムアウト秒数
        parse_messages: メッセージをパースするか
    
    Returns:
        終了コード
    """
    if parse_messages:
        result = receiver.receive_and_parse(list_name, timeout)
        if result is None:
            print(f"Timeout: No message received within {timeout} seconds", file=sys.stderr)
            return 1
        received, parsed = result
        print_message(received, parsed, show_parsed=True)
    else:
        received = receiver.receive(list_name, timeout)
        if received is None:
            print(f"Timeout: No message received within {timeout} seconds", file=sys.stderr)
            return 1
        print_message(received)
    
    return 0


def receive_multiple(
    receiver: MessageReceiver,
    list_name: str,
    count: int,
    timeout: int,
    parse_messages: bool,
) -> int:
    """
    複数メッセージを受信
    
    Args:
        receiver: MessageReceiverインスタンス
        list_name: リスト名
        count: 最大受信数
        timeout: タイムアウト秒数
        parse_messages: メッセージをパースするか
    
    Returns:
        終了コード
    """
    received_count = 0
    
    for i in range(count):
        if parse_messages:
            result = receiver.receive_and_parse(list_name, timeout)
            if result is None:
                if i == 0:
                    print(f"Timeout: No message received within {timeout} seconds", file=sys.stderr)
                break
            received, parsed = result
            received.index = i + 1
            print_message(received, parsed, show_parsed=True)
        else:
            received = receiver.receive(list_name, timeout)
            if received is None:
                if i == 0:
                    print(f"Timeout: No message received within {timeout} seconds", file=sys.stderr)
                break
            received.index = i + 1
            print_message(received)
        
        received_count += 1
    
    print(f"\nReceived {received_count} message(s)", file=sys.stderr)
    return 0 if received_count > 0 else 1


def receive_continuous(
    receiver: MessageReceiver,
    list_name: str,
    timeout: int,
    parse_messages: bool,
) -> int:
    """
    連続受信モード
    
    Args:
        receiver: MessageReceiverインスタンス
        list_name: リスト名
        timeout: 各受信のタイムアウト秒数
        parse_messages: メッセージをパースするか
    
    Returns:
        終了コード
    """
    received_count = 0
    
    try:
        print(f"Continuous mode: waiting for messages on '{list_name}' (Ctrl+C to stop)", file=sys.stderr)
        
        for received in receiver.receive_iter(list_name, timeout):
            received_count += 1
            
            if parse_messages:
                try:
                    from app.messages import parse_message
                    parsed = parse_message(received.raw_data)
                    received.parsed = parsed
                    print_message(received, parsed, show_parsed=True)
                except (json.JSONDecodeError, ValueError, TypeError):
                    print_message(received)
            else:
                print_message(received)
    
    except KeyboardInterrupt:
        print(f"\nInterrupted. Received {received_count} message(s)", file=sys.stderr)
        return 0
    
    print(f"\nTimeout. Received {received_count} message(s)", file=sys.stderr)
    return 0 if received_count > 0 else 1


def create_parser() -> argparse.ArgumentParser:
    """コマンドライン引数パーサーを作成"""
    parser = argparse.ArgumentParser(
        description="Redis BLPOP Receiver - ブロッキングリストからメッセージを受信",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s my_queue                    # 単一メッセージを受信（無限待機）
  %(prog)s my_queue --timeout 10       # 10秒タイムアウトで受信
  %(prog)s my_queue --count 5          # 最大5件受信
  %(prog)s my_queue --parse            # メッセージをパースして表示
  %(prog)s my_queue --continuous       # 連続受信モード
  %(prog)s my_queue --host redis-dev   # カスタムホストに接続

Message Types (with --parse):
  task      - 親エージェントからのタスク指示
  report    - 子エージェントからの結果報告
  shutdown  - シャットダウン指示
  status    - ステータス通知
        """,
    )

    parser.add_argument(
        "list_name",
        help="受信対象のRedisリスト名",
    )
    parser.add_argument(
        "--host",
        default="redis",
        help="Redisホスト名 (default: redis)",
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
    parser.add_argument(
        "--parse",
        action="store_true",
        help="メッセージをパースして詳細表示（task/report/shutdown/statusを自動判別）",
    )
    parser.add_argument(
        "--continuous",
        "-c",
        action="store_true",
        help="連続受信モード（Ctrl+Cで停止）",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="ステータスメッセージを抑制",
    )

    return parser


def main() -> NoReturn:
    """CLIエントリーポイント"""
    parser = create_parser()
    args = parser.parse_args()

    try:
        # Redisクライアント作成
        receiver = MessageReceiver(host=args.host, port=args.port)
        
        # 接続確認
        try:
            receiver.ping()
        except RedisConnectionError as e:
            print(f"Error: Cannot connect to Redis at {args.host}:{args.port}", file=sys.stderr)
            print(f"Details: {e}", file=sys.stderr)
            sys.exit(1)

        # ステータスメッセージ
        if not args.quiet:
            print(f"Waiting for messages on '{args.list_name}'...", file=sys.stderr)

        # 受信モード選択
        if args.continuous:
            exit_code = receive_continuous(
                receiver,
                args.list_name,
                args.timeout,
                args.parse,
            )
        elif args.count > 1:
            exit_code = receive_multiple(
                receiver,
                args.list_name,
                args.count,
                args.timeout,
                args.parse,
            )
        else:
            exit_code = receive_single(
                receiver,
                args.list_name,
                args.timeout,
                args.parse,
            )

        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
