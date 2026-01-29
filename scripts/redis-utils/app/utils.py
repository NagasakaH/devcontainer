"""
ユーティリティ関数モジュール

セッションID生成、タイムスタンプ生成、プレフィックス生成などの共通関数を提供。
"""

import os
import socket
import time
import uuid
from typing import Optional


def generate_session_id() -> str:
    """
    ユニークなセッションIDを生成（通常モード用）
    
    タイムスタンプ（ミリ秒）とプロセスIDを組み合わせた形式。
    
    Returns:
        セッションID（例: "1704067200000-12345"）
    """
    timestamp = int(time.time() * 1000)  # ミリ秒単位
    pid = os.getpid()
    return f"{timestamp}-{pid}"


def generate_uuid_session_id() -> str:
    """
    UUID形式のセッションIDを生成（summonerモード用）
    
    Returns:
        UUID形式のセッションID（例: "550e8400-e29b-41d4-a716-446655440000"）
    """
    return str(uuid.uuid4())


def get_timestamp() -> int:
    """
    現在のUnixタイムスタンプを取得（秒）
    
    Returns:
        Unixタイムスタンプ（秒）
    """
    return int(time.time())


def get_timestamp_ms() -> int:
    """
    現在のUnixタイムスタンプを取得（ミリ秒）
    
    Returns:
        Unixタイムスタンプ（ミリ秒）
    """
    return int(time.time() * 1000)


def get_iso_timestamp() -> str:
    """
    現在時刻をISO 8601形式で取得
    
    Returns:
        ISO 8601形式の日時文字列（例: "2024-01-01T12:00:00+0900"）
    """
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def get_default_prefix(
    project_name: Optional[str] = None,
    host_name: Optional[str] = None,
    max_host_length: int = 12,
) -> str:
    """
    デフォルトのプレフィックスを生成
    
    環境変数 PROJECT_NAME と HOSTNAME から生成。
    ホスト名が長い場合は切り詰める。
    
    Args:
        project_name: プロジェクト名（Noneの場合は環境変数から取得）
        host_name: ホスト名（Noneの場合は環境変数から取得）
        max_host_length: ホスト名の最大長
    
    Returns:
        プレフィックス（例: "myproject-hostname"）
    """
    if project_name is None:
        project_name = os.environ.get("PROJECT_NAME", "project")
    if host_name is None:
        host_name = os.environ.get("HOSTNAME", socket.gethostname())
    
    # ホスト名が長すぎる場合は短縮
    if len(host_name) > max_host_length:
        host_name = host_name[:max_host_length]
    
    return f"{project_name}-{host_name}"


def generate_list_name(prefix: str, direction: str, child_id: int) -> str:
    """
    リスト名を生成
    
    Args:
        prefix: プレフィックス
        direction: 方向（"p2c" for parent-to-child, "c2p" for child-to-parent）
        child_id: 子エージェントID
    
    Returns:
        リスト名（例: "myproject-host-001:p2c:1"）
    """
    return f"{prefix}:{direction}:{child_id}"


def generate_summoner_task_queue(session_id: str, child_id: int) -> str:
    """
    Summonerモードのタスクキュー名を生成
    
    Args:
        session_id: セッションID（UUID形式）
        child_id: 子エージェントID（chocobo番号）
    
    Returns:
        タスクキュー名（例: "summoner:abc123:tasks:1"）
    """
    return f"summoner:{session_id}:tasks:{child_id}"


def generate_summoner_report_queue(session_id: str) -> str:
    """
    Summonerモードのレポートキュー名を生成
    
    Args:
        session_id: セッションID（UUID形式）
    
    Returns:
        レポートキュー名（例: "summoner:abc123:reports"）
    """
    return f"summoner:{session_id}:reports"


def generate_summoner_monitor_channel(session_id: str) -> str:
    """
    Summonerモードのモニターチャンネル名を生成
    
    Args:
        session_id: セッションID（UUID形式）
    
    Returns:
        モニターチャンネル名（例: "summoner:abc123:monitor"）
    """
    return f"summoner:{session_id}:monitor"


def truncate_string(s: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    文字列を指定長で切り詰める
    
    Args:
        s: 元の文字列
        max_length: 最大長
        suffix: 切り詰め時に付加する接尾辞
    
    Returns:
        切り詰めた文字列（超過していない場合はそのまま）
    """
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix
