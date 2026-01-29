"""
RPUSH送信モジュール

Redisリストへのメッセージ送信機能を提供。
共通クライアント（redis_client.py）を使用してRPUSH操作を実行する。
"""

import json
from typing import Any, Optional, Union

from .config import RedisConfig, get_default_config
from .redis_client import RespRedisClient, RedisConnectionError, RedisCommandError
from .messages import TaskMessage, ReportMessage, BaseMessage
from .utils import get_iso_timestamp


class SendResult:
    """
    送信結果を表すクラス
    
    Attributes:
        success: 送信成功かどうか
        list_length: 送信後のリスト長
        message_count: 送信したメッセージ数
        published: Pub/Subに発行したかどうか
        subscribers: Pub/Subのサブスクライバー数
        error: エラーメッセージ（失敗時）
    """
    
    def __init__(
        self,
        success: bool = True,
        list_length: int = 0,
        message_count: int = 0,
        published: bool = False,
        subscribers: int = 0,
        error: Optional[str] = None,
    ):
        self.success = success
        self.list_length = list_length
        self.message_count = message_count
        self.published = published
        self.subscribers = subscribers
        self.error = error
    
    def __repr__(self) -> str:
        return (
            f"SendResult(success={self.success}, "
            f"list_length={self.list_length}, "
            f"message_count={self.message_count}, "
            f"published={self.published})"
        )


class RedisSender:
    """
    Redisへのメッセージ送信クラス
    
    RespRedisClientを使用してRPUSH操作とPub/Sub送信を行う。
    
    Attributes:
        client: RespRedisClientインスタンス
    """
    
    def __init__(
        self,
        host: str = "redis",
        port: int = 6379,
        timeout: float = 10.0,
        config: Optional[RedisConfig] = None,
        client: Optional[RespRedisClient] = None,
    ):
        """
        送信クラスを初期化
        
        Args:
            host: Redisホスト名
            port: Redisポート番号
            timeout: ソケットタイムアウト
            config: Redis設定オブジェクト
            client: 既存のクライアントインスタンス（テスト用）
        """
        if client:
            self.client = client
        elif config:
            self.client = RespRedisClient(config=config)
        else:
            self.client = RespRedisClient(host=host, port=port, timeout=timeout)
    
    def send_message(self, list_name: str, message: str) -> SendResult:
        """
        単一メッセージをリストに送信
        
        Args:
            list_name: リスト名
            message: 送信するメッセージ
        
        Returns:
            送信結果
        """
        try:
            list_length = self.client.rpush(list_name, message)
            return SendResult(
                success=True,
                list_length=list_length,
                message_count=1,
            )
        except (RedisConnectionError, RedisCommandError) as e:
            return SendResult(success=False, error=str(e))
    
    def send_messages(self, list_name: str, messages: list[str]) -> SendResult:
        """
        複数メッセージを一括でリストに送信
        
        Args:
            list_name: リスト名
            messages: 送信するメッセージのリスト
        
        Returns:
            送信結果
        """
        if not messages:
            return SendResult(success=True, message_count=0)
        
        try:
            list_length = self.client.rpush(list_name, *messages)
            return SendResult(
                success=True,
                list_length=list_length,
                message_count=len(messages),
            )
        except (RedisConnectionError, RedisCommandError) as e:
            return SendResult(success=False, error=str(e))
    
    def send_task(self, list_name: str, task_message: TaskMessage) -> SendResult:
        """
        TaskMessageオブジェクトをリストに送信
        
        Args:
            list_name: リスト名
            task_message: タスクメッセージオブジェクト
        
        Returns:
            送信結果
        """
        return self.send_message(list_name, task_message.to_json())
    
    def send_report(self, list_name: str, report_message: ReportMessage) -> SendResult:
        """
        ReportMessageオブジェクトをリストに送信
        
        Args:
            list_name: リスト名
            report_message: レポートメッセージオブジェクト
        
        Returns:
            送信結果
        """
        return self.send_message(list_name, report_message.to_json())
    
    def send_any_message(self, list_name: str, message: BaseMessage) -> SendResult:
        """
        任意のBaseMessage派生オブジェクトをリストに送信
        
        Args:
            list_name: リスト名
            message: メッセージオブジェクト
        
        Returns:
            送信結果
        """
        return self.send_message(list_name, message.to_json())
    
    def publish_to_monitor(
        self,
        channel: str,
        queue: str,
        message: str,
    ) -> int:
        """
        モニターチャンネルへの通知を送信
        
        Args:
            channel: Pub/Subチャンネル名
            queue: キュー名
            message: 元のメッセージ
        
        Returns:
            メッセージを受信したサブスクライバー数
        """
        payload = create_publish_payload(queue, message)
        return self.client.publish(channel, payload)
    
    def send_with_publish(
        self,
        list_name: str,
        message: str,
        channel: str,
    ) -> SendResult:
        """
        RPUSH + Pub/Sub同時送信
        
        リストにメッセージを追加し、同時にチャンネルにも通知を送信する。
        
        Args:
            list_name: リスト名
            message: 送信するメッセージ
            channel: Pub/Subチャンネル名
        
        Returns:
            送信結果
        """
        # まずRPUSHを実行
        result = self.send_message(list_name, message)
        if not result.success:
            return result
        
        # 次にPUBLISHを実行
        try:
            subscribers = self.publish_to_monitor(channel, list_name, message)
            result.published = True
            result.subscribers = subscribers
        except (RedisConnectionError, RedisCommandError) as e:
            # PUBLISHが失敗してもRPUSHは成功しているのでエラーとしない
            result.error = f"PUBLISH failed: {e}"
        
        return result
    
    def send_messages_with_publish(
        self,
        list_name: str,
        messages: list[str],
        channel: str,
    ) -> SendResult:
        """
        複数メッセージのRPUSH + 各メッセージへのPub/Sub通知
        
        Args:
            list_name: リスト名
            messages: 送信するメッセージのリスト
            channel: Pub/Subチャンネル名
        
        Returns:
            送信結果
        """
        if not messages:
            return SendResult(success=True, message_count=0)
        
        # まずRPUSHを実行
        result = self.send_messages(list_name, messages)
        if not result.success:
            return result
        
        # 各メッセージに対してPUBLISHを実行
        total_subscribers = 0
        publish_errors = []
        
        for msg in messages:
            try:
                subscribers = self.publish_to_monitor(channel, list_name, msg)
                total_subscribers += subscribers
            except (RedisConnectionError, RedisCommandError) as e:
                publish_errors.append(str(e))
        
        result.published = True
        result.subscribers = total_subscribers
        
        if publish_errors:
            result.error = f"PUBLISH errors: {len(publish_errors)} failures"
        
        return result


