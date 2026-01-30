"""
Pub/Sub リスナー

Redis Pub/Subを購読し、メッセージをリアルタイムで受信する。
スレッドを使用して非同期でメッセージを受信。
"""

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from queue import Queue, Empty
from typing import Any, Callable, Optional

import redis

from ...config import RedisConfig, get_default_config


@dataclass
class MonitorMessage:
    """モニターメッセージ
    
    受信データの "message" フィールドを対象とする。
    message フィールドは {"type": "...", "task_id": "..."} 形式。
    """
    timestamp: datetime
    channel: str
    raw_data: str
    parsed_data: Optional[dict[str, Any]] = None
    message_type: str = "unknown"  # "task", "report", その他
    display_content: str = ""  # task_id の中身
    sender: str = "unknown"  # 送信者（"moogle", "chocobo-N", など）
    
    def __post_init__(self):
        """パースとメタデータ抽出"""
        if self.parsed_data is None:
            try:
                self.parsed_data = json.loads(self.raw_data)
            except (json.JSONDecodeError, TypeError):
                self.parsed_data = {"raw": self.raw_data}
        
        # message フィールドから type と表示内容を抽出
        if isinstance(self.parsed_data, dict):
            message_field = self.parsed_data.get("message")
            
            # message_field が文字列の場合はJSONパースする
            if isinstance(message_field, str):
                try:
                    message_field = json.loads(message_field)
                except (json.JSONDecodeError, TypeError):
                    pass
            
            if isinstance(message_field, dict):
                self.message_type = message_field.get("type", "unknown")
                # タイプに応じた表示内容を設定
                if self.message_type == "task":
                    # taskの場合はinstructionまたはpromptを使用
                    self.display_content = message_field.get("instruction", "") or message_field.get("prompt", "")
                elif self.message_type == "report":
                    # reportの場合はresultを使用
                    self.display_content = message_field.get("result", "")
                else:
                    # その他の場合はtask_idをフォールバック
                    self.display_content = message_field.get("task_id", "")
                
                # 送信者を判定
                self.sender = self._determine_sender(message_field)
            else:
                # message フィールドがない場合はフォールバック
                self.message_type = "unknown"
                self.display_content = str(message_field) if message_field else ""
                self.sender = "unknown"
    
    def _determine_sender(self, message_data: dict[str, Any]) -> str:
        """メッセージタイプとchocobo_id/child_idから送信者を判定
        
        Args:
            message_data: messageフィールドの内容
            
        Returns:
            送信者を表す文字列（"moogle", "chocobo_N", "chocobo", "unknown"）
        """
        msg_type = message_data.get("type", "unknown")
        # chocobo_id を優先、なければ child_id をフォールバック
        chocobo_id = message_data.get("chocobo_id") or message_data.get("child_id")
        
        if msg_type == "task":
            return "moogle"
        elif msg_type == "report":
            return f"chocobo_{chocobo_id}" if chocobo_id is not None else "chocobo"
        elif msg_type == "status":
            return f"chocobo_{chocobo_id}" if chocobo_id is not None else "chocobo"
        elif msg_type == "shutdown":
            return "moogle"
        else:
            return "unknown"
    
    def get_display_content(self) -> str:
        """表示用の内容を取得（task_id の内容をそのまま返す）"""
        return self.display_content


class PubSubListener:
    """Pub/Sub リスナー（スレッドベース）"""
    
    def __init__(
        self,
        channel: str,
        config: Optional[RedisConfig] = None,
        message_callback: Optional[Callable[[MonitorMessage], None]] = None,
    ):
        """
        初期化
        
        Args:
            channel: 購読するチャンネル名
            config: Redis設定（Noneの場合はデフォルト設定を使用）
            message_callback: メッセージ受信時のコールバック
        """
        self.channel = channel
        self.config = config or get_default_config()
        self.message_callback = message_callback
        
        self._client: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._message_queue: Queue[MonitorMessage] = Queue(maxsize=1000)
    
    @property
    def client(self) -> redis.Redis:
        """Redisクライアントを取得（遅延初期化）"""
        if self._client is None:
            self._client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                decode_responses=True,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
            )
        return self._client
    
    def start(self) -> bool:
        """
        リスナーを開始
        
        Returns:
            開始成功時True
        """
        if self._running:
            return True
        
        try:
            self._pubsub = self.client.pubsub()
            self._pubsub.subscribe(self.channel)
            self._running = True
            
            self._thread = threading.Thread(
                target=self._listen_loop,
                daemon=True
            )
            self._thread.start()
            
            return True
        
        except redis.ConnectionError as e:
            raise ConnectionError(f"Redis接続エラー: {e}")
        except Exception as e:
            raise RuntimeError(f"リスナー開始エラー: {e}")
    
    def stop(self) -> None:
        """リスナーを停止"""
        self._running = False
        
        if self._pubsub:
            try:
                self._pubsub.unsubscribe()
                self._pubsub.close()
            except Exception:
                pass
            self._pubsub = None
        
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
    
    def _listen_loop(self) -> None:
        """メッセージ受信ループ"""
        while self._running and self._pubsub:
            try:
                message = self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )
                
                if message and message.get("type") == "message":
                    monitor_msg = MonitorMessage(
                        timestamp=datetime.now(),
                        channel=message.get("channel", ""),
                        raw_data=message.get("data", ""),
                    )
                    
                    # キューに追加
                    try:
                        self._message_queue.put_nowait(monitor_msg)
                    except Exception:
                        # キューがいっぱいの場合は古いメッセージを削除
                        try:
                            self._message_queue.get_nowait()
                            self._message_queue.put_nowait(monitor_msg)
                        except Empty:
                            pass
                    
                    # コールバックを呼び出し
                    if self.message_callback:
                        try:
                            self.message_callback(monitor_msg)
                        except Exception:
                            pass
            
            except redis.ConnectionError:
                if self._running:
                    time.sleep(1.0)
            except Exception:
                if self._running:
                    time.sleep(0.5)
    
    def get_messages(self, max_count: int = 100) -> list[MonitorMessage]:
        """
        キューからメッセージを取得
        
        Args:
            max_count: 取得する最大メッセージ数
        
        Returns:
            メッセージのリスト
        """
        messages: list[MonitorMessage] = []
        
        while len(messages) < max_count:
            try:
                msg = self._message_queue.get_nowait()
                messages.append(msg)
            except Empty:
                break
        
        return messages
    
    def has_messages(self) -> bool:
        """未読メッセージがあるか"""
        return not self._message_queue.empty()
    
    @property
    def is_running(self) -> bool:
        """リスナーが動作中か"""
        return self._running
