"""
Redis操作共通モジュール

summoner、moogle、chocoboエージェントから利用するRedis操作の共通ライブラリ。
"""

from .config import RedisConfig, get_default_config
from .redis_client import RedisClient, RespRedisClient
from .messages import TaskMessage, ReportMessage, ShutdownMessage, MessageType
from .utils import (
    generate_session_id,
    generate_uuid_session_id,
    get_timestamp,
    get_iso_timestamp,
    get_default_prefix,
)
from .orchestration import (
    OrchestrationConfig,
    initialize_orchestration,
    initialize_summoner_orchestration,
    get_config,
    cleanup_session,
)
from .sender import (
    RedisSender,
    SendResult,
    send_message,
    send_messages,
    send_with_publish,
    create_publish_payload,
)
from .receiver import (
    MessageReceiver,
    ReceivedMessage,
    receive_message,
    receive_messages,
    receive_task,
    receive_report,
    receive_any_message,
    wait_for_shutdown,
)

__version__ = "1.0.0"

__all__ = [
    # config
    "RedisConfig",
    "get_default_config",
    # redis_client
    "RedisClient",
    "RespRedisClient",
    # messages
    "TaskMessage",
    "ReportMessage",
    "ShutdownMessage",
    "MessageType",
    # utils
    "generate_session_id",
    "generate_uuid_session_id",
    "get_timestamp",
    "get_iso_timestamp",
    "get_default_prefix",
    # orchestration
    "OrchestrationConfig",
    "initialize_orchestration",
    "initialize_summoner_orchestration",
    "get_config",
    "cleanup_session",
    # sender
    "RedisSender",
    "SendResult",
    "send_message",
    "send_messages",
    "send_with_publish",
    "create_publish_payload",
    # receiver
    "MessageReceiver",
    "ReceivedMessage",
    "receive_message",
    "receive_messages",
    "receive_task",
    "receive_report",
    "receive_any_message",
    "wait_for_shutdown",
]
