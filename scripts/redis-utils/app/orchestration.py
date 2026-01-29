#!/usr/bin/env python3
"""
オーケストレーション初期化モジュール

親エージェント（moogle）と子エージェント（chocobo）間の通信基盤を
Redis Blocked List/ストリームを使用してセットアップします。

通常モード:
    - 親→子: RPUSH {prefix}-{sequence}:p2c:{i} / BLPOP で待機
    - 子→親: RPUSH {prefix}-{sequence}:c2p:{i} / BLPOP で受信
    - 命名規則: {PROJECT_NAME}-{HOST_NAME}-{連番}

Summonerモード:
    - 親→子: RPUSH summoner:{session_id}:tasks:{i} / BLPOP で待機
    - 子→親: RPUSH summoner:{session_id}:reports （全chocobo共有）
    - モニター: PUBLISH summoner:{session_id}:monitor
    - 命名規則: summoner:{UUID}
"""

from __future__ import annotations

import json
import os
import socket
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Optional

# 将来的には共通モジュールからインポートする予定
# from .config import get_redis_config
# from .redis_client import RedisClient

__all__ = [
    "OrchestrationConfig",
    "initialize_orchestration",
    "initialize_summoner_orchestration",
    "get_config",
    "cleanup_session",
    "get_default_prefix",
    "generate_session_id",
]


