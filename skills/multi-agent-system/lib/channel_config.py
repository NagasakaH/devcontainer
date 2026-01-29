"""
チャンネル設定モジュール

セッションIDベースのチャンネル名・キュー名の生成と管理を提供します。

命名規則:
    {システム名}:{リソースタイプ}:{用途}:{セッションID}
    
例:
    - mas:queue:task:20260129-101213-a1b2c3d4
    - mas:queue:completion:20260129-101213-a1b2c3d4
    - mas:channel:terminate:20260129-101213-a1b2c3d4
    - mas:channel:notify:20260129-101213-a1b2c3d4

使用例:
    >>> from lib.channel_config import ChannelConfig
    >>> config = ChannelConfig.create_session()
    >>> print(config.task_queue)
    mas:queue:task:20260129-101213-a1b2c3d4
    >>> print(config.notification_channel)
    mas:channel:notify:20260129-101213-a1b2c3d4
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import random
import string


# システム識別子
SYSTEM_PREFIX = "mas"


class ChannelType(str, Enum):
    """チャンネル/キュータイプ"""
    TASK_QUEUE = "queue:task"           # タスク配信キュー（親→子）
    COMPLETION_QUEUE = "queue:completion"  # 完了報告キュー（子→親）
    TERMINATE_CHANNEL = "channel:terminate"  # 終了通知チャンネル（親→子）
    NOTIFY_CHANNEL = "channel:notify"       # ユーザー通知チャンネル


def generate_session_id() -> str:
    """
    セッションIDを生成
    
    形式: {timestamp}-{random}
    例: 20260129-101213-a1b2c3d4
    
    Returns:
        生成されたセッションID
    """
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{timestamp}-{random_part}"


def generate_channel_name(channel_type: ChannelType, session_id: str) -> str:
    """
    チャンネル/キュー名を生成
    
    Args:
        channel_type: チャンネルタイプ
        session_id: セッションID
        
    Returns:
        生成されたチャンネル/キュー名
    """
    return f"{SYSTEM_PREFIX}:{channel_type.value}:{session_id}"


def parse_channel_name(channel_name: str) -> tuple[Optional[ChannelType], Optional[str]]:
    """
    チャンネル/キュー名をパース
    
    Args:
        channel_name: チャンネル名
        
    Returns:
        (チャンネルタイプ, セッションID) のタプル。パース失敗時は (None, None)
    """
    try:
        parts = channel_name.split(":")
        if len(parts) < 4 or parts[0] != SYSTEM_PREFIX:
            return None, None
        
        # channel_type は parts[1]:parts[2]
        type_str = f"{parts[1]}:{parts[2]}"
        session_id = parts[3]
        
        # ChannelType を検索
        for ct in ChannelType:
            if ct.value == type_str:
                return ct, session_id
        
        return None, session_id
    except Exception:
        return None, None


@dataclass
class ChannelConfig:
    """
    チャンネル設定
    
    セッションに関連するすべてのチャンネル/キュー名を管理します。
    """
    session_id: str
    
    @classmethod
    def create_session(cls, session_id: Optional[str] = None) -> "ChannelConfig":
        """
        新しいセッション用のチャンネル設定を作成
        
        Args:
            session_id: セッションID（省略時は自動生成）
            
        Returns:
            新しいChannelConfig
        """
        return cls(session_id=session_id or generate_session_id())

    @property
    def task_queue(self) -> str:
        """タスク配信キュー名（親→子）"""
        return generate_channel_name(ChannelType.TASK_QUEUE, self.session_id)

    @property
    def completion_queue(self) -> str:
        """完了報告キュー名（子→親）"""
        return generate_channel_name(ChannelType.COMPLETION_QUEUE, self.session_id)

    @property
    def terminate_channel(self) -> str:
        """終了通知チャンネル名（親→子）"""
        return generate_channel_name(ChannelType.TERMINATE_CHANNEL, self.session_id)

    @property
    def notification_channel(self) -> str:
        """ユーザー通知チャンネル名"""
        return generate_channel_name(ChannelType.NOTIFY_CHANNEL, self.session_id)

    def get_channel(self, channel_type: ChannelType) -> str:
        """
        指定されたタイプのチャンネル/キュー名を取得
        
        Args:
            channel_type: チャンネルタイプ
            
        Returns:
            チャンネル/キュー名
        """
        return generate_channel_name(channel_type, self.session_id)

    def get_all_channels(self) -> dict[str, str]:
        """
        すべてのチャンネル/キュー名を辞書として取得
        
        Returns:
            チャンネルタイプ名をキー、チャンネル名を値とする辞書
        """
        return {
            "task_queue": self.task_queue,
            "completion_queue": self.completion_queue,
            "terminate_channel": self.terminate_channel,
            "notification_channel": self.notification_channel
        }

    def get_parent_channels(self) -> dict[str, list[str]]:
        """
        親エージェント用のチャンネル設定を取得
        
        Returns:
            {"listen": [...], "publish": [...]} 形式の辞書
        """
        return {
            "listen": [self.completion_queue],
            "publish": [self.task_queue, self.terminate_channel, self.notification_channel]
        }

    def get_child_channels(self) -> dict[str, list[str]]:
        """
        子エージェント用のチャンネル設定を取得
        
        Returns:
            {"listen": [...], "publish": [...]} 形式の辞書
        """
        return {
            "listen": [self.task_queue, self.terminate_channel],
            "publish": [self.completion_queue, self.notification_channel]
        }

    def to_dict(self) -> dict:
        """辞書に変換"""
        return {
            "session_id": self.session_id,
            "channels": self.get_all_channels()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChannelConfig":
        """辞書から作成"""
        return cls(session_id=data["session_id"])

    def __str__(self) -> str:
        return f"ChannelConfig(session_id={self.session_id})"

    def __repr__(self) -> str:
        return self.__str__()


# ==================== 便利な定数 ====================

class ChannelPatterns:
    """チャンネル名パターンの定数"""
    
    # パターン（セッションIDを含まない）
    TASK_QUEUE_PATTERN = f"{SYSTEM_PREFIX}:queue:task:*"
    COMPLETION_QUEUE_PATTERN = f"{SYSTEM_PREFIX}:queue:completion:*"
    TERMINATE_CHANNEL_PATTERN = f"{SYSTEM_PREFIX}:channel:terminate:*"
    NOTIFY_CHANNEL_PATTERN = f"{SYSTEM_PREFIX}:channel:notify:*"
    
    # すべてのパターン
    ALL_PATTERNS = [
        TASK_QUEUE_PATTERN,
        COMPLETION_QUEUE_PATTERN,
        TERMINATE_CHANNEL_PATTERN,
        NOTIFY_CHANNEL_PATTERN
    ]


def validate_session_id(session_id: str) -> bool:
    """
    セッションIDの形式を検証
    
    Args:
        session_id: 検証するセッションID
        
    Returns:
        有効な形式の場合True
    """
    if not session_id:
        return False
    
    parts = session_id.split("-")
    if len(parts) != 3:
        return False
    
    # 日付部分の検証
    date_part = parts[0]
    if len(date_part) != 8 or not date_part.isdigit():
        return False
    
    # 時刻部分の検証
    time_part = parts[1]
    if len(time_part) != 6 or not time_part.isdigit():
        return False
    
    # ランダム部分の検証
    random_part = parts[2]
    if len(random_part) != 8:
        return False
    if not all(c in string.ascii_lowercase + string.digits for c in random_part):
        return False
    
    return True
