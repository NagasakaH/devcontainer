"""
Multi-Agent System (MAS) 共通ライブラリ

Redis を介した神・親・子エージェント間の通信を支援するライブラリです。

主要コンポーネント:
- RedisClient: Redis操作ラッパー（キュー・Pub/Sub）
- Message: メッセージ生成・解析
- ChannelConfig: チャンネル設定・命名規則
- Logger: 構造化ロギング

プロトコルバージョン: 1.0.0
"""

from .redis_client import RedisClient, RedisConfig
from .message import (
    Message,
    MessageType,
    StartupInfoPayload,
    TaskDispatchPayload,
    TaskCompletionPayload,
    UserNotificationPayload,
    ShutdownCommandPayload,
    TaskType,
    TaskPriority,
    TaskStatus,
    NotificationEvent,
    AgentRole,
    TaskContent,
    TaskTimeout,
    TaskMetadata,
    ExecutionTime,
    TaskOutput,
    TaskError,
    ChannelsConfig,
    AgentConfig,
    create_startup_info,
    create_task_dispatch,
    create_task_completion,
    create_user_notification,
    create_shutdown_command,
    generate_uuid,
    generate_timestamp,
    PROTOCOL_VERSION,
)
from .channel_config import ChannelConfig, ChannelType
from .logger import AgentLogger, LogLevel

__version__ = "1.0.0"
__protocol_version__ = "1.0.0"

__all__ = [
    # Version
    "__version__",
    "__protocol_version__",
    # Redis Client
    "RedisClient",
    "RedisConfig",
    # Messages
    "Message",
    "MessageType",
    "StartupInfoPayload",
    "TaskDispatchPayload",
    "TaskCompletionPayload",
    "UserNotificationPayload",
    "ShutdownCommandPayload",
    "TaskType",
    "TaskPriority",
    "TaskStatus",
    "NotificationEvent",
    "AgentRole",
    "TaskContent",
    "TaskTimeout",
    "TaskMetadata",
    "ExecutionTime",
    "TaskOutput",
    "TaskError",
    "ChannelsConfig",
    "AgentConfig",
    # Factory functions
    "create_startup_info",
    "create_task_dispatch",
    "create_task_completion",
    "create_user_notification",
    "create_shutdown_command",
    "generate_uuid",
    "generate_timestamp",
    "PROTOCOL_VERSION",
    # Channel Config
    "ChannelConfig",
    "ChannelType",
    # Logger
    "AgentLogger",
    "LogLevel",
]
