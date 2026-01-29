"""
メッセージ生成・解析モジュール

プロトコル仕様に基づくメッセージクラスとシリアライズ/デシリアライズ機能を提供します。

プロトコルバージョン: 1.0.0

使用例:
    >>> from lib.message import Message, MessageType, TaskDispatchPayload
    >>> 
    >>> # タスク配信メッセージの作成
    >>> payload = TaskDispatchPayload(
    ...     task_id="task-001",
    ...     task_type=TaskType.CODE_REVIEW,
    ...     content={"instruction": "レビューしてください"},
    ...     priority=TaskPriority.NORMAL,
    ...     timeout={"seconds": 300}
    ... )
    >>> msg = Message.create(
    ...     message_type=MessageType.TASK_DISPATCH,
    ...     sender_id="parent-001",
    ...     payload=payload
    ... )
    >>> json_str = msg.to_json()
    >>> 
    >>> # JSON文字列からメッセージを復元
    >>> restored = Message.from_json(json_str)
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, TypeVar, Union
import json
import uuid


# プロトコルバージョン
PROTOCOL_VERSION = "1.0.0"


class MessageType(str, Enum):
    """メッセージタイプ"""
    STARTUP_INFO = "STARTUP_INFO"
    TASK_DISPATCH = "TASK_DISPATCH"
    TASK_COMPLETION = "TASK_COMPLETION"
    USER_NOTIFICATION = "USER_NOTIFICATION"
    SHUTDOWN_COMMAND = "SHUTDOWN_COMMAND"
    HEARTBEAT = "HEARTBEAT"


class TaskType(str, Enum):
    """タスクの種類"""
    CODE_REVIEW = "CODE_REVIEW"
    CODE_EDIT = "CODE_EDIT"
    TEST_EXECUTION = "TEST_EXECUTION"
    DOCUMENTATION = "DOCUMENTATION"
    EXPLORATION = "EXPLORATION"
    BUILD = "BUILD"
    CUSTOM = "CUSTOM"


class TaskPriority(str, Enum):
    """タスク優先度"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class TaskStatus(str, Enum):
    """タスク実行結果ステータス"""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PARTIAL = "PARTIAL"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class NotificationEvent(str, Enum):
    """通知イベントタイプ"""
    WORK_STARTED = "WORK_STARTED"
    WORK_COMPLETED = "WORK_COMPLETED"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    AGENT_READY = "AGENT_READY"
    AGENT_TERMINATED = "AGENT_TERMINATED"


class AgentRole(str, Enum):
    """エージェントの役割"""
    GOD = "god"
    PARENT = "parent"
    CHILD = "child"


class MessageValidationError(Exception):
    """メッセージ検証エラー"""
    pass


def generate_uuid() -> str:
    """UUID v4を生成"""
    return str(uuid.uuid4())


def generate_timestamp() -> str:
    """ISO 8601形式のタイムスタンプを生成"""
    return datetime.now(timezone.utc).isoformat()


def parse_timestamp(timestamp_str: str) -> datetime:
    """ISO 8601形式のタイムスタンプをパース"""
    return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))


# ==================== ペイロードクラス ====================

@dataclass
class ChannelsConfig:
    """チャンネル設定"""
    listen: list[str] = field(default_factory=list)
    publish: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"listen": self.listen, "publish": self.publish}

    @classmethod
    def from_dict(cls, data: dict) -> "ChannelsConfig":
        return cls(
            listen=data.get("listen", []),
            publish=data.get("publish", [])
        )


@dataclass
class AgentConfig:
    """エージェント設定"""
    timeout_seconds: int = 300
    max_retries: int = 3
    working_directory: Optional[str] = None
    docs_root: Optional[str] = None
    custom_params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        result = {
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
        }
        if self.working_directory:
            result["working_directory"] = self.working_directory
        if self.docs_root:
            result["docs_root"] = self.docs_root
        if self.custom_params:
            result["custom_params"] = self.custom_params
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "AgentConfig":
        return cls(
            timeout_seconds=data.get("timeout_seconds", 300),
            max_retries=data.get("max_retries", 3),
            working_directory=data.get("working_directory"),
            docs_root=data.get("docs_root"),
            custom_params=data.get("custom_params", {})
        )