@dataclass
class OrchestrationConfig:
    """オーケストレーション設定データクラス

    Attributes:
        session_id: セッション識別子
        prefix: Redisキー名のプレフィックス
        max_children: 最大子エージェント数
        created_at: 作成日時（ISO 8601形式）
        parent_to_child_lists: 親→子通信用リスト名
        child_to_parent_lists: 子→親通信用リスト名
        status_stream: 状態管理用ストリーム名
        result_stream: 結果収集用ストリーム名
        control_list: 制御用リスト名
        monitor_channel: モニタリング用Pub/Subチャンネル名（summonerモード用）
        mode: 動作モード（"normal" or "summoner"）
    """

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

    def to_dict(self) -> dict:
        """設定を辞書形式で返す"""
        return asdict(self)

    def to_json(self, indent: Optional[int] = None) -> str:
        """設定をJSON文字列で返す"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "OrchestrationConfig":
        """辞書からインスタンスを生成"""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "OrchestrationConfig":
        """JSON文字列からインスタンスを生成"""
        return cls.from_dict(json.loads(json_str))


def get_default_prefix() -> str:
    """環境変数からデフォルトプレフィックスを取得

    Returns:
        プレフィックス文字列（{PROJECT_NAME}-{HOST_NAME}形式）
    """
    project_name = os.environ.get("PROJECT_NAME", "project")
    host_name = os.environ.get("HOSTNAME", socket.gethostname())
    # ホスト名が長すぎる場合は短縮
    if len(host_name) > 12:
        host_name = host_name[:12]
    return f"{project_name}-{host_name}"


def generate_session_id() -> str:
    """ユニークなセッションIDを生成（通常モード用）

    Returns:
        タイムスタンプとPIDベースのセッションID
    """
    timestamp = int(time.time() * 1000)  # ミリ秒単位
    pid = os.getpid()
    return f"{timestamp}-{pid}"


def generate_uuid_session_id() -> str:
    """UUID形式のセッションIDを生成（summonerモード用）

    Returns:
        UUID文字列
    """
    return str(uuid.uuid4())


def _send_redis_command(host: str, port: int, *args: str) -> str:
    """RESPプロトコルでRedisコマンドを送信

    Args:
        host: Redisホスト
        port: Redisポート
        *args: コマンド引数

    Returns:
        Redisからのレスポンス
    """
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


def _check_key_exists(host: str, port: int, key: str) -> bool:
    """Redisキーの存在確認

    Args:
        host: Redisホスト
        port: Redisポート
        key: チェックするキー名

    Returns:
        キーが存在する場合True
    """
    response = _send_redis_command(host, port, "EXISTS", key)
    return response == ":1"


def _find_available_sequence(
    host: str, port: int, prefix: str, max_attempts: int = 100
) -> int:
    """使用可能な連番を検索（重複回避）

    Args:
        host: Redisホスト
        port: Redisポート
        prefix: キープレフィックス
        max_attempts: 最大試行数

    Returns:
        使用可能なシーケンス番号

    Raises:
        RuntimeError: 使用可能なシーケンス番号が見つからない場合
    """
    for seq in range(1, max_attempts + 1):
        config_key = f"{prefix}-{seq:03d}:config"
        if not _check_key_exists(host, port, config_key):
            return seq
    raise RuntimeError(f"No available sequence number found (tried 1-{max_attempts})")


def initialize_orchestration(
    host: str = "redis",
    port: int = 6379,
    prefix: Optional[str] = None,
    max_children: int = 9,
    sequence: Optional[int] = None,
    ttl: int = 3600,
) -> OrchestrationConfig:
    """通常モードのオーケストレーションを初期化

    Redis Blocked Listとストリームを作成し、親子間通信の基盤をセットアップします。

    Args:
        host: Redisホスト（デフォルト: "redis"）
        port: Redisポート（デフォルト: 6379）
        prefix: リスト名プレフィックス（Noneの場合は環境変数から取得）
        max_children: 最大子エージェント数（デフォルト: 9）
        sequence: シーケンス番号（Noneの場合は自動検索）
        ttl: 設定のTTL秒数（デフォルト: 3600 = 1時間）

    Returns:
        OrchestrationConfig: 初期化された設定

    Raises:
        ConnectionRefusedError: Redis接続失敗
        RuntimeError: シーケンス番号が見つからない
    """
    if prefix is None:
        prefix = get_default_prefix()

    # シーケンス番号の決定
    if sequence is None:
        sequence = _find_available_sequence(host, port, prefix)

    session_prefix = f"{prefix}-{sequence:03d}"
    session_id = generate_session_id()
    created_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    # 設定オブジェクト作成
    config = OrchestrationConfig(
        session_id=session_id,
        prefix=session_prefix,
        max_children=max_children,
        created_at=created_at,
        mode="normal",
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
    config_json = config.to_json()
    _send_redis_command(host, port, "SET", config_key, config_json)
    _send_redis_command(host, port, "EXPIRE", config_key, str(ttl))

    # 初期状態をストリームに記録
    _send_redis_command(
        host,
        port,
        "XADD",
        config.status_stream,
        "*",
        "event",
        "initialized",
        "session_id",
        session_id,
        "max_children",
        str(max_children),
        "created_at",
        created_at,
    )
    _send_redis_command(host, port, "EXPIRE", config.status_stream, str(ttl))

    return config


def initialize_summoner_orchestration(
    host: str = "redis",
    port: int = 6379,
    max_children: int = 9,
    session_id: Optional[str] = None,
    ttl: int = 3600,
) -> OrchestrationConfig:
    """Summonerモード用のオーケストレーションを初期化

    UUID形式のセッションIDを使用し、共有報告キューとモニターチャンネルを備えた
    オーケストレーション環境をセットアップします。

    Args:
        host: Redisホスト（デフォルト: "redis"）
        port: Redisポート（デフォルト: 6379）
        max_children: 最大子エージェント（chocobo）数（デフォルト: 9）
        session_id: セッションID（Noneの場合はUUID自動生成）
        ttl: 設定のTTL秒数（デフォルト: 3600 = 1時間）

    Returns:
        OrchestrationConfig: 初期化された設定

    Raises:
        ConnectionRefusedError: Redis接続失敗
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
    config_json = config.to_json()
    _send_redis_command(host, port, "SET", config_key, config_json)
    _send_redis_command(host, port, "EXPIRE", config_key, str(ttl))

    # 初期状態をストリームに記録
    _send_redis_command(
        host,
        port,
        "XADD",
        config.status_stream,
        "*",
        "event",
        "initialized",
        "mode",
        "summoner",
        "session_id",
        session_id,
        "max_children",
        str(max_children),
        "created_at",
        created_at,
    )
    _send_redis_command(host, port, "EXPIRE", config.status_stream, str(ttl))

    # モニターチャンネルに初期化イベントを通知
    init_message = json.dumps(
        {
            "event": "initialized",
            "session_id": session_id,
            "max_children": max_children,
            "created_at": created_at,
        },
        ensure_ascii=False,
    )
    _send_redis_command(host, port, "PUBLISH", config.monitor_channel, init_message)

    return config


