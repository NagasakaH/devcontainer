"""
メッセージフォーマットモジュール

タスク、レポート、シャットダウンなどのメッセージ形式を定義。
JSON変換メソッドを提供。
"""

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional

from .utils import get_iso_timestamp, generate_uuid_session_id


class MessageType(str, Enum):
    """メッセージタイプ列挙型"""
    TASK = "task"
    REPORT = "report"
    SHUTDOWN = "shutdown"
    STATUS = "status"
    CONTROL = "control"


@dataclass
class BaseMessage:
    """
    メッセージ基底クラス
    
    Attributes:
        type: メッセージタイプ
        timestamp: 作成日時（ISO 8601形式）
        message_id: メッセージ固有ID
    """
    type: str
    timestamp: str = field(default_factory=get_iso_timestamp)
    message_id: str = field(default_factory=generate_uuid_session_id)
    
    def to_dict(self) -> dict[str, Any]:
        """
        辞書形式に変換
        
        Returns:
            メッセージの辞書表現
        """
        return asdict(self)
    
    def to_json(self, ensure_ascii: bool = False, indent: Optional[int] = None) -> str:
        """
        JSON文字列に変換
        
        Args:
            ensure_ascii: ASCII文字のみにエスケープするか
            indent: インデント幅（Noneの場合は整形なし）
        
        Returns:
            JSON文字列
        """
        return json.dumps(self.to_dict(), ensure_ascii=ensure_ascii, indent=indent)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaseMessage":
        """
        辞書からインスタンスを生成
        
        Args:
            data: メッセージデータの辞書
        
        Returns:
            メッセージインスタンス
        """
        # typeフィールドは各サブクラスで固定値なので除外
        filtered_data = {k: v for k, v in data.items() if k != "type"}
        return cls(**filtered_data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "BaseMessage":
        """
        JSON文字列からインスタンスを生成
        
        Args:
            json_str: JSON文字列
        
        Returns:
            メッセージインスタンス
        """
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class TaskMessage(BaseMessage):
    """
    タスクメッセージ
    
    親エージェント（moogle/summoner）から子エージェント（chocobo）へのタスク指示。
    
    Attributes:
        task_id: タスク固有ID
        session_id: オーケストレーションセッションID
        child_id: 宛先の子エージェントID
        prompt: タスク指示内容
        context: 追加コンテキスト情報
        priority: 優先度（1=最高、5=最低）
        timeout: タイムアウト秒数（Noneの場合は無制限）
    """
    type: str = field(default=MessageType.TASK.value, init=False)
    task_id: str = ""
    session_id: str = ""
    child_id: int = 0
    prompt: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    priority: int = 3
    timeout: Optional[int] = None
    
    def __post_init__(self):
        if not self.task_id:
            self.task_id = generate_uuid_session_id()
    
    @property
    def instruction(self) -> str:
        """
        prompt のエイリアスプロパティ
        
        エージェント定義では instruction フィールドを使用するため、
        互換性のために prompt と同じ値を返す。
        
        Returns:
            タスク指示内容（prompt と同一）
        """
        return self.prompt
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskMessage":
        """
        辞書からインスタンスを生成
        
        instruction フィールドが存在する場合、prompt にマッピングする。
        両方存在する場合は instruction を優先する。
        
        Args:
            data: メッセージデータの辞書
        
        Returns:
            TaskMessage インスタンス
        """
        # データをコピーして操作
        filtered_data = {k: v for k, v in data.items() if k != "type"}
        
        # instruction → prompt マッピング
        if "instruction" in filtered_data:
            instruction_value = filtered_data.pop("instruction")
            # instruction を優先（prompt が無い場合、または両方ある場合）
            if "prompt" not in filtered_data or filtered_data.get("prompt") == "":
                filtered_data["prompt"] = instruction_value
            else:
                # 両方存在する場合も instruction を優先
                filtered_data["prompt"] = instruction_value
        
        return cls(**filtered_data)
    
    @classmethod
    def create(
        cls,
        prompt: str,
        session_id: str,
        child_id: int,
        context: Optional[dict[str, Any]] = None,
        priority: int = 3,
        timeout: Optional[int] = None,
    ) -> "TaskMessage":
        """
        タスクメッセージを作成するファクトリメソッド
        
        Args:
            prompt: タスク指示内容
            session_id: セッションID
            child_id: 子エージェントID
            context: 追加コンテキスト
            priority: 優先度
            timeout: タイムアウト秒数
        
        Returns:
            TaskMessage インスタンス
        """
        return cls(
            session_id=session_id,
            child_id=child_id,
            prompt=prompt,
            context=context or {},
            priority=priority,
            timeout=timeout,
        )


@dataclass
class ReportMessage(BaseMessage):
    """
    レポートメッセージ
    
    子エージェント（chocobo）から親エージェント（moogle/summoner）への結果報告。
    
    Attributes:
        task_id: 対応するタスクID
        session_id: オーケストレーションセッションID
        child_id: 報告元の子エージェントID
        status: 完了状態（"success", "failure", "error", "timeout"）
        result: 結果内容
        error: エラー情報（失敗時）
        duration_ms: 実行時間（ミリ秒）
        metadata: 追加メタデータ
    """
    type: str = field(default=MessageType.REPORT.value, init=False)
    task_id: str = ""
    session_id: str = ""
    child_id: int = 0
    status: str = "success"
    result: Any = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def success(
        cls,
        task_id: str,
        session_id: str,
        child_id: int,
        result: Any,
        duration_ms: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "ReportMessage":
        """
        成功レポートを作成
        
        Args:
            task_id: タスクID
            session_id: セッションID
            child_id: 子エージェントID
            result: 結果
            duration_ms: 実行時間
            metadata: メタデータ
        
        Returns:
            ReportMessage インスタンス
        """
        return cls(
            task_id=task_id,
            session_id=session_id,
            child_id=child_id,
            status="success",
            result=result,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )
    
    @classmethod
    def failure(
        cls,
        task_id: str,
        session_id: str,
        child_id: int,
        error: str,
        duration_ms: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "ReportMessage":
        """
        失敗レポートを作成
        
        Args:
            task_id: タスクID
            session_id: セッションID
            child_id: 子エージェントID
            error: エラーメッセージ
            duration_ms: 実行時間
            metadata: メタデータ
        
        Returns:
            ReportMessage インスタンス
        """
        return cls(
            task_id=task_id,
            session_id=session_id,
            child_id=child_id,
            status="failure",
            error=error,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )


@dataclass
class ShutdownMessage(BaseMessage):
    """
    シャットダウンメッセージ
    
    エージェント終了を指示するメッセージ。
    
    Attributes:
        session_id: オーケストレーションセッションID
        reason: 終了理由
        graceful: グレースフル終了かどうか
        target_child_id: 特定の子エージェントID（Noneの場合は全員）
    """
    type: str = field(default=MessageType.SHUTDOWN.value, init=False)
    session_id: str = ""
    reason: str = "normal"
    graceful: bool = True
    target_child_id: Optional[int] = None
    
    @classmethod
    def create(
        cls,
        session_id: str,
        reason: str = "normal",
        graceful: bool = True,
        target_child_id: Optional[int] = None,
    ) -> "ShutdownMessage":
        """
        シャットダウンメッセージを作成
        
        Args:
            session_id: セッションID
            reason: 終了理由
            graceful: グレースフル終了かどうか
            target_child_id: 対象の子エージェントID
        
        Returns:
            ShutdownMessage インスタンス
        """
        return cls(
            session_id=session_id,
            reason=reason,
            graceful=graceful,
            target_child_id=target_child_id,
        )


@dataclass
class StatusMessage(BaseMessage):
    """
    ステータスメッセージ
    
    エージェントの状態を通知するメッセージ。
    
    Attributes:
        session_id: オーケストレーションセッションID
        child_id: 子エージェントID
        event: イベント種別（"started", "ready", "busy", "completed", "stopped"）
        details: 詳細情報
    """
    type: str = field(default=MessageType.STATUS.value, init=False)
    session_id: str = ""
    child_id: int = 0
    event: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        session_id: str,
        child_id: int,
        event: str,
        details: Optional[dict[str, Any]] = None,
    ) -> "StatusMessage":
        """
        ステータスメッセージを作成
        
        Args:
            session_id: セッションID
            child_id: 子エージェントID
            event: イベント種別
            details: 詳細情報
        
        Returns:
            StatusMessage インスタンス
        """
        return cls(
            session_id=session_id,
            child_id=child_id,
            event=event,
            details=details or {},
        )


def parse_message(json_str: str) -> BaseMessage:
    """
    JSON文字列からメッセージをパースし、適切な型のインスタンスを返す
    
    Args:
        json_str: JSON文字列
    
    Returns:
        メッセージインスタンス（TaskMessage, ReportMessage, ShutdownMessage, StatusMessage）
    
    Raises:
        ValueError: 不明なメッセージタイプの場合
    """
    data = json.loads(json_str)
    msg_type = data.get("type")
    
    if msg_type == MessageType.TASK.value:
        return TaskMessage.from_dict(data)
    elif msg_type == MessageType.REPORT.value:
        return ReportMessage.from_dict(data)
    elif msg_type == MessageType.SHUTDOWN.value:
        return ShutdownMessage.from_dict(data)
    elif msg_type == MessageType.STATUS.value:
        return StatusMessage.from_dict(data)
    else:
        raise ValueError(f"Unknown message type: {msg_type}")