@dataclass
class StartupInfoPayload:
    """起動情報ペイロード（神→親/子）"""
    agent_id: str
    role: AgentRole
    channels: ChannelsConfig
    config: AgentConfig

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value if isinstance(self.role, AgentRole) else self.role,
            "channels": self.channels.to_dict(),
            "config": self.config.to_dict()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StartupInfoPayload":
        role = data.get("role", "child")
        if isinstance(role, str):
            role = AgentRole(role)
        return cls(
            agent_id=data["agent_id"],
            role=role,
            channels=ChannelsConfig.from_dict(data.get("channels", {})),
            config=AgentConfig.from_dict(data.get("config", {}))
        )


@dataclass
class TaskContent:
    """タスク内容"""
    instruction: str
    target_files: list[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        result = {"instruction": self.instruction}
        if self.target_files:
            result["target_files"] = self.target_files
        if self.context:
            result["context"] = self.context
        if self.constraints:
            result["constraints"] = self.constraints
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "TaskContent":
        return cls(
            instruction=data.get("instruction", ""),
            target_files=data.get("target_files", []),
            context=data.get("context", {}),
            constraints=data.get("constraints", [])
        )


@dataclass
class TaskTimeout:
    """タスクタイムアウト設定"""
    seconds: int
    action_on_timeout: str = "ABORT"

    def to_dict(self) -> dict:
        return {
            "seconds": self.seconds,
            "action_on_timeout": self.action_on_timeout
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskTimeout":
        return cls(
            seconds=data.get("seconds", 300),
            action_on_timeout=data.get("action_on_timeout", "ABORT")
        )


@dataclass
class TaskMetadata:
    """タスクメタデータ"""
    parent_task_id: Optional[str] = None
    retry_count: int = 0
    original_message_id: Optional[str] = None

    def to_dict(self) -> dict:
        result = {"retry_count": self.retry_count}
        if self.parent_task_id:
            result["parent_task_id"] = self.parent_task_id
        if self.original_message_id:
            result["original_message_id"] = self.original_message_id
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "TaskMetadata":
        return cls(
            parent_task_id=data.get("parent_task_id"),
            retry_count=data.get("retry_count", 0),
            original_message_id=data.get("original_message_id")
        )


@dataclass
class TaskDispatchPayload:
    """タスク配信ペイロード（親→子）"""
    task_id: str
    task_type: TaskType
    content: TaskContent
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: TaskTimeout = field(default_factory=lambda: TaskTimeout(seconds=300))
    dependencies: list[str] = field(default_factory=list)
    metadata: TaskMetadata = field(default_factory=TaskMetadata)

    def to_dict(self) -> dict:
        task_type_val = self.task_type.value if isinstance(self.task_type, TaskType) else self.task_type
        priority_val = self.priority.value if isinstance(self.priority, TaskPriority) else self.priority
        return {
            "task_id": self.task_id,
            "task_type": task_type_val,
            "content": self.content.to_dict() if isinstance(self.content, TaskContent) else self.content,
            "priority": priority_val,
            "timeout": self.timeout.to_dict() if isinstance(self.timeout, TaskTimeout) else self.timeout,
            "dependencies": self.dependencies,
            "metadata": self.metadata.to_dict() if isinstance(self.metadata, TaskMetadata) else self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskDispatchPayload":
        task_type = data.get("task_type", "CUSTOM")
        if isinstance(task_type, str):
            task_type = TaskType(task_type)
        
        priority = data.get("priority", "NORMAL")
        if isinstance(priority, str):
            priority = TaskPriority(priority)
        
        content = data.get("content", {})
        if isinstance(content, dict):
            content = TaskContent.from_dict(content)
        
        timeout = data.get("timeout", {"seconds": 300})
        if isinstance(timeout, dict):
            timeout = TaskTimeout.from_dict(timeout)
        
        metadata = data.get("metadata", {})
        if isinstance(metadata, dict):
            metadata = TaskMetadata.from_dict(metadata)
        
        return cls(
            task_id=data["task_id"],
            task_type=task_type,
            content=content,
            priority=priority,
            timeout=timeout,
            dependencies=data.get("dependencies", []),
            metadata=metadata
        )


@dataclass
class ExecutionTime:
    """実行時間情報"""
    started_at: str
    completed_at: str
    duration_ms: int

    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionTime":
        return cls(
            started_at=data["started_at"],
            completed_at=data["completed_at"],
            duration_ms=data["duration_ms"]
        )

    @classmethod
    def create(cls, started_at: datetime, completed_at: datetime) -> "ExecutionTime":
        """datetimeオブジェクトから作成"""
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        return cls(
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            duration_ms=duration_ms
        )


@dataclass
class TaskOutput:
    """タスク出力"""
    summary: str = ""
    data: dict = field(default_factory=dict)
    artifacts: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        result = {}
        if self.summary:
            result["summary"] = self.summary
        if self.data:
            result["data"] = self.data
        if self.artifacts:
            result["artifacts"] = self.artifacts
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "TaskOutput":
        return cls(
            summary=data.get("summary", ""),
            data=data.get("data", {}),
            artifacts=data.get("artifacts", [])
        )


@dataclass
class TaskError:
    """タスクエラー情報"""
    code: str
    message: str
    details: dict = field(default_factory=dict)
    stack_trace: Optional[str] = None
    recoverable: bool = False

    def to_dict(self) -> dict:
        result = {
            "code": self.code,
            "message": self.message,
            "recoverable": self.recoverable
        }
        if self.details:
            result["details"] = self.details
        if self.stack_trace:
            result["stack_trace"] = self.stack_trace
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "TaskError":
        return cls(
            code=data.get("code", "UNKNOWN"),
            message=data.get("message", "Unknown error"),
            details=data.get("details", {}),
            stack_trace=data.get("stack_trace"),
            recoverable=data.get("recoverable", False)
        )


@dataclass
class TaskCompletionPayload:
    """完了報告ペイロード（子→親）"""
    task_id: str
    agent_id: str
    status: TaskStatus
    execution_time: ExecutionTime
    output: TaskOutput = field(default_factory=TaskOutput)
    error: Optional[TaskError] = None

    def to_dict(self) -> dict:
        status_val = self.status.value if isinstance(self.status, TaskStatus) else self.status
        result = {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "status": status_val,
            "execution_time": self.execution_time.to_dict() if isinstance(self.execution_time, ExecutionTime) else self.execution_time,
            "output": self.output.to_dict() if isinstance(self.output, TaskOutput) else self.output
        }
        if self.error:
            result["error"] = self.error.to_dict() if isinstance(self.error, TaskError) else self.error
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "TaskCompletionPayload":
        status = data.get("status", "SUCCESS")
        if isinstance(status, str):
            status = TaskStatus(status)
        
        execution_time = data.get("execution_time", {})
        if isinstance(execution_time, dict):
            execution_time = ExecutionTime.from_dict(execution_time)
        
        output = data.get("output", {})
        if isinstance(output, dict):
            output = TaskOutput.from_dict(output)
        
        error_data = data.get("error")
        error = TaskError.from_dict(error_data) if error_data else None
        
        return cls(
            task_id=data["task_id"],
            agent_id=data["agent_id"],
            status=status,
            execution_time=execution_time,
            output=output,
            error=error
        )


@dataclass
class UserNotificationPayload:
    """ユーザー通知ペイロード"""
    event: NotificationEvent
    agent_id: str
    agent_type: AgentRole
    message: str
    task_id: Optional[str] = None
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        event_val = self.event.value if isinstance(self.event, NotificationEvent) else self.event
        agent_type_val = self.agent_type.value if isinstance(self.agent_type, AgentRole) else self.agent_type
        result = {
            "event": event_val,
            "agent_id": self.agent_id,
            "agent_type": agent_type_val,
            "message": self.message
        }
        if self.task_id:
            result["task_id"] = self.task_id
        if self.data:
            result["data"] = self.data
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "UserNotificationPayload":
        event = data.get("event", "WORK_STARTED")
        if isinstance(event, str):
            event = NotificationEvent(event)
        
        agent_type = data.get("agent_type", "child")
        if isinstance(agent_type, str):
            agent_type = AgentRole(agent_type)
        
        return cls(
            event=event,
            agent_id=data["agent_id"],
            agent_type=agent_type,
            message=data["message"],
            task_id=data.get("task_id"),
            data=data.get("data", {})
        )


@dataclass
class ShutdownCommandPayload:
    """終了指示ペイロード（親→子）"""
    reason: str
    graceful: bool = True
    timeout_seconds: int = 30

    def to_dict(self) -> dict:
        return {
            "reason": self.reason,
            "graceful": self.graceful,
            "timeout_seconds": self.timeout_seconds
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ShutdownCommandPayload":
        return cls(
            reason=data.get("reason", "shutdown_requested"),
            graceful=data.get("graceful", True),
            timeout_seconds=data.get("timeout_seconds", 30)
        )


# ペイロードタイプの共用体
PayloadType = Union[
    StartupInfoPayload,
    TaskDispatchPayload,
    TaskCompletionPayload,
    UserNotificationPayload,
    ShutdownCommandPayload,
    dict
]


# ==================== メインメッセージクラス ====================

@dataclass
class Message:
    """
    プロトコルメッセージ
    
    すべてのメッセージの共通構造を定義します。
    """
    protocol_version: str
    message_type: MessageType
    message_id: str
    timestamp: str
    sender_id: str
    payload: PayloadType

    def to_dict(self) -> dict:
        """辞書に変換"""
        message_type_val = self.message_type.value if isinstance(self.message_type, MessageType) else self.message_type
        payload_dict = self.payload.to_dict() if hasattr(self.payload, 'to_dict') else self.payload
        return {
            "protocol_version": self.protocol_version,
            "message_type": message_type_val,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "sender_id": self.sender_id,
            "payload": payload_dict
        }

    def to_json(self, indent: Optional[int] = None) -> str:
        """JSON文字列に変換"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        """辞書からメッセージを作成"""
        message_type_str = data.get("message_type", "")
        message_type = MessageType(message_type_str) if message_type_str else MessageType.CUSTOM
        
        payload_data = data.get("payload", {})
        payload = cls._parse_payload(message_type, payload_data)
        
        return cls(
            protocol_version=data.get("protocol_version", PROTOCOL_VERSION),
            message_type=message_type,
            message_id=data.get("message_id", generate_uuid()),
            timestamp=data.get("timestamp", generate_timestamp()),
            sender_id=data.get("sender_id", ""),
            payload=payload
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Message":
        """JSON文字列からメッセージを作成"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def create(
        cls,
        message_type: MessageType,
        sender_id: str,
        payload: PayloadType,
        message_id: Optional[str] = None,
        timestamp: Optional[str] = None
    ) -> "Message":
        """
        新しいメッセージを作成
        
        Args:
            message_type: メッセージタイプ
            sender_id: 送信元エージェントID
            payload: ペイロード
            message_id: メッセージID（省略時は自動生成）
            timestamp: タイムスタンプ（省略時は現在時刻）
            
        Returns:
            作成されたメッセージ
        """
        return cls(
            protocol_version=PROTOCOL_VERSION,
            message_type=message_type,
            message_id=message_id or generate_uuid(),
            timestamp=timestamp or generate_timestamp(),
            sender_id=sender_id,
            payload=payload
        )

    @staticmethod
    def _parse_payload(message_type: MessageType, payload_data: dict) -> PayloadType:
        """メッセージタイプに応じてペイロードをパース"""
        try:
            if message_type == MessageType.STARTUP_INFO:
                return StartupInfoPayload.from_dict(payload_data)
            elif message_type == MessageType.TASK_DISPATCH:
                return TaskDispatchPayload.from_dict(payload_data)
            elif message_type == MessageType.TASK_COMPLETION:
                return TaskCompletionPayload.from_dict(payload_data)
            elif message_type == MessageType.USER_NOTIFICATION:
                return UserNotificationPayload.from_dict(payload_data)
            elif message_type == MessageType.SHUTDOWN_COMMAND:
                return ShutdownCommandPayload.from_dict(payload_data)
            else:
                return payload_data
        except Exception:
            # パース失敗時は生のdictを返す
            return payload_data

    def validate(self) -> list[str]:
        """
        メッセージを検証
        
        Returns:
            エラーメッセージのリスト（空なら有効）
        """
        errors = []
        
        if not self.protocol_version:
            errors.append("protocol_version is required")
        if not self.message_type:
            errors.append("message_type is required")
        if not self.message_id:
            errors.append("message_id is required")
        if not self.timestamp:
            errors.append("timestamp is required")
        if not self.sender_id:
            errors.append("sender_id is required")
        if self.payload is None:
            errors.append("payload is required")
        
        return errors

    def is_valid(self) -> bool:
        """メッセージが有効かどうか"""
        return len(self.validate()) == 0


# ==================== ファクトリ関数 ====================

def create_startup_info(
    sender_id: str,
    agent_id: str,
    role: AgentRole,
    channels: ChannelsConfig,
    config: Optional[AgentConfig] = None
) -> Message:
    """起動情報メッセージを作成"""
    payload = StartupInfoPayload(
        agent_id=agent_id,
        role=role,
        channels=channels,
        config=config or AgentConfig()
    )
    return Message.create(
        message_type=MessageType.STARTUP_INFO,
        sender_id=sender_id,
        payload=payload
    )


def create_task_dispatch(
    sender_id: str,
    task_id: str,
    task_type: TaskType,
    instruction: str,
    priority: TaskPriority = TaskPriority.NORMAL,
    timeout_seconds: int = 300,
    target_files: Optional[list[str]] = None,
    context: Optional[dict] = None,
    constraints: Optional[list[str]] = None,
    dependencies: Optional[list[str]] = None
) -> Message:
    """タスク配信メッセージを作成"""
    content = TaskContent(
        instruction=instruction,
        target_files=target_files or [],
        context=context or {},
        constraints=constraints or []
    )
    timeout = TaskTimeout(seconds=timeout_seconds)
    payload = TaskDispatchPayload(
        task_id=task_id,
        task_type=task_type,
        content=content,
        priority=priority,
        timeout=timeout,
        dependencies=dependencies or []
    )
    return Message.create(
        message_type=MessageType.TASK_DISPATCH,
        sender_id=sender_id,
        payload=payload
    )


def create_task_completion(
    sender_id: str,
    task_id: str,
    agent_id: str,
    status: TaskStatus,
    started_at: datetime,
    completed_at: datetime,
    summary: str = "",
    data: Optional[dict] = None,
    artifacts: Optional[list[dict]] = None,
    error: Optional[TaskError] = None
) -> Message:
    """完了報告メッセージを作成"""
    execution_time = ExecutionTime.create(started_at, completed_at)
    output = TaskOutput(
        summary=summary,
        data=data or {},
        artifacts=artifacts or []
    )
    payload = TaskCompletionPayload(
        task_id=task_id,
        agent_id=agent_id,
        status=status,
        execution_time=execution_time,
        output=output,
        error=error
    )
    return Message.create(
        message_type=MessageType.TASK_COMPLETION,
        sender_id=sender_id,
        payload=payload
    )


def create_user_notification(
    sender_id: str,
    event: NotificationEvent,
    agent_id: str,
    agent_type: AgentRole,
    message: str,
    task_id: Optional[str] = None,
    data: Optional[dict] = None
) -> Message:
    """ユーザー通知メッセージを作成"""
    payload = UserNotificationPayload(
        event=event,
        agent_id=agent_id,
        agent_type=agent_type,
        message=message,
        task_id=task_id,
        data=data or {}
    )
    return Message.create(
        message_type=MessageType.USER_NOTIFICATION,
        sender_id=sender_id,
        payload=payload
    )


def create_shutdown_command(
    sender_id: str,
    reason: str = "all_tasks_completed",
    graceful: bool = True,
    timeout_seconds: int = 30
) -> Message:
    """終了指示メッセージを作成"""
    payload = ShutdownCommandPayload(
        reason=reason,
        graceful=graceful,
        timeout_seconds=timeout_seconds
    )
    return Message.create(
        message_type=MessageType.SHUTDOWN_COMMAND,
        sender_id=sender_id,
        payload=payload
    )
