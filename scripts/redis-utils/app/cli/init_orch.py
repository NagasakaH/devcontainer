#!/usr/bin/env python3
"""
オーケストレーション初期化CLI

Usage:
    python -m app.cli.init_orch [--max-children N] [--prefix PREFIX]
    python -m app.cli.init_orch --summoner-mode [--max-children N]

Examples:
    # デフォルト設定で初期化（最大9子）
    python -m app.cli.init_orch

    # カスタム最大子数
    python -m app.cli.init_orch --max-children 5

    # カスタムプレフィックス
    python -m app.cli.init_orch --prefix "myproject-myhost"

    # Summonerモードで初期化
    python -m app.cli.init_orch --summoner-mode --max-children 3

    # JSON形式で出力
    python -m app.cli.init_orch --summoner-mode --json
"""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn

# モジュールとしてインポート
try:
    from app.orchestration import (
        OrchestrationConfig,
        get_default_prefix,
        initialize_orchestration,
        initialize_summoner_orchestration,
        get_config,
        cleanup_session,
    )
except ImportError:
    # 直接実行時のフォールバック
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from app.orchestration import (
        OrchestrationConfig,
        get_default_prefix,
        initialize_orchestration,
        initialize_summoner_orchestration,
        get_config,
        cleanup_session,
    )


def print_normal_mode_result(config: OrchestrationConfig) -> None:
    """通常モードの初期化結果を表示"""
    print("✓ オーケストレーション初期化完了")
    print()
    print(f"  セッションID: {config.session_id}")
    print(f"  プレフィックス: {config.prefix}")
    print(f"  最大子数: {config.max_children}")
    print(f"  作成日時: {config.created_at}")
    print(f"  モード: normal")
    print()
    print("  Blocked List/ストリーム:")
    print(f"    親→子 (BLPOP): {config.prefix}:p2c:{{1-{config.max_children}}}")
    print(f"    子→親 (BLPOP): {config.prefix}:c2p:{{1-{config.max_children}}}")
    print(f"    状態: {config.status_stream}")
    print(f"    結果: {config.result_stream}")
    print(f"    制御 (BLPOP): {config.control_list}")
    print(f"    設定: {config.prefix}:config")
    print()
    print("  環境変数にエクスポート:")
    print(f"    export ORCH_SESSION={config.prefix}")


def print_summoner_mode_result(config: OrchestrationConfig) -> None:
    """Summonerモードの初期化結果を表示"""
    print("✓ Summonerオーケストレーション初期化完了")
    print()
    print(f"  セッションID: {config.session_id}")
    print(f"  プレフィックス: {config.prefix}")
    print(f"  最大子数: {config.max_children}")
    print(f"  作成日時: {config.created_at}")
    print(f"  モード: summoner")
    print()
    print("  キュー構造:")
    print(f"    親→子 (tasks): {config.prefix}:tasks:{{1-{config.max_children}}}")
    print(f"    子→親 (reports): {config.prefix}:reports  ※全chocobo共有")
    print(f"    状態: {config.status_stream}")
    print(f"    結果: {config.result_stream}")
    print(f"    制御: {config.control_list}")
    print(f"    モニター (Pub/Sub): {config.monitor_channel}")
    print(f"    設定: {config.prefix}:config")
    print()
    print("  環境変数にエクスポート:")
    print(f"    export SUMMONER_SESSION={config.session_id}")
    print(f"    export SUMMONER_PREFIX={config.prefix}")


def print_get_config_result(config: OrchestrationConfig) -> None:
    """設定取得結果を表示"""
    print("✓ オーケストレーション設定取得完了")
    print()
    print(f"  セッションID: {config.session_id}")
    print(f"  プレフィックス: {config.prefix}")
    print(f"  最大子数: {config.max_children}")
    print(f"  作成日時: {config.created_at}")
    print(f"  モード: {config.mode}")