def create_publish_payload(queue_name: str, message: str) -> str:
    """
    Pub/Sub用のJSONペイロードを作成
    
    Args:
        queue_name: キュー名
        message: 元のメッセージ
    
    Returns:
        JSON形式のペイロード文字列
    """
    payload = {
        "queue": queue_name,
        "message": message,
        "timestamp": get_iso_timestamp(),
    }
    return json.dumps(payload, ensure_ascii=False)


# 便利関数（モジュールレベル）

def send_message(
    list_name: str,
    message: str,
    host: str = "redis",
    port: int = 6379,
) -> SendResult:
    """
    単一メッセージを送信するユーティリティ関数
    
    Args:
        list_name: リスト名
        message: 送信するメッセージ
        host: Redisホスト名
        port: Redisポート番号
    
    Returns:
        送信結果
    """
    sender = RedisSender(host=host, port=port)
    return sender.send_message(list_name, message)


def send_messages(
    list_name: str,
    messages: list[str],
    host: str = "redis",
    port: int = 6379,
) -> SendResult:
    """
    複数メッセージを送信するユーティリティ関数
    
    Args:
        list_name: リスト名
        messages: 送信するメッセージのリスト
        host: Redisホスト名
        port: Redisポート番号
    
    Returns:
        送信結果
    """
    sender = RedisSender(host=host, port=port)
    return sender.send_messages(list_name, messages)


def send_with_publish(
    list_name: str,
    message: str,
    channel: str,
    host: str = "redis",
    port: int = 6379,
) -> SendResult:
    """
    RPUSH + Pub/Sub同時送信のユーティリティ関数
    
    Args:
        list_name: リスト名
        message: 送信するメッセージ
        channel: Pub/Subチャンネル名
        host: Redisホスト名
        port: Redisポート番号
    
    Returns:
        送信結果
    """
    sender = RedisSender(host=host, port=port)
    return sender.send_with_publish(list_name, message, channel)