def get_config(
    host: str = "redis",
    port: int = 6379,
    prefix: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Optional[OrchestrationConfig]:
    """既存のオーケストレーション設定を取得

    Args:
        host: Redisホスト（デフォルト: "redis"）
        port: Redisポート（デフォルト: 6379）
        prefix: 設定キーのプレフィックス（通常モード用）
        session_id: セッションID（Summonerモード用）

    Returns:
        OrchestrationConfig: 設定（存在しない場合None）

    Raises:
        ValueError: prefixとsession_idの両方がNone
    """
    if prefix is None and session_id is None:
        raise ValueError("Either prefix or session_id must be provided")

    if session_id is not None:
        config_key = f"summoner:{session_id}:config"
    else:
        config_key = f"{prefix}:config"

    response = _send_redis_command(host, port, "GET", config_key)

    # RESPプロトコル: $-1 は nil (key not found)
    if response == "$-1" or response.startswith("$-1"):
        return None

    # バルク文字列からJSONを抽出
    # 形式: $<length>\r\n<data>
    if response.startswith("$"):
        lines = response.split("\r\n", 1)
        if len(lines) > 1:
            json_str = lines[1]
        else:
            return None
    else:
        json_str = response

    try:
        return OrchestrationConfig.from_json(json_str)
    except (json.JSONDecodeError, TypeError):
        return None


def cleanup_session(
    host: str = "redis",
    port: int = 6379,
    config: Optional[OrchestrationConfig] = None,
    prefix: Optional[str] = None,
    session_id: Optional[str] = None,
) -> bool:
    """オーケストレーションセッションをクリーンアップ

    関連するすべてのRedisキーを削除します。

    Args:
        host: Redisホスト（デフォルト: "redis"）
        port: Redisポート（デフォルト: 6379）
        config: OrchestrationConfigオブジェクト（指定時は他パラメータを無視）
        prefix: 設定キーのプレフィックス（通常モード用）
        session_id: セッションID（Summonerモード用）

    Returns:
        クリーンアップ成功時True

    Raises:
        ValueError: config, prefix, session_idのいずれも指定されていない場合
    """
    # 設定を取得
    if config is None:
        if prefix is None and session_id is None:
            raise ValueError("Either config, prefix, or session_id must be provided")
        config = get_config(host, port, prefix=prefix, session_id=session_id)
        if config is None:
            return False

    # 削除対象キーのリスト
    keys_to_delete = []

    # リストキー
    keys_to_delete.extend(config.parent_to_child_lists)
    keys_to_delete.extend(config.child_to_parent_lists)

    # ストリームキー
    if config.status_stream:
        keys_to_delete.append(config.status_stream)
    if config.result_stream:
        keys_to_delete.append(config.result_stream)

    # 制御・設定キー
    if config.control_list:
        keys_to_delete.append(config.control_list)
    keys_to_delete.append(f"{config.prefix}:config")

    # 各キーを削除
    for key in keys_to_delete:
        _send_redis_command(host, port, "DEL", key)

    # Summonerモードの場合、クリーンアップイベントを通知
    if config.mode == "summoner" and config.monitor_channel:
        cleanup_message = json.dumps(
            {
                "event": "cleanup",
                "session_id": config.session_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            },
            ensure_ascii=False,
        )
        _send_redis_command(host, port, "PUBLISH", config.monitor_channel, cleanup_message)

    return True