def create_parser() -> argparse.ArgumentParser:
    """コマンドライン引数パーサーを作成"""
    parser = argparse.ArgumentParser(
        description="オーケストレーション用Redis Blocked List/ストリームを初期化",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # サブコマンドの設定
    subparsers = parser.add_subparsers(dest="command", help="コマンド")

    # init コマンド（デフォルト動作）
    init_parser = subparsers.add_parser("init", help="オーケストレーションを初期化")
    _add_common_args(init_parser)

    # get コマンド
    get_parser = subparsers.add_parser("get", help="既存の設定を取得")
    get_parser.add_argument(
        "--host",
        default="redis",
        help="Redisホスト (default: redis)",
    )
    get_parser.add_argument(
        "--port",
        type=int,
        default=6379,
        help="Redisポート (default: 6379)",
    )
    get_parser.add_argument(
        "--prefix",
        default=None,
        help="設定プレフィックス（通常モード用）",
    )
    get_parser.add_argument(
        "--session-id",
        default=None,
        help="セッションID（Summonerモード用）",
    )
    get_parser.add_argument(
        "--json",
        action="store_true",
        help="JSON形式で出力",
    )

    # cleanup コマンド
    cleanup_parser = subparsers.add_parser("cleanup", help="セッションをクリーンアップ")
    cleanup_parser.add_argument(
        "--host",
        default="redis",
        help="Redisホスト (default: redis)",
    )
    cleanup_parser.add_argument(
        "--port",
        type=int,
        default=6379,
        help="Redisポート (default: 6379)",
    )
    cleanup_parser.add_argument(
        "--prefix",
        default=None,
        help="設定プレフィックス（通常モード用）",
    )
    cleanup_parser.add_argument(
        "--session-id",
        default=None,
        help="セッションID（Summonerモード用）",
    )

    # 引数なしの場合は init として扱う（後方互換性）
    _add_common_args(parser)

    return parser


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """共通引数を追加"""
    parser.add_argument(
        "--host",
        default="redis",
        help="Redisホスト (default: redis)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=6379,
        help="Redisポート (default: 6379)",
    )
    parser.add_argument(
        "--prefix",
        default=None,
        help="リストプレフィックス (default: $PROJECT_NAME-$HOST_NAME) ※通常モードのみ",
    )
    parser.add_argument(
        "--max-children",
        type=int,
        default=9,
        help="最大子エージェント数 (default: 9)",
    )
    parser.add_argument(
        "--sequence",
        type=int,
        default=None,
        help="シーケンス番号（省略時は自動検索）※通常モードのみ",
    )
    parser.add_argument(
        "--ttl",
        type=int,
        default=3600,
        help="設定のTTL秒数 (default: 3600 = 1時間)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="JSON形式で出力",
    )
    parser.add_argument(
        "--summoner-mode",
        action="store_true",
        help="Summonerモードで初期化（UUID形式セッションID、共有報告キュー、モニターチャンネル付き）",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="セッションIDを指定（省略時は自動生成）※summonerモードのみ",
    )


def handle_init(args: argparse.Namespace) -> int:
    """initコマンドの処理"""
    try:
        if args.summoner_mode:
            # Summonerモードで初期化
            config = initialize_summoner_orchestration(
                host=args.host,
                port=args.port,
                max_children=args.max_children,
                session_id=args.session_id,
                ttl=args.ttl,
            )

            if args.json:
                print(config.to_json(indent=2))
            else:
                print_summoner_mode_result(config)
        else:
            # 通常モードで初期化
            prefix = args.prefix if args.prefix else get_default_prefix()

            config = initialize_orchestration(
                host=args.host,
                port=args.port,
                prefix=prefix,
                max_children=args.max_children,
                sequence=args.sequence,
                ttl=args.ttl,
            )

            if args.json:
                print(config.to_json(indent=2))
            else:
                print_normal_mode_result(config)

        return 0

    except ConnectionRefusedError:
        print(f"✗ Error: Cannot connect to Redis at {args.host}:{args.port}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1


def handle_get(args: argparse.Namespace) -> int:
    """getコマンドの処理"""
    try:
        if args.prefix is None and args.session_id is None:
            print("✗ Error: Either --prefix or --session-id must be provided", file=sys.stderr)
            return 1

        config = get_config(
            host=args.host,
            port=args.port,
            prefix=args.prefix,
            session_id=args.session_id,
        )

        if config is None:
            print("✗ Error: Configuration not found", file=sys.stderr)
            return 1

        if args.json:
            print(config.to_json(indent=2))
        else:
            print_get_config_result(config)

        return 0

    except ConnectionRefusedError:
        print(f"✗ Error: Cannot connect to Redis at {args.host}:{args.port}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1


def handle_cleanup(args: argparse.Namespace) -> int:
    """cleanupコマンドの処理"""
    try:
        if args.prefix is None and args.session_id is None:
            print("✗ Error: Either --prefix or --session-id must be provided", file=sys.stderr)
            return 1

        success = cleanup_session(
            host=args.host,
            port=args.port,
            prefix=args.prefix,
            session_id=args.session_id,
        )

        if success:
            print("✓ セッションをクリーンアップしました")
            return 0
        else:
            print("✗ Error: Session not found or already cleaned up", file=sys.stderr)
            return 1

    except ConnectionRefusedError:
        print(f"✗ Error: Cannot connect to Redis at {args.host}:{args.port}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1


def main() -> NoReturn:
    """CLIエントリーポイント"""
    parser = create_parser()
    args = parser.parse_args()

    # サブコマンドが指定されていない場合は init として扱う
    if args.command is None:
        exit_code = handle_init(args)
    elif args.command == "init":
        exit_code = handle_init(args)
    elif args.command == "get":
        exit_code = handle_get(args)
    elif args.command == "cleanup":
        exit_code = handle_cleanup(args)
    else:
        parser.print_help()
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
