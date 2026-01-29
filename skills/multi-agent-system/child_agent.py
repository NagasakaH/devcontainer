#!/usr/bin/env python3
"""
子エージェント（Child Agent）

タスク待機・実行・報告を行う子エージェントです。
親エージェントからのタスクを BLPOP で待機し、完了後に RPUSH で報告します。

使用方法:
    python child_agent.py --session-id <session_id> --agent-id child-1 [オプション]

オプション:
    --session-id    セッションID（必須）
    --agent-id      エージェントID（child-1 〜 child-5）（必須）
    --redis-host    Redisホスト（デフォルト: localhost）
    --redis-port    Redisポート（デフォルト: 6379）
    --blpop-timeout BLPOPタイムアウト秒数（デフォルト: 5）
    --log-level     ログレベル（DEBUG/INFO/WARN/ERROR）（デフォルト: INFO）

例:
    python child_agent.py --session-id session-20260129 --agent-id child-1
    python child_agent.py --session-id session-20260129 --agent-id child-2 --redis-host redis
"""

import argparse
import json
import signal
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from typing import Optional, Callable, Any

# 共通ライブラリのパスを追加
sys.path.insert(0, str(__file__).replace("/child_agent.py", ""))

from lib.redis_client import RedisClient, RedisConfig, RedisConnectionError
from lib.channel_config import ChannelConfig
from lib.message import (
    Message,
    MessageType,
    TaskDispatchPayload,
    TaskCompletionPayload,
    UserNotificationPayload,
    ShutdownCommandPayload,
    TaskStatus,
    NotificationEvent,
    AgentRole,
    ExecutionTime,
    TaskOutput,
    TaskError,
    create_task_completion,
    create_user_notification,
)
from lib.logger import AgentLogger, LogLevel


