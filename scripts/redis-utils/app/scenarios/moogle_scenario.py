#!/usr/bin/env python3
"""
Moogleシナリオスクリプト

Moogleエージェント（親エージェント）の動作をシミュレートする。
- chocoboへのタスク配信
- レポートの収集
- シャットダウン指示の送信

Usage:
    python -m app.scenarios.moogle_scenario --session-id SESSION_ID [--host HOST] [--port PORT]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict, field
from typing import Optional

from app.orchestration import get_config, OrchestrationConfig
from app.sender import RedisSender, SendResult
from app.receiver import MessageReceiver, ReceivedMessage
from app.messages import (
    TaskMessage,
    ReportMessage,
    ShutdownMessage,
    StatusMessage,
    parse_message,
)


@dataclass
class MoogleResult:
    """Moogleシナリオの実行結果"""
    success: bool
    session_id: str = ""
    tasks_sent: int = 0
    reports_received: int = 0
    successful_reports: int = 0
    failed_reports: int = 0
    shutdown_sent: bool = False
    error: Optional[str] = None
    duration_ms: int = 0
    details: list[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class MoogleScenario:
    """
    Moogleシナリオクラス
    
    Moogleエージェント（親エージェント）の動作をシミュレートする。
    タスクの配信、レポートの収集、シャットダウンの送信を行う。
    
    Attributes:
        host: Redisホスト名
        port: Redisポート番号
        session_id: オーケストレーションセッションID
        config: オーケストレーション設定
        sender: Redisメッセージ送信クライアント
        receiver: Redisメッセージ受信クライアント
    """
    
    def __init__(
        self,
        session_id: str,
        host: str = "redis",
        port: int = 6379,
    ):
        """
        Moogleシナリオを初期化
        
        Args:
            session_id: オーケストレーションセッションID
            host: Redisホスト名
            port: Redisポート番号
        """
        self.host = host
        self.port = port
        self.session_id = session_id
        self.config: Optional[OrchestrationConfig] = None
        self.sender: Optional[RedisSender] = None
        self.receiver: Optional[MessageReceiver] = None
    
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
            
            self.sender = RedisSender(host=self.host, port=self.port)
            self.receiver = MessageReceiver(host=self.host, port=self.port)
            
            return True
        
        except Exception:
            return False
    
    def send_task(
        self,
        child_id: int,
        prompt: str,
        context: Optional[dict] = None,
        priority: int = 3,
        timeout: Optional[int] = None,
    ) -> tuple[bool, str]:
        """
        chocoboにタスクを送信
        
        Args:
            child_id: 送信先の子エージェントID（1始まり）
            prompt: タスク指示内容
            context: 追加コンテキスト
            priority: 優先度
            timeout: タイムアウト秒数
        
        Returns:
            (成功フラグ, タスクID)のタプル
        """
        if self.config is None or self.sender is None:
            raise RuntimeError("Not connected. Call connect() first.")
        
        task = TaskMessage.create(
            prompt=prompt,
            session_id=self.session_id,
            child_id=child_id,
            context=context,
            priority=priority,
            timeout=timeout,
        )
        
        queue = self.config.parent_to_child_lists[child_id - 1]
        result = self.sender.send_task(queue, task)
        
        # モニターチャンネルにも通知
        if result.success and self.config.monitor_channel:
            self.sender.publish_to_monitor(
                self.config.monitor_channel,
                queue,
                task.to_json(),
            )
        
        return (result.success, task.task_id)
    
    def send_tasks_to_all(
        self,
        prompts: list[str],
        context: Optional[dict] = None,
    ) -> list[tuple[int, str, bool]]:
        """
        全chocoboにタスクを配信
        
        Args:
            prompts: 各chocoboに送るタスク指示のリスト（child_id順）
            context: 共通コンテキスト
        
        Returns:
            [(child_id, task_id, success), ...] のリスト
        """
        if self.config is None:
            raise RuntimeError("Not connected. Call connect() first.")
        
        results = []
        
        for i, prompt in enumerate(prompts):
            child_id = i + 1
            if child_id > self.config.max_children:
                break
            
            success, task_id = self.send_task(
                child_id=child_id,
                prompt=prompt,
                context=context,
            )
            results.append((child_id, task_id, success))
        
        return results
    
    def receive_report(self, timeout: int = 5) -> Optional[ReportMessage]:
        """
        レポートを1件受信
        
        Args:
            timeout: タイムアウト秒数
        
        Returns:
            ReportMessage（タイムアウト時はNone）
        """
        if self.config is None or self.receiver is None:
            raise RuntimeError("Not connected. Call connect() first.")
        
        report_queue = self.config.child_to_parent_lists[0]
        result = self.receiver.receive_and_parse(report_queue, timeout=timeout)
        
        if result is None:
            return None
        
        received, parsed = result
        if isinstance(parsed, ReportMessage):
            return parsed
        
        return None
    
    def receive_all_reports(
        self,
        expected_count: int,
        timeout: int = 30,
    ) -> list[ReportMessage]:
        """
        期待する数のレポートを受信
        
        Args:
            expected_count: 期待するレポート数
            timeout: 全体のタイムアウト秒数
        
        Returns:
            受信したReportMessageのリスト
        """
        if self.config is None or self.receiver is None:
            raise RuntimeError("Not connected. Call connect() first.")
        
        reports = []
        report_queue = self.config.child_to_parent_lists[0]
        start_time = time.time()
        
        while len(reports) < expected_count:
            remaining = timeout - (time.time() - start_time)
            if remaining <= 0:
                break
            
            per_timeout = min(5, int(remaining) + 1)
            result = self.receiver.receive_and_parse(report_queue, timeout=per_timeout)
            
            if result is not None:
                received, parsed = result
                if isinstance(parsed, ReportMessage):
                    reports.append(parsed)
        
        return reports
    
    def send_shutdown(
        self,
        reason: str = "normal",
        graceful: bool = True,
        target_child_id: Optional[int] = None,
    ) -> list[bool]:
        """
        シャットダウンメッセージを送信
        
        Args:
            reason: 終了理由
            graceful: グレースフル終了かどうか
            target_child_id: 特定の子エージェントのみに送信（Noneの場合は全員）
        
        Returns:
            各chocoboへの送信成功フラグのリスト
        """
        if self.config is None or self.sender is None:
            raise RuntimeError("Not connected. Call connect() first.")
        
        shutdown = ShutdownMessage.create(
            session_id=self.session_id,
            reason=reason,
            graceful=graceful,
            target_child_id=target_child_id,
        )
        
        results = []
        
        if target_child_id is not None:
            # 特定のchocoboにのみ送信
            queue = self.config.parent_to_child_lists[target_child_id - 1]
            result = self.sender.send_any_message(queue, shutdown)
            results.append(result.success)
        else:
            # 全chocoboに送信
            for queue in self.config.parent_to_child_lists:
                result = self.sender.send_any_message(queue, shutdown)
                results.append(result.success)
        
        return results
    
    def run_full_scenario(
        self,
        task_prompts: Optional[list[str]] = None,
        wait_for_reports: bool = True,
        send_shutdown_after: bool = True,
        report_timeout: int = 30,
    ) -> MoogleResult:
        """
        完全なMoogleシナリオを実行
        
        1. セッションに接続
        2. タスクを配信
        3. レポートを収集
        4. シャットダウンを送信
        
        Args:
            task_prompts: 各chocoboに送るタスク（Noneの場合はデフォルト）
            wait_for_reports: レポートを待つかどうか
            send_shutdown_after: シナリオ後にシャットダウンを送信するか
            report_timeout: レポート待ちのタイムアウト秒数
        
        Returns:
            MoogleResult: シナリオ実行結果
        """
        start_time = time.time()
        result = MoogleResult(success=False, session_id=self.session_id)
        
        print("=== Moogle Scenario ===")
        print()
        
        # 1. 接続
        print("1. Connecting to session...")
        if not self.connect():
            result.error = f"Failed to connect to session: {self.session_id}"
            print(f"   ERROR: {result.error}")
            return result
        print(f"   Connected to session: {self.session_id}")
        print(f"   Max children: {self.config.max_children}")
        print()
        
        # 2. タスク配信
        if task_prompts is None:
            task_prompts = [
                f"Task for chocobo-{i+1}: Process data batch #{i+1}"
                for i in range(self.config.max_children)
            ]
        
        print(f"2. Sending tasks to {len(task_prompts)} chocobo(s)...")
        task_results = self.send_tasks_to_all(task_prompts)
        
        for child_id, task_id, success in task_results:
            status = "OK" if success else "FAILED"
            print(f"   Chocobo {child_id}: {task_id[:8]}... [{status}]")
            result.details.append({
                "action": "send_task",
                "child_id": child_id,
                "task_id": task_id,
                "success": success,
            })
            if success:
                result.tasks_sent += 1
        print()
        
        # 3. レポート収集
        if wait_for_reports and result.tasks_sent > 0:
            print(f"3. Waiting for reports (timeout: {report_timeout}s)...")
            reports = self.receive_all_reports(result.tasks_sent, timeout=report_timeout)
            
            for report in reports:
                result.reports_received += 1
                if report.status == "success":
                    result.successful_reports += 1
                    print(f"   Report from chocobo-{report.child_id}: SUCCESS")
                else:
                    result.failed_reports += 1
                    print(f"   Report from chocobo-{report.child_id}: {report.status.upper()}")
                
                result.details.append({
                    "action": "receive_report",
                    "child_id": report.child_id,
                    "task_id": report.task_id,
                    "status": report.status,
                })
            
            if result.reports_received < result.tasks_sent:
                missing = result.tasks_sent - result.reports_received
                print(f"   WARNING: {missing} report(s) not received (timeout)")
            print()
        
        # 4. シャットダウン
        if send_shutdown_after:
            print("4. Sending shutdown messages...")
            shutdown_results = self.send_shutdown(reason="scenario_complete")
            
            success_count = sum(1 for r in shutdown_results if r)
            print(f"   Shutdown sent to {success_count}/{len(shutdown_results)} chocobo(s)")
            result.shutdown_sent = success_count > 0
            print()
        
        result.success = True
        result.duration_ms = int((time.time() - start_time) * 1000)
        
        print("=== Moogle scenario completed ===")
        print(f"   Tasks sent: {result.tasks_sent}")
        print(f"   Reports received: {result.reports_received}")
        print(f"   Duration: {result.duration_ms}ms")
        
        return result


def main():
    """メインエントリポイント"""
    parser = argparse.ArgumentParser(
        description="Moogle scenario - Distribute tasks and collect reports"
    )
    parser.add_argument(
        "--session-id",
        required=True,
        help="Orchestration session ID (required)",
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
        "--tasks",
        nargs="+",
        default=None,
        help="Task prompts to send (default: auto-generate)",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for reports",
    )
    parser.add_argument(
        "--no-shutdown",
        action="store_true",
        help="Don't send shutdown after scenario",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Report timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON only",
    )
    
    args = parser.parse_args()
    
    scenario = MoogleScenario(
        session_id=args.session_id,
        host=args.host,
        port=args.port,
    )
    
    if args.json:
        # JSON出力モード
        if not scenario.connect():
            result = MoogleResult(
                success=False,
                session_id=args.session_id,
                error="Failed to connect to session",
            )
            print(result.to_json())
            sys.exit(1)
        
        result = MoogleResult(success=True, session_id=args.session_id)
        
        if args.tasks:
            task_results = scenario.send_tasks_to_all(args.tasks)
            for child_id, task_id, success in task_results:
                if success:
                    result.tasks_sent += 1
        
        if not args.no_shutdown:
            scenario.send_shutdown()
            result.shutdown_sent = True
        
        print(result.to_json())
        sys.exit(0)
    else:
        result = scenario.run_full_scenario(
            task_prompts=args.tasks,
            wait_for_reports=not args.no_wait,
            send_shutdown_after=not args.no_shutdown,
            report_timeout=args.timeout,
        )
        
        sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
