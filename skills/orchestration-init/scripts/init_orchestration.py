#!/usr/bin/env python3
"""
オーケストレーション用Redis Blocked List/ストリームの初期化スクリプト

通常モード（Blocked List方式）:
- 親→子: RPUSH {prefix}:p2c:{i} でタスク送信、子はBLPOP で待機
- 子→親: RPUSH {prefix}:c2p:{i} で結果報告、親はBLPOP で受信
- 命名規則: {PROJECT_NAME}-{HOST_NAME}-{連番}

Summonerモード:
- 親→子: RPUSH summoner:{session_id}:tasks:{i} でタスク送信、子はBLPOP で待機
- 子→親: RPUSH summoner:{session_id}:reports で結果報告（全chocobo共有）
- モニター: PUBLISH summoner:{session_id}:monitor でPub/Sub可視化
- 命名規則: summoner:{UUID}

Usage:
    python init_orchestration.py [--max-children N] [--prefix PREFIX]
    python init_orchestration.py --summoner-mode [--max-children N]

Examples:
    # デフォルト設定で初期化（最大9子）
    python init_orchestration.py

    # カスタム最大子数
    python init_orchestration.py --max-children 5

    # カスタムプレフィックス
    python init_orchestration.py --prefix "myproject-myhost"
    
    # Summonerモードで初期化
    python init_orchestration.py --summoner-mode --max-children 3
"""

import argparse
import json
import os
import socket
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class OrchestrationConfig:
    """オーケストレーション設定"""
    session_id: str
    prefix: str
    max_children: int
    created_at: str
    
    # リスト名（親→子への指示、BLPOPで待機）
    parent_to_child_lists: list[str] = field(default_factory=list)
    
    # リスト名（子→親への報告、BLPOPで受信）
    child_to_parent_lists: list[str] = field(default_factory=list)
    
    # 状態管理用ストリーム
    status_stream: str = ""
    
    # 結果収集用ストリーム
    result_stream: str = ""
    
    # 制御用リスト（停止/キャンセル、BLPOPで待機）
    control_list: str = ""
    
    # モニタリング用Pub/Subチャンネル（summonerモード用）
    monitor_channel: str = ""
    
    # モード識別（"normal" or "summoner"）
    mode: str = "normal"


def get_default_prefix() -> str:
    """環境変数からデフォルトプレフィックスを取得"""
    project_name = os.environ.get("PROJECT_NAME", "project")
    host_name = os.environ.get("HOSTNAME", socket.gethostname())
    # ホスト名が長すぎる場合は短縮
    if len(host_name) > 12:
        host_name = host_name[:12]
    return f"{project_name}-{host_name}"


def generate_session_id() -> str:
    """ユニークなセッションIDを生成（通常モード用）"""
    timestamp = int(time.time() * 1000)  # ミリ秒単位
    pid = os.getpid()
    return f"{timestamp}-{pid}"


def generate_uuid_session_id() -> str:
    """UUID形式のセッションIDを生成（summonerモード用）"""
    return str(uuid.uuid4())


def send_redis_command(host: str, port: int, *args: str) -> str:
    """RESPプロトコルでRedisコマンドを送信"""
    cmd_parts = [f"*{len(args)}"]
    for arg in args:
        encoded = arg.encode("utf-8")
        cmd_parts.append(f"${len(encoded)}")
        cmd_parts.append(arg)
    command = "\r\n".join(cmd_parts) + "\r\n"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(10)
        sock.connect((host, port))
        sock.sendall(command.encode("utf-8"))

        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
            if b"\r\n" in response:
                break

    return response.decode("utf-8").strip()


def check_key_exists(host: str, port: int, key: str) -> bool:
    """Redisキーの存在確認"""
    response = send_redis_command(host, port, "EXISTS", key)
    return response == ":1"