class ChildAgent:
    """
    子エージェント
    
    タスク待機・実行・報告のメインループを管理します。
    
    動作フロー:
        1. 初期化: Redis接続、チャンネル情報設定
        2. 待機ループ: BLPOP でタスク待機
        3. タスク実行: 受信したタスクを実行
        4. 完了報告: RPUSH で結果を報告
        5. 待機に戻る or 終了
    """
    
    def __init__(
        self,
        session_id: str,
        agent_id: str,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        blpop_timeout: int = 5,
        log_level: LogLevel = LogLevel.INFO,
    ):
        """
        子エージェントを初期化
        
        Args:
            session_id: セッションID
            agent_id: エージェントID（child-1 〜 child-5）
            redis_host: Redisホスト
            redis_port: Redisポート
            blpop_timeout: BLPOPタイムアウト秒数
            log_level: ログレベル
        """
        self.session_id = session_id
        self.agent_id = agent_id
        self.blpop_timeout = blpop_timeout
        
        # チャンネル設定
        self.channels = ChannelConfig(session_id=session_id)
        
        # Redis設定
        self.redis_config = RedisConfig(
            host=redis_host,
            port=redis_port,
        )
        self.redis: Optional[RedisClient] = None
        self.pubsub_redis: Optional[RedisClient] = None  # Pub/Sub用の別接続
        
        # ロガー設定
        self.logger = AgentLogger(
            agent_id=agent_id,
            agent_type="child",
            level=log_level,
        )
        
        # 状態管理
        self._running = False
        self._shutdown_requested = threading.Event()
        self._current_task: Optional[TaskDispatchPayload] = None
        self._lock = threading.Lock()
        
        # タスク実行ハンドラー（オーバーライド可能）
        self._task_handler: Callable[[TaskDispatchPayload], dict] = self._default_task_handler
    
    def connect(self) -> None:
        """Redis接続を確立"""
        try:
            # メイン接続（BLPOP/RPUSH用）
            self.redis = RedisClient(self.redis_config)
            self.redis.connect()
            
            # Pub/Sub用の別接続
            self.pubsub_redis = RedisClient(self.redis_config)
            self.pubsub_redis.connect()
            
            self.logger.info(
                "Redis connected",
                host=self.redis_config.host,
                port=self.redis_config.port,
            )
        except RedisConnectionError as e:
            self.logger.error("Failed to connect to Redis", error=str(e))
            raise
    
    def disconnect(self) -> None:
        """Redis接続を切断"""
        if self.pubsub_redis:
            self.pubsub_redis.close()
            self.pubsub_redis = None
        if self.redis:
            self.redis.close()
            self.redis = None
        self.logger.info("Redis disconnected")
    
    def start(self) -> None:
        """エージェントを起動"""
        self.logger.info(
            "Starting child agent",
            session_id=self.session_id,
            task_queue=self.channels.task_queue,
            completion_queue=self.channels.completion_queue,
        )
        
        # 接続
        self.connect()
        
        # 終了チャンネルの購読を開始
        self._subscribe_terminate_channel()
        
        # 準備完了通知
        self._notify_agent_ready()
        
        # メインループ開始
        self._running = True
        self._run_loop()
    
    def stop(self, reason: str = "shutdown_requested") -> None:
        """エージェントを停止"""
        self.logger.info("Stopping child agent", reason=reason)
        self._running = False
        self._shutdown_requested.set()
    
    def _subscribe_terminate_channel(self) -> None:
        """終了チャンネルを購読"""
        def on_terminate(channel: str, message: str):
            try:
                data = json.loads(message) if isinstance(message, str) else message
                msg = Message.from_dict(data)
                
                if msg.message_type == MessageType.SHUTDOWN_COMMAND:
                    payload = msg.payload
                    reason = payload.get("reason", "shutdown_command") if isinstance(payload, dict) else getattr(payload, "reason", "shutdown_command")
                    self.logger.info(
                        "Received shutdown command",
                        reason=reason,
                    )
                    self.stop(reason=reason)
            except Exception as e:
                self.logger.error("Error processing terminate message", error=str(e))
        
        if self.pubsub_redis:
            self.pubsub_redis.subscribe(
                self.channels.terminate_channel,
                callback=on_terminate,
            )
            self.logger.debug(
                "Subscribed to terminate channel",
                channel=self.channels.terminate_channel,
            )
    
    def _run_loop(self) -> None:
        """メイン待機ループ"""
        self.logger.info("Entering main loop")
        
        while self._running and not self._shutdown_requested.is_set():
            try:
                # タスクを待機（BLPOP）
                result = self.redis.blpop(
                    self.channels.task_queue,
                    timeout=self.blpop_timeout,
                )
                
                if result is None:
                    # タイムアウト - 終了チェックして再待機
                    continue
                
                key, message = result
                self.logger.debug("Received message from queue", key=key)
                
                # メッセージをパース
                try:
                    data = json.loads(message) if isinstance(message, str) else message
                    msg = Message.from_dict(data)
                except json.JSONDecodeError as e:
                    self.logger.error("Invalid JSON message", error=str(e))
                    continue
                
                # タスク配信メッセージを処理
                if msg.message_type == MessageType.TASK_DISPATCH:
                    self._handle_task(msg)
                else:
                    self.logger.warn(
                        "Unexpected message type",
                        message_type=msg.message_type.value,
                    )
                    
            except KeyboardInterrupt:
                self.logger.info("Interrupted by user")
                break
            except Exception as e:
                self.logger.error(
                    "Error in main loop",
                    error=str(e),
                    traceback=traceback.format_exc(),
                )
                time.sleep(1)  # エラー時は少し待機
        
        # 終了処理
        self._shutdown()
    
    def _handle_task(self, msg: Message) -> None:
        """タスクを処理"""
        payload = msg.payload
        
        # ペイロードをTaskDispatchPayloadに変換
        if isinstance(payload, dict):
            payload = TaskDispatchPayload.from_dict(payload)
        
        task_id = payload.task_id
        instruction = payload.content.instruction if hasattr(payload.content, "instruction") else str(payload.content)
        
        self.logger.info(
            "Processing task",
            task_id=task_id,
            task_type=payload.task_type.value if hasattr(payload.task_type, "value") else str(payload.task_type),
        )
        
        with self._lock:
            self._current_task = payload
        
        started_at = datetime.now(timezone.utc)
        
        # タスク開始通知
        self._notify_task_started(task_id, instruction)
        
        # タスク実行
        try:
            result = self._task_handler(payload)
            completed_at = datetime.now(timezone.utc)
            
            status = TaskStatus.SUCCESS
            error = None
            summary = result.get("summary", "タスク完了")
            data = result.get("data", {})
            
            self.logger.info(
                "Task completed successfully",
                task_id=task_id,
                duration_ms=int((completed_at - started_at).total_seconds() * 1000),
            )
            
        except Exception as e:
            completed_at = datetime.now(timezone.utc)
            status = TaskStatus.FAILURE
            error = TaskError(
                code="E_TASK_EXECUTION",
                message=str(e),
                details={"traceback": traceback.format_exc()},
                recoverable=True,
            )
            summary = f"タスク実行エラー: {e}"
            data = {}
            
            self.logger.error(
                "Task failed",
                task_id=task_id,
                error=str(e),
            )
        
        with self._lock:
            self._current_task = None
        
        # タスク完了通知
        self._notify_task_completed(task_id, summary, status == TaskStatus.SUCCESS)
        
        # 完了報告
        self._report_completion(
            task_id=task_id,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            summary=summary,
            data=data,
            error=error,
        )
    
    def _default_task_handler(self, payload: TaskDispatchPayload) -> dict:
        """
        デフォルトのタスク実行ハンドラー
        
        このメソッドをオーバーライドするか、set_task_handler()で
        カスタムハンドラーを設定して実際のタスク処理を実装します。
        
        Args:
            payload: タスク配信ペイロード
            
        Returns:
            {"summary": "...", "data": {...}} 形式の結果
        """
        # デモ実装: 指示を表示してシミュレート実行
        instruction = payload.content.instruction if hasattr(payload.content, "instruction") else str(payload.content)
        
        self.logger.info(f"Executing task: {instruction}")
        
        # シミュレート: 少し待機
        time.sleep(2)
        
        return {
            "summary": f"タスク「{instruction[:50]}...」を完了しました",
            "data": {
                "instruction_length": len(instruction),
                "executed_by": self.agent_id,
            },
        }
    
    def set_task_handler(self, handler: Callable[[TaskDispatchPayload], dict]) -> None:
        """
        タスク実行ハンドラーを設定
        
        Args:
            handler: タスク実行関数 (payload) -> {"summary": ..., "data": ...}
        """
        self._task_handler = handler
    
    def _notify_agent_ready(self) -> None:
        """エージェント準備完了通知を送信"""
        msg = create_user_notification(
            sender_id=self.agent_id,
            event=NotificationEvent.AGENT_READY,
            agent_id=self.agent_id,
            agent_type=AgentRole.CHILD,
            message=f"{self.agent_id} がタスク待機を開始しました",
        )
        self._publish_notification(msg)
    
    def _notify_task_started(self, task_id: str, description: str) -> None:
        """タスク開始通知を送信"""
        msg = create_user_notification(
            sender_id=self.agent_id,
            event=NotificationEvent.TASK_STARTED,
            agent_id=self.agent_id,
            agent_type=AgentRole.CHILD,
            message=f"タスク開始: {description[:100]}",
            task_id=task_id,
        )
        self._publish_notification(msg)
    
    def _notify_task_completed(self, task_id: str, summary: str, success: bool) -> None:
        """タスク完了通知を送信"""
        event = NotificationEvent.TASK_COMPLETED if success else NotificationEvent.TASK_FAILED
        msg = create_user_notification(
            sender_id=self.agent_id,
            event=event,
            agent_id=self.agent_id,
            agent_type=AgentRole.CHILD,
            message=summary,
            task_id=task_id,
        )
        self._publish_notification(msg)
    
    def _notify_agent_terminated(self, reason: str) -> None:
        """エージェント終了通知を送信"""
        msg = create_user_notification(
            sender_id=self.agent_id,
            event=NotificationEvent.AGENT_TERMINATED,
            agent_id=self.agent_id,
            agent_type=AgentRole.CHILD,
            message=f"{self.agent_id} が終了しました: {reason}",
        )
        self._publish_notification(msg)
    
    def _publish_notification(self, msg: Message) -> None:
        """ユーザー通知をPublish"""
        try:
            if self.redis:
                self.redis.publish(
                    self.channels.notify_channel,
                    msg.to_json(),
                )
                self.logger.debug(
                    "Published notification",
                    channel=self.channels.notify_channel,
                    event=msg.payload.event.value if hasattr(msg.payload, "event") else "unknown",
                )
        except Exception as e:
            self.logger.error("Failed to publish notification", error=str(e))
    
    def _report_completion(
        self,
        task_id: str,
        status: TaskStatus,
        started_at: datetime,
        completed_at: datetime,
        summary: str,
        data: Optional[dict] = None,
        error: Optional[TaskError] = None,
    ) -> None:
        """完了報告をキューに送信"""
        msg = create_task_completion(
            sender_id=self.agent_id,
            task_id=task_id,
            agent_id=self.agent_id,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            summary=summary,
            data=data,
            error=error,
        )
        
        try:
            if self.redis:
                self.redis.rpush(
                    self.channels.completion_queue,
                    msg.to_json(),
                )
                self.logger.info(
                    "Reported task completion",
                    task_id=task_id,
                    status=status.value,
                    queue=self.channels.completion_queue,
                )
        except Exception as e:
            self.logger.error(
                "Failed to report completion",
                task_id=task_id,
                error=str(e),
            )
    
    def _shutdown(self) -> None:
        """シャットダウン処理"""
        self.logger.info("Shutting down")
        
        # 終了通知
        self._notify_agent_terminated("graceful_shutdown")
        
        # 接続を切断
        self.disconnect()
        
        self.logger.info("Shutdown complete")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(
        description="子エージェント - タスク待機・実行・報告",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python child_agent.py --session-id session-001 --agent-id child-1
  python child_agent.py --session-id session-001 --agent-id child-2 --redis-host redis
        """,
    )
    
    parser.add_argument(
        "--session-id",
        required=True,
        help="セッションID",
    )
    parser.add_argument(
        "--agent-id",
        required=True,
        choices=["child-1", "child-2", "child-3", "child-4", "child-5"],
        help="エージェントID（child-1 〜 child-5）",
    )
    parser.add_argument(
        "--redis-host",
        default="localhost",
        help="Redisホスト（デフォルト: localhost）",
    )
    parser.add_argument(
        "--redis-port",
        type=int,
        default=6379,
        help="Redisポート（デフォルト: 6379）",
    )
    parser.add_argument(
        "--blpop-timeout",
        type=int,
        default=5,
        help="BLPOPタイムアウト秒数（デフォルト: 5）",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARN", "ERROR"],
        default="INFO",
        help="ログレベル（デフォルト: INFO）",
    )
    
    return parser.parse_args()


def main() -> int:
    """メインエントリーポイント"""
    args = parse_args()
    
    # ログレベルを変換
    log_level = LogLevel[args.log_level]
    
    # エージェントを作成
    agent = ChildAgent(
        session_id=args.session_id,
        agent_id=args.agent_id,
        redis_host=args.redis_host,
        redis_port=args.redis_port,
        blpop_timeout=args.blpop_timeout,
        log_level=log_level,
    )
    
    # シグナルハンドラを設定
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...", file=sys.stderr)
        agent.stop(reason=f"signal_{signum}")
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # エージェントを起動
    try:
        agent.start()
        return 0
    except RedisConnectionError as e:
        print(f"Error: Cannot connect to Redis: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
