#!/usr/bin/env python3
"""
親エージェント（Parent Agent）

タスク配信と完了報告管理を担当するエージェントです。

機能:
- 神エージェントから受け取った設定に基づき初期化
- ユーザーからの作業指示をタスクに分割して子エージェントに配信
- 子エージェントからの完了報告を収集し、進捗を追跡
- 作業開始・完了をユーザーに通知
- 全タスク完了後に終了指示を発行

使用例:
    python parent_agent.py --session-id abc123 --agent-id parent-001 --task "コードレビューしてください"
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

# プロジェクト内ライブラリをインポート可能にする
sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

from lib import (
    RedisClient,
    RedisConfig,
    ChannelConfig,
    AgentLogger,
    LogLevel,
    Message,
    MessageType,
    TaskType,
    TaskPriority,
    TaskStatus,
    NotificationEvent,
    AgentRole,
    create_task_dispatch,
    create_user_notification,
    create_shutdown_command,
    generate_uuid,
)


@dataclass
class TaskInfo:
    """タスク情報を保持するデータクラス"""

    task_id: str
    instruction: str
    task_type: TaskType
    priority: TaskPriority
    status: str = "PENDING"  # PENDING, DISPATCHED, COMPLETED, FAILED
    dispatched_at: datetime | None = None
    completed_at: datetime | None = None
    assigned_to: str | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


@dataclass
class ParentAgent:
    """
    親エージェント

    タスク配信と完了報告管理を行います。
    """

    session_id: str
    agent_id: str
    redis_config: RedisConfig = field(default_factory=RedisConfig)

    # 内部状態
    _redis: RedisClient | None = field(default=None, init=False, repr=False)
    _channels: ChannelConfig | None = field(default=None, init=False, repr=False)
    _logger: AgentLogger | None = field(default=None, init=False, repr=False)
    _tasks: dict[str, TaskInfo] = field(default_factory=dict, init=False, repr=False)
    _shutdown_event: threading.Event = field(
        default_factory=threading.Event, init=False, repr=False
    )
    _completion_thread: threading.Thread | None = field(
        default=None, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """初期化後の設定"""
        self._channels = ChannelConfig(session_id=self.session_id)
        self._logger = AgentLogger(
            agent_id=self.agent_id,
            agent_type="parent",
            level=LogLevel.INFO,
        )

    # ==================== 初期化・終了 ====================

    def initialize(self) -> None:
        """
        エージェントを初期化しRedisに接続
        """
        self._logger.info("初期化開始", session_id=self.session_id)

        # Redis接続
        self._redis = RedisClient(config=self.redis_config)
        self._redis.connect()

        # 接続確認
        if not self._redis.ping():
            raise ConnectionError("Redis接続に失敗しました")

        self._logger.info(
            "Redis接続完了",
            host=self.redis_config.host,
            port=self.redis_config.port,
        )

    def shutdown(self, reason: str = "shutdown_requested") -> None:
        """
        エージェントをシャットダウン

        Args:
            reason: シャットダウン理由
        """
        self._logger.info("シャットダウン開始", reason=reason)

        self._shutdown_event.set()

        # 完了報告受信スレッドの終了を待機
        if self._completion_thread and self._completion_thread.is_alive():
            self._completion_thread.join(timeout=5.0)

        # Redis接続を閉じる
        if self._redis:
            self._redis.close()
            self._redis = None

        self._logger.info("シャットダウン完了")

    # ==================== タスク管理 ====================

    def add_task(
        self,
        instruction: str,
        task_type: TaskType = TaskType.CUSTOM,
        priority: TaskPriority = TaskPriority.NORMAL,
        task_id: str | None = None,
    ) -> str:
        """
        タスクを追加

        Args:
            instruction: タスクの指示内容
            task_type: タスクの種類
            priority: 優先度
            task_id: タスクID（省略時は自動生成）

        Returns:
            タスクID
        """
        if task_id is None:
            task_id = f"task-{generate_uuid()[:8]}"

        task = TaskInfo(
            task_id=task_id,
            instruction=instruction,
            task_type=task_type,
            priority=priority,
        )
        self._tasks[task_id] = task

        self._logger.debug(
            "タスク追加",
            task_id=task_id,
            task_type=task_type.value,
            priority=priority.value,
        )

        return task_id

    def parse_and_add_tasks(self, task_description: str) -> list[str]:
        """
        作業指示を解析してタスクに分割

        Args:
            task_description: ユーザーからの作業指示

        Returns:
            追加されたタスクIDのリスト

        Note:
            シンプルな実装として、作業指示を1つのタスクとして追加します。
            より高度な実装では、NLPを使って複数のサブタスクに分割することも可能です。
        """
        # 基本実装: 1つの指示を1つのタスクとして追加
        # TODO: 将来的にはタスク分割ロジックを追加
        task_id = self.add_task(
            instruction=task_description,
            task_type=TaskType.CUSTOM,
            priority=TaskPriority.NORMAL,
        )
        return [task_id]

    def get_pending_tasks(self) -> list[TaskInfo]:
        """PENDINGステータスのタスクを取得"""
        return [t for t in self._tasks.values() if t.status == "PENDING"]

    def get_completed_tasks(self) -> list[TaskInfo]:
        """COMPLETED/FAILEDステータスのタスクを取得"""
        return [t for t in self._tasks.values() if t.status in ("COMPLETED", "FAILED")]

    def is_all_tasks_completed(self) -> bool:
        """全タスクが完了したかを確認"""
        if not self._tasks:
            return True
        return all(t.status in ("COMPLETED", "FAILED") for t in self._tasks.values())

    # ==================== タスク配信 ====================

    def dispatch_task(self, task_id: str, timeout_seconds: int = 300) -> bool:
        """
        タスクを子エージェントに配信

        Args:
            task_id: 配信するタスクID
            timeout_seconds: タイムアウト秒数

        Returns:
            配信成功時はTrue
        """
        if task_id not in self._tasks:
            self._logger.error("タスクが見つかりません", task_id=task_id)
            return False

        task = self._tasks[task_id]

        if task.status != "PENDING":
            self._logger.warn(
                "タスクは既に配信済みです",
                task_id=task_id,
                status=task.status,
            )
            return False

        # タスク配信メッセージを作成
        message = create_task_dispatch(
            sender_id=self.agent_id,
            task_id=task.task_id,
            task_type=task.task_type,
            instruction=task.instruction,
            priority=task.priority,
            timeout_seconds=timeout_seconds,
        )

        # タスクキューに配信
        queue_name = self._channels.task_queue
        message_json = message.to_json()

        self._redis.rpush(queue_name, message_json)

        # タスクステータスを更新
        task.status = "DISPATCHED"
        task.dispatched_at = datetime.now(timezone.utc)

        self._logger.info(
            "タスク配信完了",
            task_id=task_id,
            queue=queue_name,
        )

        return True

    def dispatch_all_pending_tasks(self, timeout_seconds: int = 300) -> int:
        """
        全てのPENDINGタスクを配信

        Args:
            timeout_seconds: 各タスクのタイムアウト秒数

        Returns:
            配信したタスク数
        """
        pending = self.get_pending_tasks()
        dispatched_count = 0

        for task in pending:
            if self.dispatch_task(task.task_id, timeout_seconds):
                dispatched_count += 1

        return dispatched_count

    # ==================== 完了報告受信 ====================

    def receive_completion(self, timeout: int = 5) -> Message | None:
        """
        完了報告を1件受信

        Args:
            timeout: タイムアウト秒数（0=無限待機）

        Returns:
            受信したメッセージ、またはタイムアウト時はNone
        """
        queue_name = self._channels.completion_queue

        result = self._redis.blpop(queue_name, timeout=timeout)

        if result is None:
            return None

        key, value = result
        message = Message.from_json(value) if isinstance(value, str) else Message.from_dict(value)

        return message

    def process_completion(self, message: Message) -> bool:
        """
        完了報告を処理

        Args:
            message: 完了報告メッセージ

        Returns:
            処理成功時はTrue
        """
        if message.message_type != MessageType.TASK_COMPLETION:
            self._logger.warn(
                "不明なメッセージタイプ",
                message_type=str(message.message_type),
            )
            return False

        payload = message.payload
        if isinstance(payload, dict):
            task_id = payload.get("task_id")
            agent_id = payload.get("agent_id")
            status = payload.get("status")
            output = payload.get("output", {})
            error = payload.get("error")
        else:
            task_id = payload.task_id
            agent_id = payload.agent_id
            status = payload.status.value if hasattr(payload.status, "value") else payload.status
            output = payload.output
            error = payload.error

        if task_id not in self._tasks:
            self._logger.warn("不明なタスクの完了報告", task_id=task_id)
            return False

        task = self._tasks[task_id]
        task.status = "COMPLETED" if status == "SUCCESS" else "FAILED"
        task.completed_at = datetime.now(timezone.utc)
        task.assigned_to = agent_id
        task.result = output.to_dict() if hasattr(output, "to_dict") else output
        task.error = error.to_dict() if hasattr(error, "to_dict") else error

        self._logger.info(
            "完了報告を処理",
            task_id=task_id,
            status=status,
            agent_id=agent_id,
        )

        return True

    def start_completion_listener(
        self,
        on_completion: Callable[[TaskInfo], None] | None = None,
        poll_interval: int = 5,
    ) -> None:
        """
        完了報告リスナーをバックグラウンドで開始

        Args:
            on_completion: タスク完了時のコールバック
            poll_interval: ポーリング間隔（秒）
        """

        def listener_loop():
            self._logger.info("完了報告リスナー開始")
            while not self._shutdown_event.is_set():
                try:
                    message = self.receive_completion(timeout=poll_interval)
                    if message:
                        self.process_completion(message)
                        if on_completion:
                            task_id = (
                                message.payload.get("task_id")
                                if isinstance(message.payload, dict)
                                else message.payload.task_id
                            )
                            if task_id in self._tasks:
                                on_completion(self._tasks[task_id])
                except Exception as e:
                    if not self._shutdown_event.is_set():
                        self._logger.error("完了報告受信エラー", error=str(e))

            self._logger.info("完了報告リスナー終了")

        self._completion_thread = threading.Thread(target=listener_loop, daemon=True)
        self._completion_thread.start()

    def wait_for_all_completions(
        self,
        timeout: int = 0,
        poll_interval: int = 5,
    ) -> bool:
        """
        全タスクの完了を待機

        Args:
            timeout: 全体のタイムアウト（秒、0=無限待機）
            poll_interval: ポーリング間隔（秒）

        Returns:
            全タスク完了時はTrue、タイムアウト時はFalse
        """
        start_time = datetime.now(timezone.utc)

        while not self.is_all_tasks_completed():
            if self._shutdown_event.is_set():
                return False

            # タイムアウトチェック
            if timeout > 0:
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                if elapsed >= timeout:
                    self._logger.warn("タスク完了待機がタイムアウト", elapsed=elapsed)
                    return False

            # 完了報告を受信
            message = self.receive_completion(timeout=poll_interval)
            if message:
                self.process_completion(message)

        return True

    # ==================== ユーザー通知 ====================

    def notify_user(
        self,
        event: NotificationEvent,
        message: str,
        task_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        """
        ユーザーに通知を送信

        Args:
            event: 通知イベント種別
            message: 通知メッセージ
            task_id: 関連するタスクID
            data: 追加データ
        """
        notification = create_user_notification(
            sender_id=self.agent_id,
            event=event,
            agent_id=self.agent_id,
            agent_type=AgentRole.PARENT,
            message=message,
            task_id=task_id,
            data=data,
        )

        channel_name = self._channels.notification_channel
        self._redis.publish(channel_name, notification.to_json())

        self._logger.info(
            "ユーザー通知送信",
            event=event.value,
            message=message[:50],
        )

    def notify_work_started(self) -> None:
        """作業開始を通知"""
        task_count = len(self._tasks)
        self.notify_user(
            event=NotificationEvent.WORK_STARTED,
            message=f"作業を開始します。タスク数: {task_count}",
            data={"task_count": task_count},
        )

    def notify_work_completed(self) -> None:
        """作業完了を通知"""
        completed = len([t for t in self._tasks.values() if t.status == "COMPLETED"])
        failed = len([t for t in self._tasks.values() if t.status == "FAILED"])

        self.notify_user(
            event=NotificationEvent.WORK_COMPLETED,
            message=f"作業が完了しました。成功: {completed}, 失敗: {failed}",
            data={
                "completed_count": completed,
                "failed_count": failed,
                "total_count": len(self._tasks),
            },
        )

    # ==================== 終了処理 ====================

    def send_shutdown_to_children(
        self,
        reason: str = "all_tasks_completed",
        graceful: bool = True,
        timeout_seconds: int = 30,
    ) -> None:
        """
        子エージェントに終了指示を送信

        Args:
            reason: 終了理由
            graceful: グレースフルシャットダウンかどうか
            timeout_seconds: 子エージェントの終了猶予時間
        """
        message = create_shutdown_command(
            sender_id=self.agent_id,
            reason=reason,
            graceful=graceful,
            timeout_seconds=timeout_seconds,
        )

        channel_name = self._channels.terminate_channel
        self._redis.publish(channel_name, message.to_json())

        self._logger.info(
            "終了指示を送信",
            channel=channel_name,
            reason=reason,
            graceful=graceful,
        )

    # ==================== メインループ ====================

    def run(
        self,
        task_description: str,
        task_timeout: int = 300,
        completion_timeout: int = 0,
    ) -> dict[str, Any]:
        """
        エージェントのメイン処理を実行

        Args:
            task_description: ユーザーからの作業指示
            task_timeout: 各タスクのタイムアウト（秒）
            completion_timeout: 全体の完了待機タイムアウト（秒、0=無限待機）

        Returns:
            実行結果のサマリー
        """
        try:
            # 1. 初期化
            self.initialize()

            # 2. タスクを解析・追加
            task_ids = self.parse_and_add_tasks(task_description)
            self._logger.info("タスク追加完了", task_count=len(task_ids))

            # 3. 作業開始通知
            self.notify_work_started()

            # 4. タスク配信
            dispatched = self.dispatch_all_pending_tasks(timeout_seconds=task_timeout)
            self._logger.info("タスク配信完了", dispatched_count=dispatched)

            # 5. 完了報告を待機
            success = self.wait_for_all_completions(
                timeout=completion_timeout,
                poll_interval=5,
            )

            # 6. 作業完了通知
            self.notify_work_completed()

            # 7. 子エージェントに終了指示
            self.send_shutdown_to_children()

            # 8. 結果サマリーを作成
            result = self._build_result_summary(success)

            return result

        except Exception as e:
            self._logger.error("実行エラー", error=str(e))
            raise

        finally:
            self.shutdown()

    def _build_result_summary(self, success: bool) -> dict[str, Any]:
        """結果サマリーを構築"""
        completed_tasks = [t for t in self._tasks.values() if t.status == "COMPLETED"]
        failed_tasks = [t for t in self._tasks.values() if t.status == "FAILED"]

        return {
            "success": success and len(failed_tasks) == 0,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "summary": {
                "total_tasks": len(self._tasks),
                "completed": len(completed_tasks),
                "failed": len(failed_tasks),
            },
            "tasks": [
                {
                    "task_id": t.task_id,
                    "status": t.status,
                    "instruction": t.instruction[:100],
                    "result": t.result,
                    "error": t.error,
                }
                for t in self._tasks.values()
            ],
        }


def main():
    """CLI エントリーポイント"""
    parser = argparse.ArgumentParser(
        description="親エージェント - タスク配信と完了報告管理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python parent_agent.py --session-id abc123 --agent-id parent-001 --task "コードレビューしてください"
  python parent_agent.py -s abc123 -a parent-001 -t "テストを実行してください" --timeout 600
        """,
    )

    parser.add_argument(
        "--session-id",
        "-s",
        required=True,
        help="セッションID（チャンネル名に使用）",
    )
    parser.add_argument(
        "--agent-id",
        "-a",
        required=True,
        help="エージェントID",
    )
    parser.add_argument(
        "--task",
        "-t",
        required=True,
        help="作業指示（タスク内容）",
    )
    parser.add_argument(
        "--redis-host",
        default="redis",
        help="Redisホスト名 (default: redis)",
    )
    parser.add_argument(
        "--redis-port",
        type=int,
        default=6379,
        help="Redisポート番号 (default: 6379)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="タスクタイムアウト秒数 (default: 300)",
    )
    parser.add_argument(
        "--completion-timeout",
        type=int,
        default=0,
        help="全体完了待機タイムアウト秒数 (default: 0=無限)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="結果をJSON形式で出力",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="デバッグログを有効化",
    )

    args = parser.parse_args()

    # Redis設定
    redis_config = RedisConfig(
        host=args.redis_host,
        port=args.redis_port,
    )

    # エージェントを作成
    agent = ParentAgent(
        session_id=args.session_id,
        agent_id=args.agent_id,
        redis_config=redis_config,
    )

    if args.debug:
        agent._logger.set_level(LogLevel.DEBUG)

    # シグナルハンドラを設定
    def signal_handler(signum, frame):
        agent._logger.info("シグナル受信", signal=signum)
        agent.shutdown("signal_received")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 実行
    result = agent.run(
        task_description=args.task,
        task_timeout=args.timeout,
        completion_timeout=args.completion_timeout,
    )

    # 結果出力
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'='*50}")
        print("実行結果")
        print(f"{'='*50}")
        print(f"成功: {result['success']}")
        print(f"セッションID: {result['session_id']}")
        print(f"エージェントID: {result['agent_id']}")
        print(f"\nサマリー:")
        print(f"  総タスク数: {result['summary']['total_tasks']}")
        print(f"  完了: {result['summary']['completed']}")
        print(f"  失敗: {result['summary']['failed']}")

        if result["tasks"]:
            print(f"\nタスク詳細:")
            for task in result["tasks"]:
                status_icon = "✓" if task["status"] == "COMPLETED" else "✗"
                print(f"  {status_icon} [{task['task_id']}] {task['instruction'][:50]}...")

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