def find_available_sequence(host: str, port: int, prefix: str, max_attempts: int = 100) -> int:
    """使用可能な連番を検索（重複回避）"""
    for seq in range(1, max_attempts + 1):
        # このシーケンス番号の設定キーが存在するか確認
        config_key = f"{prefix}-{seq:03d}:config"
        if not check_key_exists(host, port, config_key):
            return seq
    raise RuntimeError(f"No available sequence number found (tried 1-{max_attempts})")


def initialize_orchestration(
    host: str,
    port: int,
    prefix: str,
    max_children: int,
    sequence: Optional[int] = None,
    ttl: int = 3600,
) -> OrchestrationConfig:
    """
    オーケストレーション用のRedis Blocked List/ストリームを初期化

    Args:
        host: Redisホスト
        port: Redisポート
        prefix: リスト名プレフィックス
        max_children: 最大子エージェント数
        sequence: シーケンス番号（Noneの場合は自動検索）
        ttl: 設定のTTL秒数（デフォルト: 1時間）

    Returns:
        OrchestrationConfig: 初期化された設定
    """
    # シーケンス番号の決定
    if sequence is None:
        sequence = find_available_sequence(host, port, prefix)
    
    session_prefix = f"{prefix}-{sequence:03d}"
    session_id = generate_session_id()
    created_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    
    # 設定オブジェクト作成
    config = OrchestrationConfig(
        session_id=session_id,
        prefix=session_prefix,
        max_children=max_children,
        created_at=created_at,
    )
    
    # 親→子リスト（タスク割り当て、子はBLPOPで待機）
    for i in range(1, max_children + 1):
        config.parent_to_child_lists.append(f"{session_prefix}:p2c:{i}")
    
    # 子→親リスト（結果報告、親はBLPOPで受信）
    for i in range(1, max_children + 1):
        config.child_to_parent_lists.append(f"{session_prefix}:c2p:{i}")
    
    # 状態管理ストリーム
    config.status_stream = f"{session_prefix}:status"
    
    # 結果収集ストリーム
    config.result_stream = f"{session_prefix}:results"
    
    # 制御リスト（BLPOPで待機）
    config.control_list = f"{session_prefix}:control"
    
    # 設定をRedisに保存
    config_key = f"{session_prefix}:config"
    config_json = json.dumps(asdict(config), ensure_ascii=False)
    send_redis_command(host, port, "SET", config_key, config_json)
    send_redis_command(host, port, "EXPIRE", config_key, str(ttl))
    
    # 初期状態をストリームに記録
    send_redis_command(
        host, port,
        "XADD", config.status_stream, "*",
        "event", "initialized",
        "session_id", session_id,
        "max_children", str(max_children),
        "created_at", created_at,
    )
    send_redis_command(host, port, "EXPIRE", config.status_stream, str(ttl))
    
    return config


