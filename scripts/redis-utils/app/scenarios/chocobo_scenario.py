#!/usr/bin/env python3
"""
Chocoboシナリオスクリプト

Chocoboエージェント（子エージェント）の動作をシミュレートする。
- タスクの受信待機
- タスクの処理（シミュレート）
- レポートの送信
- シャットダウンの処理

Usage:
    python -m app.scenarios.chocobo_scenario --session-id SESSION_ID --child-id N [--host HOST]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict, field
from typing import Optional, Callable

from app.orchestration import get_config, OrchestrationConfig
from app.sender import RedisSender
from app.receiver import MessageReceiver
from app.messages import (
    TaskMessage,
    ReportMessage,
    ShutdownMessage,
    StatusMessage,
    parse_message,
)


@dataclass
class ChocoboResult:
    """Chocoboシナリオの実行結果"""
    success: bool
    session_id: str = ""
    child_id: int = 0
    tasks_received: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    shutdown_received: bool = False
    error: Optional[str] = None
    duration_ms: int = 0
    details: list[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class ChocoboScenario:
    """
    Chocoboシナリオクラス
    
    Chocoboエージェント（子エージェント/ワーカー）の動作をシミュレートする。
    タスクの受信、処理、レポートの送信を行う。
    
    Attributes:
        host: Redisホスト名
        port: Redisポート番号
        session_id: オーケストレーションセッションID
        child_id: 子エージェントID（1始まり）
        config: オーケストレーション設定
        sender: Redisメッセージ送信クライアント
        receiver: Redisメッセージ受信クライアント
        task_handler: タスク処理関数
    """
    
    def __init__(
        self,
        session_id: str,
        child_id: int,
        host: str = "redis",
        port: int = 6379,
        task_handler: Optional[Callable[[TaskMessage], tuple[bool, str]]] = None,
    ):
        """
        Chocoboシナリオを初期化
        
        Args:
            session_id: オーケストレーションセッションID
            child_id: 子エージェントID（1始まり）
            host: Redisホスト名
            port: Redisポート番号
            task_handler: タスク処理関数（Noneの場合はデフォルトハンドラ）
        """
        self.host = host
        self.port = port
        self.session_id = session_id
        self.child_id = child_id
        self.config: Optional[OrchestrationConfig] = None
        self.sender: Optional[RedisSender] = None
        self.receiver: Optional[MessageReceiver] = None
        self.task_handler = task_handler or self._default_task_handler
        self._running = False
    
    def _default_task_handler(self, task: TaskMessage) -> tuple[bool, str]:
        """
        デフォルトのタスクハンドラ
        
        Args:
            task: 処理するタスク
        
        Returns:
            (成功フラグ, 結果メッセージ)のタプル
        """
        # シミュレート: 少し待機して成功を返す
        time.sleep(0.1)
        return (True, f"Processed: {task.prompt[:50]}")
    
    def connect(self) -> bool:
        """
        セッションに接続
        
        Returns:
            接続成功時True
        """
        try:
            self.config = get_config(
                host=self.host,
                port=self.port,
                session_id=self.session_id,
            )
            
            if self.config is None:
                return False
            
            if self.child_id < 1 or self.child_id > self.config.max_children:
                return False
            
            self.sender = RedisSender(host=self.host, port=self.port)
            self.receiver = MessageReceiver(host=self.host, port=self.port)
            
            return True
        
        except Exception:
            return False
    
    def get_task_queue(self) -> str:
        """タスクキュー名を取得"""
        if self.config is None:
            raise RuntimeError("Not connected. Call connect() first.")
        return self.config.parent_to_child_lists[self.child_id - 1]
    
    def get_report_queue(self) -> str:
        """レポートキュー名を取得"""
        if self.config is None:
            raise RuntimeError("Not connected. Call connect() first.")
        return self.config.child_to_parent_lists[0]
    
    def receive_task(self, timeout: int = 5) -> Optional[TaskMessage]:
        """
        タスクを1件受信
        
        Args:
            timeout: タイムアウト秒数
        
        Returns:
            TaskMessage（タイムアウト時はNone）
        """
        if self.receiver is None:
            raise RuntimeError("Not connected. Call connect() first.")
        
        result = self.receiver.receive_and_parse(
            self.get_task_queue(),
            timeout=timeout,
        )
        
        if result is None:
            return None
        
        received, parsed = result
        if isinstance(parsed, TaskMessage):
            return parsed
        elif isinstance(parsed, ShutdownMessage):
            # シャットダウンメッセージを受信
            return None
        
        return None
    
    def receive_message(self, timeout: int = 5):
        """
        任意のメッセージを1件受信（タスクまたはシャットダウン）
        
        Args:
            timeout: タイムアウト秒数
        
        Returns:
            TaskMessage, ShutdownMessage, またはNone
        """
        if self.receiver is None:
            raise RuntimeError("Not connected. Call connect() first.")
        
        result = self.receiver.receive_and_parse(
            self.get_task_queue(),
            timeout=timeout,
        )
        
        if result is None:
            return None
        
        received, parsed = result
        return parsed
    
    def send_report(
        self,
        task_id: str,
        success: bool,
        result: str,
        duration_ms: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> bool:
        """
        レポートを送信
        
        Args:
            task_id: タスクID
            success: 成功フラグ
            result: 結果（成功時）またはエラーメッセージ（失敗時）
            duration_ms: 処理時間（ミリ秒）
            metadata: 追加メタデータ
        
        Returns:
            送信成功時True
        """
        if self.sender is None:
            raise RuntimeError("Not connected. Call connect() first.")
        
        if success:
            report = ReportMessage.success(
                task_id=task_id,
                session_id=self.session_id,
                child_id=self.child_id,
                result=result,
                duration_ms=duration_ms,
                metadata=metadata,
            )
        else:
            report = ReportMessage.failure(
                task_id=task_id,
                session_id=self.session_id,
                child_id=self.child_id,
                error=result,
                duration_ms=duration_ms,
                metadata=metadata,
            )
        
        send_result = self.sender.send_report(self.get_report_queue(), report)
        
        # モニターチャンネルにも通知
        if send_result.success and self.config and self.config.monitor_channel:
            self.sender.publish_to_monitor(
                self.config.monitor_channel,
                self.get_report_queue(),
                report.to_json(),
            )
        
        return send_result.success
    
    def send_status(self, event: str, details: Optional[dict] = None) -> bool:
        """
        ステータスを送信
        
        Args:
            event: イベント種別（"started", "ready", "busy", "completed", "stopped"）
            details: 詳細情報
        
        Returns:
            送信成功時True
        """
        if self.sender is None or self.config is None:
            raise RuntimeError("Not connected. Call connect() first.")
        
        status = StatusMessage.create(
            session_id=self.session_id,
            child_id=self.child_id,
            event=event,
            details=details,
        )
        
        # ステータスはモニターチャンネルに送信
        if self.config.monitor_channel:
            self.sender.publish_to_monitor(
                self.config.monitor_channel,
                f"status:{self.child_id}",
                status.to_json(),
            )
        
        return True
    
    def process_task(self, task: TaskMessage) -> tuple[bool, str, int]:
        """
        タスクを処理
        
        Args:
            task: 処理するタスク
        
        Returns:
            (成功フラグ, 結果, 処理時間ms)のタプル
        """
        start_time = time.time()
        
        try:
            success, result = self.task_handler(task)
            duration_ms = int((time.time() - start_time) * 1000)
            return (success, result, duration_ms)
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return (False, str(e), duration_ms)
    
    def stop(self):
        """ワーカーループを停止"""
        self._running = False
    
    def run_worker_loop(
        self,
        max_tasks: Optional[int] = None,
        timeout: int = 5,
    ) -> ChocoboResult:
        """
        ワーカーループを実行
        
        タスクを受信し、処理し、レポートを送信するループを実行。
        シャットダウンメッセージを受信するか、max_tasksに達したら終了。
        
        Args:
            max_tasks: 処理するタスクの最大数（Noneの場合は無制限）
            timeout: 各受信のタイムアウト秒数
        
        Returns:
            ChocoboResult: 実行結果
        """
        start_time = time.time()
        result = ChocoboResult(
            success=False,
            session_id=self.session_id,
            child_id=self.child_id,
        )
        
        if not self.connect():
            result.error = f"Failed to connect to session: {self.session_id}"
            return result
        
        self._running = True
        self.send_status("started")
        
        while self._running:
            # タスク数チェック
            if max_tasks is not None and result.tasks_completed + result.tasks_failed >= max_tasks:
                break
            
            # メッセージ受信
            message = self.receive_message(timeout=timeout)
            
            if message is None:
                continue
            
            if isinstance(message, ShutdownMessage):
                result.shutdown_received = True
                result.details.append({
                    "action": "shutdown_received",
                    "reason": message.reason,
                })
                break
            
            if isinstance(message, TaskMessage):
                result.tasks_received += 1
                
                # タスク処理
                self.send_status("busy")
                success, task_result, duration_ms = self.process_task(message)
                
                # レポート送信
                self.send_report(
                    task_id=message.task_id,
                    success=success,
                    result=task_result,
                    duration_ms=duration_ms,
                )
                
                if success:
                    result.tasks_completed += 1
                else:
                    result.tasks_failed += 1
                
                result.details.append({
                    "action": "task_processed",
                    "task_id": message.task_id,
                    "success": success,
                    "duration_ms": duration_ms,
                })
                
                self.send_status("ready")
        
        self.send_status("stopped")
        self._running = False
        
        result.success = True
        result.duration_ms = int((time.time() - start_time) * 1000)
        
        return result
    
    def run_full_scenario(
        self,
        max_tasks: int = 10,
        timeout: int = 5,
    ) -> ChocoboResult:
        """
        完全なChocoboシナリオを実行
        
        Args:
            max_tasks: 処理するタスクの最大数
            timeout: 各受信のタイムアウト秒数
        
        Returns:
            ChocoboResult: シナリオ実行結果
        """
        print(f"=== Chocobo Scenario (ID: {self.child_id}) ===")
        print()
        
        # 1. 接続
        print("1. Connecting to session...")
        if not self.connect():
            print(f"   ERROR: Failed to connect to session: {self.session_id}")
            return ChocoboResult(
                success=False,
                session_id=self.session_id,
                child_id=self.child_id,
                error="Failed to connect",
            )
        print(f"   Connected to session: {self.session_id}")
        print(f"   Task queue: {self.get_task_queue()}")
        print(f"   Report queue: {self.get_report_queue()}")
        print()
        
        # 2. ワーカーループ実行
        print(f"2. Starting worker loop (max tasks: {max_tasks}, timeout: {timeout}s)...")
        print("   Waiting for tasks...")
        
        result = self.run_worker_loop(max_tasks=max_tasks, timeout=timeout)
        
        print()
        print("=== Chocobo scenario completed ===")
        print(f"   Tasks received: {result.tasks_received}")
        print(f"   Tasks completed: {result.tasks_completed}")
        print(f"   Tasks failed: {result.tasks_failed}")
        print(f"   Shutdown received: {result.shutdown_received}")
        print(f"   Duration: {result.duration_ms}ms")
        
        return result


def main():
    """メインエントリポイント"""
    parser = argparse.ArgumentParser(
        description="Chocobo scenario - Receive tasks and send reports"
    )
    parser.add_argument(
        "--session-id",
        required=True,
        help="Orchestration session ID (required)",
    )
    parser.add_argument(
        "--child-id",
        type=int,
        required=True,
        help="Child agent ID (1-based, required)",
    )
    parser.add_argument(
        "--host",
        default="redis",
        help="Redis host (default: redis)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=6379,
        help="Redis port (default: 6379)",
    )
    parser.add_argument(
        "--max-tasks",
        type=int,
        default=10,
        help="Maximum tasks to process (default: 10)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=5,
        help="Receive timeout in seconds (default: 5)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON only",
    )
    
    args = parser.parse_args()
    
    scenario = ChocoboScenario(
        session_id=args.session_id,
        child_id=args.child_id,
        host=args.host,
        port=args.port,
    )
    
    if args.json:
        result = scenario.run_worker_loop(
            max_tasks=args.max_tasks,
            timeout=args.timeout,
        )
        print(result.to_json())
        sys.exit(0 if result.success else 1)
    else:
        result = scenario.run_full_scenario(
            max_tasks=args.max_tasks,
            timeout=args.timeout,
        )
        sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
