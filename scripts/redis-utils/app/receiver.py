"""
BLPOP受信モジュール

Redisリストからブロッキング操作でメッセージを受信する。
共通クライアント（redis_client.py）を使用。

Usage:
    from app.receiver import (
        receive_message,
        receive_messages,
        receive_task,
        receive_report,
        receive_any_message,
        wait_for_shutdown,
    )
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Iterator, Optional, Union

from .config import RedisConfig, get_default_config
from .messages import (
    BaseMessage,
    MessageType,
    ReportMessage,
    ShutdownMessage,
    StatusMessage,
    TaskMessage,
    parse_message,
)
from .redis_client import RedisClient, RedisConnectionError
from .utils import get_iso_timestamp


@dataclass
class ReceivedMessage:
    """
    受信したメッセージのラッパークラス
    
    Attributes:
        list_name: 受信元のリスト名
        raw_data: 受信した生データ
        timestamp: 受信日時（ISO 8601形式）
        index: 受信インデックス（連続受信時）
        parsed: パース済みメッセージ（parse_message成功時）
    """
    list_name: str
    raw_data: str
    timestamp: str
    index: int = 0
    parsed: Optional[BaseMessage] = None
    
    def to_dict(self) -> dict[str, Any]:
        """
        辞書形式に変換
        
        Returns:
            メッセージの辞書表現
        """
        result = {
            "index": self.index,
            "list": self.list_name,
            "message": self.raw_data,
            "timestamp": self.timestamp,
        }
        if self.parsed:
            result["parsed_type"] = self.parsed.type
        return result
    
    def to_json(self, ensure_ascii: bool = False, indent: Optional[int] = None) -> str:
        """
        JSON文字列に変換
        
        Args:
            ensure_ascii: ASCII文字のみにエスケープするか
            indent: インデント幅
        
        Returns:
            JSON文字列
        """
        return json.dumps(self.to_dict(), ensure_ascii=ensure_ascii, indent=indent)
    
    def as_json_data(self) -> Optional[dict[str, Any]]:
        """
        raw_dataをJSONとしてパース
        
        Returns:
            パース結果の辞書、パース失敗時はNone
        """
        try:
            return json.loads(self.raw_data)
        except (json.JSONDecodeError, TypeError):
            return None


class MessageReceiver:
    """
    BLPOPを使用したメッセージ受信クラス
    
    redis-pyのRedisClientを使用してブロッキング受信を行う。
    
    Attributes:
        client: RedisClientインスタンス
    """
    
    def __init__(
        self,
        host: str = "redis",
        port: int = 6379,
        config: Optional[RedisConfig] = None,
    ):
        """
        受信クライアントを初期化
        
        Args:
            host: Redisホスト名（configが指定された場合は無視）
            port: Redisポート番号（configが指定された場合は無視）
            config: Redis設定オブジェクト（指定された場合はこちらを優先）
        """
        if config:
            self.client = RedisClient(config=config)
        else:
            self.client = RedisClient(host=host, port=port)
    
    def ping(self) -> bool:
        """
        Redis接続を確認
        
        Returns:
            接続成功時True
        
        Raises:
            RedisConnectionError: 接続失敗時
        """
        return self.client.ping()
    
    def receive(
        self,
        list_name: Union[str, list[str]],
        timeout: int = 0,
    ) -> Optional[ReceivedMessage]:
        """
        リストからメッセージを1件受信
        
        Args:
            list_name: 受信対象のリスト名（または複数リスト名のリスト）
            timeout: タイムアウト秒数（0は無限待機）
        
        Returns:
            ReceivedMessage（タイムアウト時はNone）
        """
        result = self.client.blpop(list_name, timeout=timeout)
        if result is None:
            return None
        
        received_list, message = result
        return ReceivedMessage(
            list_name=received_list,
            raw_data=message,
            timestamp=get_iso_timestamp(),
            index=1,
        )
    
    def receive_many(
        self,
        list_name: Union[str, list[str]],
        count: int,
        timeout: int = 0,
    ) -> list[ReceivedMessage]:
        """
        リストから複数メッセージを受信
        
        Args:
            list_name: 受信対象のリスト名
            count: 受信するメッセージの最大数
            timeout: 各受信のタイムアウト秒数（0は無限待機）
        
        Returns:
            受信したReceivedMessageのリスト
        """
        messages: list[ReceivedMessage] = []
        
        for i in range(count):
            result = self.client.blpop(list_name, timeout=timeout)
            if result is None:
                break
            
            received_list, message = result
            messages.append(ReceivedMessage(
                list_name=received_list,
                raw_data=message,
                timestamp=get_iso_timestamp(),
                index=i + 1,
            ))
        
        return messages
    
    def receive_iter(
        self,
        list_name: Union[str, list[str]],
        timeout: int = 0,
    ) -> Iterator[ReceivedMessage]:
        """
        リストからメッセージを連続受信するイテレータ
        
        タイムアウトするまで、または外部から停止されるまでメッセージを受信し続ける。
        
        Args:
            list_name: 受信対象のリスト名
            timeout: 各受信のタイムアウト秒数（0は無限待機）
        
        Yields:
            ReceivedMessage
        """
        index = 0
        while True:
            result = self.client.blpop(list_name, timeout=timeout)
            if result is None:
                break
            
            index += 1
            received_list, message = result
            yield ReceivedMessage(
                list_name=received_list,
                raw_data=message,
                timestamp=get_iso_timestamp(),
                index=index,
            )
    
    def receive_and_parse(
        self,
        list_name: Union[str, list[str]],
        timeout: int = 0,
    ) -> Optional[tuple[ReceivedMessage, Optional[BaseMessage]]]:
        """
        メッセージを受信しパースを試みる
        
        Args:
            list_name: 受信対象のリスト名
            timeout: タイムアウト秒数
        
        Returns:
            (ReceivedMessage, パース済みメッセージまたはNone)のタプル、
            タイムアウト時はNone
        """
        received = self.receive(list_name, timeout)
        if received is None:
            return None
        
        try:
            parsed = parse_message(received.raw_data)
            received.parsed = parsed
            return (received, parsed)
        except (json.JSONDecodeError, ValueError, TypeError):
            return (received, None)


# モジュールレベルの便利関数

_default_receiver: Optional[MessageReceiver] = None


def _get_receiver(host: str = "redis", port: int = 6379) -> MessageReceiver:
    """デフォルトレシーバーを取得または作成"""
    global _default_receiver
    if _default_receiver is None:
        _default_receiver = MessageReceiver(host=host, port=port)
    return _default_receiver


def receive_message(
    list_name: str,
    timeout: int = 0,
    host: str = "redis",
    port: int = 6379,
) -> Optional[ReceivedMessage]:
    """
    単一メッセージを受信
    
    Args:
        list_name: 受信対象のリスト名
        timeout: タイムアウト秒数（0は無限待機）
        host: Redisホスト名
        port: Redisポート番号
    
    Returns:
        ReceivedMessage（タイムアウト時はNone）
    """
    receiver = MessageReceiver(host=host, port=port)
    return receiver.receive(list_name, timeout)


def receive_messages(
    list_name: str,
    count: int,
    timeout: int = 0,
    host: str = "redis",
    port: int = 6379,
) -> list[ReceivedMessage]:
    """
    複数メッセージを受信
    
    Args:
        list_name: 受信対象のリスト名
        count: 受信するメッセージの最大数
        timeout: 各受信のタイムアウト秒数（0は無限待機）
        host: Redisホスト名
        port: Redisポート番号
    
    Returns:
        受信したReceivedMessageのリスト
    """
    receiver = MessageReceiver(host=host, port=port)
    return receiver.receive_many(list_name, count, timeout)


def receive_task(
    list_name: str,
    timeout: int = 0,
    host: str = "redis",
    port: int = 6379,
) -> Optional[TaskMessage]:
    """
    TaskMessageを受信
    
    Args:
        list_name: 受信対象のリスト名
        timeout: タイムアウト秒数（0は無限待機）
        host: Redisホスト名
        port: Redisポート番号
    
    Returns:
        TaskMessage（タイムアウトまたはパース失敗時はNone）
    """
    receiver = MessageReceiver(host=host, port=port)
    result = receiver.receive_and_parse(list_name, timeout)
    if result is None:
        return None
    
    received, parsed = result
    if isinstance(parsed, TaskMessage):
        return parsed
    return None


def receive_report(
    list_name: str,
    timeout: int = 0,
    host: str = "redis",
    port: int = 6379,
) -> Optional[ReportMessage]:
    """
    ReportMessageを受信
    
    Args:
        list_name: 受信対象のリスト名
        timeout: タイムアウト秒数（0は無限待機）
        host: Redisホスト名
        port: Redisポート番号
    
    Returns:
        ReportMessage（タイムアウトまたはパース失敗時はNone）
    """
    receiver = MessageReceiver(host=host, port=port)
    result = receiver.receive_and_parse(list_name, timeout)
    if result is None:
        return None
    
    received, parsed = result
    if isinstance(parsed, ReportMessage):
        return parsed
    return None


def receive_any_message(
    list_name: str,
    timeout: int = 0,
    host: str = "redis",
    port: int = 6379,
) -> Optional[tuple[ReceivedMessage, Optional[BaseMessage]]]:
    """
    任意のメッセージを受信し自動でタイプを判別
    
    Args:
        list_name: 受信対象のリスト名
        timeout: タイムアウト秒数（0は無限待機）
        host: Redisホスト名
        port: Redisポート番号
    
    Returns:
        (ReceivedMessage, パース済みメッセージまたはNone)のタプル、
        タイムアウト時はNone
    """
    receiver = MessageReceiver(host=host, port=port)
    return receiver.receive_and_parse(list_name, timeout)


def wait_for_shutdown(
    list_name: str,
    timeout: int = 0,
    host: str = "redis",
    port: int = 6379,
) -> Optional[ShutdownMessage]:
    """
    シャットダウンメッセージを待機
    
    シャットダウンメッセージを受信するまでブロッキング。
    他のメッセージタイプは無視（キューから削除される）。
    
    Args:
        list_name: 受信対象のリスト名
        timeout: タイムアウト秒数（0は無限待機）
        host: Redisホスト名
        port: Redisポート番号
    
    Returns:
        ShutdownMessage（タイムアウト時はNone）
    """
    receiver = MessageReceiver(host=host, port=port)
    
    while True:
        result = receiver.receive_and_parse(list_name, timeout)
        if result is None:
            return None
        
        received, parsed = result
        if isinstance(parsed, ShutdownMessage):
            return parsed
        # 他のメッセージタイプは無視して次を待つ