def initialize_summoner_orchestration(
    host: str,
    port: int,
    max_children: int,
    session_id: Optional[str] = None,
    ttl: int = 3600,
) -> OrchestrationConfig:
    """
    Summonerモード用のオーケストレーションを初期化

    Args:
        host: Redisホスト
        port: Redisポート
        max_children: 最大子エージェント（chocobo）数
        session_id: セッションID（Noneの場合はUUID自動生成）
        ttl: 設定のTTL秒数（デフォルト: 1時間）

    Returns:
        OrchestrationConfig: 初期化された設定
    """
    # UUID形式のセッションIDを生成
    if session_id is None:
        session_id = generate_uuid_session_id()
    
    session_prefix = f"summoner:{session_id}"
    created_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    
    # 設定オブジェクト作成
    config = OrchestrationConfig(
        session_id=session_id,
        prefix=session_prefix,
        max_children=max_children,
        created_at=created_at,
        mode="summoner",
    )
    
    # 親→子リスト（タスク割り当て、chocobo毎に個別キュー）
    for i in range(1, max_children + 1):
        config.parent_to_child_lists.append(f"{session_prefix}:tasks:{i}")
    
    # 子→親リスト（結果報告、全chocobo共有の単一キュー）
    config.child_to_parent_lists.append(f"{session_prefix}:reports")
    
    # 状態管理ストリーム
    config.status_stream = f"{session_prefix}:status"
    
    # 結果収集ストリーム
    config.result_stream = f"{session_prefix}:results"
    
    # 制御リスト（BLPOPで待機）
    config.control_list = f"{session_prefix}:control"
    
    # モニタリング用Pub/Subチャンネル
    config.monitor_channel = f"{session_prefix}:monitor"
    
    # 設定をRedisに保存
    config_key = f"{session_prefix}:config"
    config_json = json.dumps(asdict(config), ensure_ascii=False)
    send_redis_command(host, port, "SET", config_key, config_json)
    send_redis_command(host, port, "EXPIRE", config_key, str(ttl))
    
    # 初期状態をストリームに記録
    send_redis_command(
        host, port,
        "XADD", config.status_stream, "*",
        "event", "initialized",
        "mode", "summoner",
        "session_id", session_id,
        "max_children", str(max_children),
        "created_at", created_at,
    )
    send_redis_command(host, port, "EXPIRE", config.status_stream, str(ttl))
    
    # モニターチャンネルに初期化イベントを通知
    init_message = json.dumps({
        "event": "initialized",
        "session_id": session_id,
        "max_children": max_children,
        "created_at": created_at,
    }, ensure_ascii=False)
    send_redis_command(host, port, "PUBLISH", config.monitor_channel, init_message)
    
    return config


def main():
    parser = argparse.ArgumentParser(
        description="オーケストレーション用Redis Blocked List/ストリームを初期化",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
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

    args = parser.parse_args()

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
                print(json.dumps(asdict(config), ensure_ascii=False, indent=2))
            else:
                print(f"✓ Summonerオーケストレーション初期化完了")
                print(f"")
                print(f"  セッションID: {config.session_id}")
                print(f"  プレフィックス: {config.prefix}")
                print(f"  最大子数: {config.max_children}")
                print(f"  作成日時: {config.created_at}")
                print(f"  モード: summoner")
                print(f"")
                print(f"  キュー構造:")
                print(f"    親→子 (tasks): {config.prefix}:tasks:{{1-{config.max_children}}}")
                print(f"    子→親 (reports): {config.prefix}:reports  ※全chocobo共有")
                print(f"    状態: {config.status_stream}")
                print(f"    結果: {config.result_stream}")
                print(f"    制御: {config.control_list}")
                print(f"    モニター (Pub/Sub): {config.monitor_channel}")
                print(f"    設定: {config.prefix}:config")
                print(f"")
                print(f"  環境変数にエクスポート:")
                print(f"    export SUMMONER_SESSION={config.session_id}")
                print(f"    export SUMMONER_PREFIX={config.prefix}")
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
                print(json.dumps(asdict(config), ensure_ascii=False, indent=2))
            else:
                print(f"✓ オーケストレーション初期化完了")
                print(f"")
                print(f"  セッションID: {config.session_id}")
                print(f"  プレフィックス: {config.prefix}")
                print(f"  最大子数: {config.max_children}")
                print(f"  作成日時: {config.created_at}")
                print(f"  モード: normal")
                print(f"")
                print(f"  Blocked List/ストリーム:")
                print(f"    親→子 (BLPOP): {config.prefix}:p2c:{{1-{config.max_children}}}")
                print(f"    子→親 (BLPOP): {config.prefix}:c2p:{{1-{config.max_children}}}")
                print(f"    状態: {config.status_stream}")
                print(f"    結果: {config.result_stream}")
                print(f"    制御 (BLPOP): {config.control_list}")
                print(f"    設定: {config.prefix}:config")
                print(f"")
                print(f"  環境変数にエクスポート:")
                print(f"    export ORCH_SESSION={config.prefix}")

    except ConnectionRefusedError:
        print(f"✗ Error: Cannot connect to Redis at {args.host}:{args.port}", file=sys.stderr)
        sys.exit(1)
    except socket.gaierror:
        print(f"✗ Error: Cannot resolve hostname '{args.host}'", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
