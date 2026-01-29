"""
シナリオ統合テスト

summoner、moogle、chocoboエージェントの連携動作をテストする。

テストシナリオ:
1. Summonerモードでオーケストレーション初期化
2. moogle役: タスクメッセージをchocoboキューに送信
3. chocobo役: タスクを受信して処理、レポートを送信
4. moogle役: レポートを受信して確認
5. moogle役: シャットダウンメッセージを送信
6. chocobo役: シャットダウンを受信して終了
7. セッションクリーンアップ
"""

import json
import time
import threading
import pytest
from typing import Optional

from app.orchestration import (
    initialize_summoner_orchestration,
    cleanup_session,
    OrchestrationConfig,
)
from app.sender import RedisSender, send_message
from app.receiver import MessageReceiver, receive_message
from app.messages import (
    TaskMessage,
    ReportMessage,
    ShutdownMessage,
    StatusMessage,
    parse_message,
)
from app.scenarios.summoner_scenario import SummonerScenario
from app.scenarios.moogle_scenario import MoogleScenario
from app.scenarios.chocobo_scenario import ChocoboScenario


class TestBasicSendReceive:
    """基本的な送受信テスト"""
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_task_message_roundtrip(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """TaskMessageの送受信が正しく行われること"""
        sender = RedisSender(host=redis_host, port=redis_port)
        receiver = MessageReceiver(host=redis_host, port=redis_port)
        
        # タスク送信
        task = TaskMessage.create(
            prompt="Test task prompt",
            session_id="test-session",
            child_id=1,
            context={"key": "value"},
        )
        result = sender.send_task(cleanup_list, task)
        assert result.success is True
        
        # タスク受信
        received = receiver.receive_and_parse(cleanup_list, timeout=1)
        assert received is not None
        raw, parsed = received
        
        assert isinstance(parsed, TaskMessage)
        assert parsed.prompt == "Test task prompt"
        assert parsed.task_id == task.task_id
        assert parsed.context == {"key": "value"}
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_report_message_roundtrip(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """ReportMessageの送受信が正しく行われること"""
        sender = RedisSender(host=redis_host, port=redis_port)
        receiver = MessageReceiver(host=redis_host, port=redis_port)
        
        # レポート送信
        report = ReportMessage.success(
            task_id="test-task-123",
            session_id="test-session",
            child_id=1,
            result={"output": "completed"},
            duration_ms=1500,
        )
        result = sender.send_report(cleanup_list, report)
        assert result.success is True
        
        # レポート受信
        received = receiver.receive_and_parse(cleanup_list, timeout=1)
        assert received is not None
        raw, parsed = received
        
        assert isinstance(parsed, ReportMessage)
        assert parsed.task_id == "test-task-123"
        assert parsed.status == "success"
        assert parsed.result == {"output": "completed"}
        assert parsed.duration_ms == 1500
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_shutdown_message_roundtrip(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """ShutdownMessageの送受信が正しく行われること"""
        sender = RedisSender(host=redis_host, port=redis_port)
        receiver = MessageReceiver(host=redis_host, port=redis_port)
        
        # シャットダウン送信
        shutdown = ShutdownMessage.create(
            session_id="test-session",
            reason="test-shutdown",
            graceful=True,
        )
        result = sender.send_any_message(cleanup_list, shutdown)
        assert result.success is True
        
        # シャットダウン受信
        received = receiver.receive_and_parse(cleanup_list, timeout=1)
        assert received is not None
        raw, parsed = received
        
        assert isinstance(parsed, ShutdownMessage)
        assert parsed.reason == "test-shutdown"
        assert parsed.graceful is True


class TestSummonerScenario:
    """Summonerシナリオのテスト"""
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_initialize_and_cleanup(self, redis_host: str, redis_port: int):
        """初期化とクリーンアップが正しく行われること"""
        scenario = SummonerScenario(
            host=redis_host,
            port=redis_port,
            max_children=3,
            ttl=60,
        )
        
        # 初期化
        result = scenario.initialize()
        
        assert result.success is True
        assert result.session_id != ""
        assert scenario.config is not None
        assert scenario.config.mode == "summoner"
        
        # 検証
        assert scenario.verify_session() is True
        
        # moogle情報取得
        moogle_info = scenario.get_moogle_info()
        assert moogle_info["session_id"] == result.session_id
        assert len(moogle_info["task_queues"]) == 3
        
        # chocobo情報取得
        chocobo_info = scenario.get_chocobo_info(1)
        assert chocobo_info["child_id"] == 1
        assert "tasks:1" in chocobo_info["task_queue"]
        
        # クリーンアップ
        assert scenario.cleanup() is True
        assert scenario.verify_session() is False


class TestMoogleChocoboIntegration:
    """MoogleとChocoboの統合テスト"""
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_single_task_flow(self, redis_host: str, redis_port: int):
        """単一タスクの送信→処理→レポートフローが正しく動作すること"""
        # 1. Summoner初期化
        summoner = SummonerScenario(
            host=redis_host,
            port=redis_port,
            max_children=1,
            ttl=60,
        )
        init_result = summoner.initialize()
        assert init_result.success is True
        
        try:
            session_id = init_result.session_id
            
            # 2. Moogle接続
            moogle = MoogleScenario(
                session_id=session_id,
                host=redis_host,
                port=redis_port,
            )
            assert moogle.connect() is True
            
            # 3. タスク送信
            success, task_id = moogle.send_task(
                child_id=1,
                prompt="Process test data",
                context={"batch_id": 1},
            )
            assert success is True
            assert task_id != ""
            
            # 4. Chocobo接続・タスク受信
            chocobo = ChocoboScenario(
                session_id=session_id,
                child_id=1,
                host=redis_host,
                port=redis_port,
            )
            assert chocobo.connect() is True
            
            task = chocobo.receive_task(timeout=2)
            assert task is not None
            assert task.prompt == "Process test data"
            assert task.task_id == task_id
            
            # 5. レポート送信
            report_sent = chocobo.send_report(
                task_id=task.task_id,
                success=True,
                result="Task completed successfully",
                duration_ms=100,
            )
            assert report_sent is True
            
            # 6. Moogleでレポート受信
            report = moogle.receive_report(timeout=2)
            assert report is not None
            assert report.task_id == task_id
            assert report.status == "success"
            assert report.child_id == 1
        
        finally:
            summoner.cleanup()
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_multiple_tasks_flow(self, redis_host: str, redis_port: int):
        """複数タスクのフローが正しく動作すること"""
        # 1. Summoner初期化
        summoner = SummonerScenario(
            host=redis_host,
            port=redis_port,
            max_children=3,
            ttl=60,
        )
        init_result = summoner.initialize()
        assert init_result.success is True
        
        try:
            session_id = init_result.session_id
            
            # 2. Moogle接続・タスク送信
            moogle = MoogleScenario(
                session_id=session_id,
                host=redis_host,
                port=redis_port,
            )
            assert moogle.connect() is True
            
            task_results = moogle.send_tasks_to_all([
                "Task for chocobo-1",
                "Task for chocobo-2",
                "Task for chocobo-3",
            ])
            
            assert len(task_results) == 3
            for child_id, task_id, success in task_results:
                assert success is True
            
            # 3. 各Chocoboでタスク受信・処理・レポート送信
            for i in range(1, 4):
                chocobo = ChocoboScenario(
                    session_id=session_id,
                    child_id=i,
                    host=redis_host,
                    port=redis_port,
                )
                assert chocobo.connect() is True
                
                task = chocobo.receive_task(timeout=2)
                assert task is not None
                assert task.child_id == i
                
                chocobo.send_report(
                    task_id=task.task_id,
                    success=True,
                    result=f"Completed by chocobo-{i}",
                    duration_ms=50 * i,
                )
            
            # 4. Moogleでレポート収集
            reports = moogle.receive_all_reports(expected_count=3, timeout=5)
            assert len(reports) == 3
            
            child_ids = {r.child_id for r in reports}
            assert child_ids == {1, 2, 3}
        
        finally:
            summoner.cleanup()


class TestShutdownFlow:
    """シャットダウンフローのテスト"""
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_shutdown_single_chocobo(self, redis_host: str, redis_port: int):
        """単一chocoboへのシャットダウンが正しく動作すること"""
        # Summoner初期化
        summoner = SummonerScenario(
            host=redis_host,
            port=redis_port,
            max_children=1,
            ttl=60,
        )
        init_result = summoner.initialize()
        assert init_result.success is True
        
        try:
            session_id = init_result.session_id
            
            # Moogle接続・シャットダウン送信
            moogle = MoogleScenario(
                session_id=session_id,
                host=redis_host,
                port=redis_port,
            )
            assert moogle.connect() is True
            
            shutdown_results = moogle.send_shutdown(
                reason="test-shutdown",
                graceful=True,
            )
            assert shutdown_results[0] is True
            
            # Chocoboでシャットダウン受信
            chocobo = ChocoboScenario(
                session_id=session_id,
                child_id=1,
                host=redis_host,
                port=redis_port,
            )
            assert chocobo.connect() is True
            
            message = chocobo.receive_message(timeout=2)
            assert isinstance(message, ShutdownMessage)
            assert message.reason == "test-shutdown"
        
        finally:
            summoner.cleanup()


class TestFullScenario:
    """完全なシナリオテスト"""
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_full_orchestration_scenario(self, redis_host: str, redis_port: int):
        """
        完全なオーケストレーションシナリオ
        
        1. Summonerモードでオーケストレーション初期化
        2. moogle役: タスクメッセージをchocoboキューに送信
        3. chocobo役: タスクを受信して処理、レポートを送信
        4. moogle役: レポートを受信して確認
        5. moogle役: シャットダウンメッセージを送信
        6. chocobo役: シャットダウンを受信して終了
        7. セッションクリーンアップ
        """
        num_children = 2
        
        # ===== 1. Summoner初期化 =====
        print("\n=== Step 1: Summoner Initialization ===")
        summoner = SummonerScenario(
            host=redis_host,
            port=redis_port,
            max_children=num_children,
            ttl=120,
        )
        init_result = summoner.initialize()
        
        assert init_result.success is True
        session_id = init_result.session_id
        print(f"Session ID: {session_id}")
        
        try:
            # ===== 2. Moogleタスク送信 =====
            print("\n=== Step 2: Moogle Task Distribution ===")
            moogle = MoogleScenario(
                session_id=session_id,
                host=redis_host,
                port=redis_port,
            )
            assert moogle.connect() is True
            
            task_prompts = [
                "Process batch A",
                "Process batch B",
            ]
            task_results = moogle.send_tasks_to_all(task_prompts)
            
            task_ids = {}
            for child_id, task_id, success in task_results:
                assert success is True
                task_ids[child_id] = task_id
                print(f"Sent task to chocobo-{child_id}: {task_id[:8]}...")
            
            # ===== 3. Chocoboタスク処理 =====
            print("\n=== Step 3: Chocobo Task Processing ===")
            for child_id in range(1, num_children + 1):
                chocobo = ChocoboScenario(
                    session_id=session_id,
                    child_id=child_id,
                    host=redis_host,
                    port=redis_port,
                )
                assert chocobo.connect() is True
                
                # タスク受信
                task = chocobo.receive_task(timeout=2)
                assert task is not None
                assert task.task_id == task_ids[child_id]
                print(f"Chocobo-{child_id} received: {task.prompt}")
                
                # 処理（シミュレート）
                time.sleep(0.05)
                
                # レポート送信
                report_sent = chocobo.send_report(
                    task_id=task.task_id,
                    success=True,
                    result=f"Processed by chocobo-{child_id}",
                    duration_ms=50,
                )
                assert report_sent is True
                print(f"Chocobo-{child_id} sent report")
            
            # ===== 4. Moogleレポート収集 =====
            print("\n=== Step 4: Moogle Report Collection ===")
            reports = moogle.receive_all_reports(
                expected_count=num_children,
                timeout=10,
            )
            
            assert len(reports) == num_children
            
            for report in reports:
                assert report.status == "success"
                print(f"Received report from chocobo-{report.child_id}: {report.status}")
            
            # ===== 5. Moogleシャットダウン送信 =====
            print("\n=== Step 5: Moogle Shutdown ===")
            shutdown_results = moogle.send_shutdown(reason="scenario_complete")
            
            shutdown_success = sum(1 for r in shutdown_results if r)
            assert shutdown_success == num_children
            print(f"Shutdown sent to {shutdown_success} chocobo(s)")
            
            # ===== 6. Chocoboシャットダウン受信 =====
            print("\n=== Step 6: Chocobo Shutdown Reception ===")
            for child_id in range(1, num_children + 1):
                chocobo = ChocoboScenario(
                    session_id=session_id,
                    child_id=child_id,
                    host=redis_host,
                    port=redis_port,
                )
                assert chocobo.connect() is True
                
                message = chocobo.receive_message(timeout=2)
                assert isinstance(message, ShutdownMessage)
                print(f"Chocobo-{child_id} received shutdown: {message.reason}")
            
            print("\n=== Full scenario completed successfully ===")
        
        finally:
            # ===== 7. クリーンアップ =====
            print("\n=== Step 7: Cleanup ===")
            cleanup_success = summoner.cleanup()
            assert cleanup_success is True
            print("Session cleaned up")


class TestConcurrentWorkers:
    """並行ワーカーのテスト"""
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_concurrent_chocobo_workers(self, redis_host: str, redis_port: int):
        """並行して動作する複数のchocoboワーカーが正しく動作すること"""
        num_workers = 3
        tasks_per_worker = 2
        
        # Summoner初期化
        summoner = SummonerScenario(
            host=redis_host,
            port=redis_port,
            max_children=num_workers,
            ttl=120,
        )
        init_result = summoner.initialize()
        assert init_result.success is True
        
        try:
            session_id = init_result.session_id
            
            # ワーカー結果を格納するリスト
            worker_results = []
            
            def run_worker(child_id: int):
                """ワーカースレッド関数"""
                chocobo = ChocoboScenario(
                    session_id=session_id,
                    child_id=child_id,
                    host=redis_host,
                    port=redis_port,
                )
                result = chocobo.run_worker_loop(
                    max_tasks=tasks_per_worker,
                    timeout=2,
                )
                worker_results.append((child_id, result))
            
            # ワーカースレッド開始
            threads = []
            for i in range(1, num_workers + 1):
                t = threading.Thread(target=run_worker, args=(i,))
                t.start()
                threads.append(t)
            
            # 少し待ってからタスク送信
            time.sleep(0.5)
            
            # Moogleでタスク送信
            moogle = MoogleScenario(
                session_id=session_id,
                host=redis_host,
                port=redis_port,
            )
            assert moogle.connect() is True
            
            # 各ワーカーに複数タスクを送信
            total_tasks = 0
            for _ in range(tasks_per_worker):
                for child_id in range(1, num_workers + 1):
                    success, _ = moogle.send_task(
                        child_id=child_id,
                        prompt=f"Task for worker {child_id}",
                    )
                    if success:
                        total_tasks += 1
            
            # レポート収集
            reports = moogle.receive_all_reports(
                expected_count=total_tasks,
                timeout=15,
            )
            
            # シャットダウン送信
            moogle.send_shutdown(reason="test_complete")
            
            # ワーカー終了待ち
            for t in threads:
                t.join(timeout=10)
            
            # 結果検証
            assert len(reports) == total_tasks
            
            for child_id, result in worker_results:
                assert result.success is True
                assert result.tasks_completed >= 1
        
        finally:
            summoner.cleanup()
