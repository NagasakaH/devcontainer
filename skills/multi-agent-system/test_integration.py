#!/usr/bin/env python3
"""
Redis マルチエージェントシステム統合テスト

以下のテストを実行:
1. Redis接続テスト
2. メッセージ生成・シリアライズテスト
3. キュー操作テスト（RPUSH/BLPOP）
4. Pub/Sub操作テスト
5. チャンネル設定テスト
6. ロガーテスト
7. エージェント初期化テスト

使用方法:
    python test_integration.py
    python test_integration.py --redis-host localhost --redis-port 6379 --verbose
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Callable


# 共通ライブラリのパスを追加
sys.path.insert(0, str(__file__).rsplit("/", 1)[0])

from lib import (
    # Redis Client
    RedisClient,
    RedisConfig,
    # Messages
    Message,
    MessageType,
    TaskType,
    TaskPriority,
    TaskStatus,
    NotificationEvent,
    AgentRole,
    TaskContent,
    TaskTimeout,
    TaskMetadata,
    TaskDispatchPayload,
    TaskCompletionPayload,
    UserNotificationPayload,
    ShutdownCommandPayload,
    StartupInfoPayload,
    ExecutionTime,
    TaskOutput,
    TaskError,
    ChannelsConfig,
    AgentConfig,
    # Factory functions
    create_startup_info,
    create_task_dispatch,
    create_task_completion,
    create_user_notification,
    create_shutdown_command,
    generate_uuid,
    generate_timestamp,
    PROTOCOL_VERSION,
    # Channel Config
    ChannelConfig,
    ChannelType,
    # Logger
    AgentLogger,
    LogLevel,
)


class TestResult:
    """テスト結果を保持するクラス"""
    
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error: str | None = None
        self.duration_ms: float = 0.0
    
    def __str__(self) -> str:
        status = "✓ PASS" if self.passed else "✗ FAIL"
        result = f"{status} {self.name} ({self.duration_ms:.1f}ms)"
        if self.error:
            result += f"\n       Error: {self.error}"
        return result


class IntegrationTest:
    """統合テストランナー"""
    
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        verbose: bool = False,
    ):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.verbose = verbose
        self.results: list[TestResult] = []
        self.test_prefix = f"test-{generate_uuid()[:8]}"
    
    def log(self, message: str) -> None:
        """詳細ログを出力"""
        if self.verbose:
            print(f"  [DEBUG] {message}")
    
    def run_test(self, name: str, test_func: Callable[[], None]) -> TestResult:
        """個別テストを実行"""
        result = TestResult(name)
        start_time = time.time()
        
        try:
            test_func()
            result.passed = True
        except AssertionError as e:
            result.error = str(e)
        except Exception as e:
            result.error = f"{type(e).__name__}: {e}"
            if self.verbose:
                traceback.print_exc()
        
        result.duration_ms = (time.time() - start_time) * 1000
        self.results.append(result)
        print(f"  {result}")
        return result
    
    def run_all(self) -> bool:
        """全テストを実行"""
        print("=" * 60)
        print("Redis マルチエージェントシステム統合テスト")
        print("=" * 60)
        print(f"Redis: {self.redis_host}:{self.redis_port}")
        print(f"Test prefix: {self.test_prefix}")
        print()
        
        # 1. Redis接続テスト
        print("[1/7] Redis接続テスト")
        self.run_test("Redis PING", self.test_redis_ping)
        self.run_test("Redis接続/切断", self.test_redis_connect_disconnect)
        print()
        
        # 2. メッセージ生成テスト
        print("[2/7] メッセージ生成テスト")
        self.run_test("タスク配信メッセージ生成", self.test_create_task_dispatch)
        self.run_test("完了報告メッセージ生成", self.test_create_task_completion)
        self.run_test("ユーザー通知メッセージ生成", self.test_create_user_notification)
        self.run_test("シャットダウンメッセージ生成", self.test_create_shutdown_command)
        self.run_test("起動情報メッセージ生成", self.test_create_startup_info)
        self.run_test("メッセージJSON変換", self.test_message_json_serialization)
        print()
        
        # 3. キュー操作テスト
        print("[3/7] キュー操作テスト (RPUSH/BLPOP)")
        self.run_test("RPUSH/BLPOP基本操作", self.test_queue_basic_operations)
        self.run_test("BLPOPタイムアウト", self.test_blpop_timeout)
        self.run_test("複数値RPUSH", self.test_rpush_multiple_values)
        print()
        
        # 4. Pub/Subテスト
        print("[4/7] Pub/Sub操作テスト")
        self.run_test("基本的なPublish/Subscribe", self.test_pubsub_basic)
        print()
        
        # 5. チャンネル設定テスト
        print("[5/7] チャンネル設定テスト")
        self.run_test("セッションID生成", self.test_session_id_generation)
        self.run_test("チャンネル名生成", self.test_channel_name_generation)
        self.run_test("親/子チャンネル設定", self.test_agent_channel_configs)
        print()
        
        # 6. ロガーテスト
        print("[6/7] ロガーテスト")
        self.run_test("AgentLogger基本操作", self.test_logger_basic)
        self.run_test("ロガーレベルフィルタ", self.test_logger_level_filter)
        print()
        
        # 7. エージェント初期化テスト
        print("[7/7] エージェント初期化テスト")
        self.run_test("ParentAgent初期化", self.test_parent_agent_init)
        self.run_test("ChildAgent初期化", self.test_child_agent_init)
        print()
        
        # サマリー出力
        return self.print_summary()
    
    def print_summary(self) -> bool:
        """テスト結果のサマリーを出力"""
        print("=" * 60)
        print("テスト結果サマリー")
        print("=" * 60)
        
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)
        
        print(f"合計: {total} テスト")
        print(f"成功: {passed}")
        print(f"失敗: {failed}")
        
        if failed > 0:
            print("\n失敗したテスト:")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.name}: {r.error}")
        
        print()
        
        if failed == 0:
            print("✓ 全てのテストが成功しました！")
            return True
        else:
            print("✗ 一部のテストが失敗しました")
            return False
    
    # ==================== テスト実装 ====================
    
    def test_redis_ping(self) -> None:
        """Redis PING テスト"""
        config = RedisConfig(host=self.redis_host, port=self.redis_port)
        client = RedisClient(config)
        client.connect()
        try:
            assert client.ping(), "PING failed"
            self.log("PING returned PONG")
        finally:
            client.close()
    
    def test_redis_connect_disconnect(self) -> None:
        """Redis接続/切断テスト"""
        config = RedisConfig(host=self.redis_host, port=self.redis_port)
        client = RedisClient(config)
        
        # 接続
        client.connect()
        assert client.ping(), "Connection failed"
        self.log("Connected successfully")
        
        # 切断
        client.close()
        self.log("Disconnected successfully")
        
        # 再接続
        client.connect()
        assert client.ping(), "Reconnection failed"
        client.close()
        self.log("Reconnected and disconnected")
    
    def test_create_task_dispatch(self) -> None:
        """タスク配信メッセージ生成テスト"""
        msg = create_task_dispatch(
            sender_id="parent-001",
            task_id="task-001",
            task_type=TaskType.CODE_REVIEW,
            instruction="コードをレビューしてください",
            priority=TaskPriority.HIGH,
            timeout_seconds=300,
            target_files=["src/main.py"],
            context={"branch": "main"},
            constraints=["日本語でコメント"],
        )
        
        assert msg.message_type == MessageType.TASK_DISPATCH
        assert msg.sender_id == "parent-001"
        assert msg.protocol_version == PROTOCOL_VERSION
        assert msg.payload.task_id == "task-001"
        assert msg.payload.task_type == TaskType.CODE_REVIEW
        self.log(f"Created task dispatch message: {msg.message_id}")
    
    def test_create_task_completion(self) -> None:
        """完了報告メッセージ生成テスト"""
        started = datetime(2025, 1, 29, 10, 0, 0, tzinfo=timezone.utc)
        completed = datetime(2025, 1, 29, 10, 5, 0, tzinfo=timezone.utc)
        
        msg = create_task_completion(
            sender_id="child-001",
            task_id="task-001",
            agent_id="child-001",
            status=TaskStatus.SUCCESS,
            started_at=started,
            completed_at=completed,
            summary="タスク完了",
            data={"files_reviewed": 5},
        )
        
        assert msg.message_type == MessageType.TASK_COMPLETION
        assert msg.payload.status == TaskStatus.SUCCESS
        assert msg.payload.execution_time.duration_ms == 300000  # 5分
        self.log(f"Created task completion message: {msg.message_id}")
    
    def test_create_user_notification(self) -> None:
        """ユーザー通知メッセージ生成テスト"""
        msg = create_user_notification(
            sender_id="child-001",
            event=NotificationEvent.TASK_STARTED,
            agent_id="child-001",
            agent_type=AgentRole.CHILD,
            message="タスクを開始しました",
            task_id="task-001",
        )
        
        assert msg.message_type == MessageType.USER_NOTIFICATION
        assert msg.payload.event == NotificationEvent.TASK_STARTED
        assert msg.payload.agent_type == AgentRole.CHILD
        self.log(f"Created user notification message: {msg.message_id}")
    
    def test_create_shutdown_command(self) -> None:
        """シャットダウンメッセージ生成テスト"""
        msg = create_shutdown_command(
            sender_id="parent-001",
            reason="all_tasks_completed",
            graceful=True,
            timeout_seconds=30,
        )
        
        assert msg.message_type == MessageType.SHUTDOWN_COMMAND
        assert msg.payload.graceful is True
        assert msg.payload.timeout_seconds == 30
        self.log(f"Created shutdown command message: {msg.message_id}")
    
    def test_create_startup_info(self) -> None:
        """起動情報メッセージ生成テスト"""
        channels = ChannelsConfig(
            listen=["mas:queue:task:session-001"],
            publish=["mas:queue:completion:session-001"],
        )
        config = AgentConfig(
            timeout_seconds=300,
            max_retries=3,
            working_directory="/workspaces/test",
        )
        
        msg = create_startup_info(
            sender_id="god-001",
            agent_id="child-001",
            role=AgentRole.CHILD,
            channels=channels,
            config=config,
        )
        
        assert msg.message_type == MessageType.STARTUP_INFO
        assert msg.payload.role == AgentRole.CHILD
        assert msg.payload.config.timeout_seconds == 300
        self.log(f"Created startup info message: {msg.message_id}")
    
    def test_message_json_serialization(self) -> None:
        """メッセージのJSON変換テスト"""
        original = create_task_dispatch(
            sender_id="parent-001",
            task_id="task-001",
            task_type=TaskType.CUSTOM,
            instruction="テスト指示",
        )
        
        # JSON変換
        json_str = original.to_json()
        assert isinstance(json_str, str)
        self.log(f"Serialized to JSON: {len(json_str)} bytes")
        
        # 復元
        restored = Message.from_json(json_str)
        assert restored.message_id == original.message_id
        assert restored.message_type == original.message_type
        assert restored.sender_id == original.sender_id
        self.log("Deserialized from JSON successfully")
    
    def test_queue_basic_operations(self) -> None:
        """キュー基本操作テスト"""
        queue_name = f"{self.test_prefix}:queue:test"
        
        config = RedisConfig(host=self.redis_host, port=self.redis_port)
        client = RedisClient(config)
        client.connect()
        
        try:
            # キューをクリア
            client.delete(queue_name)
            
            # RPUSH
            result = client.rpush(queue_name, '{"test": "value1"}')
            assert result == 1, f"Expected 1, got {result}"
            self.log("RPUSH succeeded")
            
            # BLPOP
            result = client.blpop(queue_name, timeout=5)
            assert result is not None, "BLPOP returned None"
            key, value = result
            assert key == queue_name
            assert value == '{"test": "value1"}'
            self.log("BLPOP succeeded")
            
            # キューが空になったことを確認
            length = client.llen(queue_name)
            assert length == 0, f"Queue should be empty, got length {length}"
            
        finally:
            client.delete(queue_name)
            client.close()
    
    def test_blpop_timeout(self) -> None:
        """BLPOPタイムアウトテスト"""
        queue_name = f"{self.test_prefix}:queue:timeout"
        
        config = RedisConfig(host=self.redis_host, port=self.redis_port)
        client = RedisClient(config)
        client.connect()
        
        try:
            # キューをクリア
            client.delete(queue_name)
            
            # タイムアウトで戻ることを確認
            start = time.time()
            result = client.blpop(queue_name, timeout=2)
            elapsed = time.time() - start
            
            assert result is None, "Expected None on timeout"
            assert elapsed >= 1.5, f"Timeout too short: {elapsed:.1f}s"
            assert elapsed < 5, f"Timeout too long: {elapsed:.1f}s"
            self.log(f"BLPOP timed out correctly after {elapsed:.1f}s")
            
        finally:
            client.delete(queue_name)
            client.close()
    
    def test_rpush_multiple_values(self) -> None:
        """複数値RPUSHテスト"""
        queue_name = f"{self.test_prefix}:queue:multi"
        
        config = RedisConfig(host=self.redis_host, port=self.redis_port)
        client = RedisClient(config)
        client.connect()
        
        try:
            # キューをクリア
            client.delete(queue_name)
            
            # 複数値をRPUSH
            result = client.rpush(queue_name, "value1", "value2", "value3")
            assert result == 3, f"Expected 3, got {result}"
            self.log("RPUSH multiple values succeeded")
            
            # 長さを確認
            length = client.llen(queue_name)
            assert length == 3, f"Expected length 3, got {length}"
            
            # 順番に取得
            for i in range(1, 4):
                result = client.blpop(queue_name, timeout=2)
                assert result is not None
                assert result[1] == f"value{i}"
            
        finally:
            client.delete(queue_name)
            client.close()
    
    def test_pubsub_basic(self) -> None:
        """Pub/Sub基本テスト"""
        channel_name = f"{self.test_prefix}:channel:test"
        received_messages: list[tuple[str, str]] = []
        
        config = RedisConfig(host=self.redis_host, port=self.redis_port)
        subscriber = RedisClient(config)
        publisher = RedisClient(config)
        subscriber.connect()
        publisher.connect()
        
        try:
            def callback(channel: str, message: str):
                received_messages.append((channel, message))
            
            # 購読開始
            subscriber.subscribe(channel_name, callback=callback)
            time.sleep(0.5)  # 購読が確立するのを待つ
            self.log("Subscribed to channel")
            
            # メッセージを発行
            count = publisher.publish(channel_name, "test message")
            self.log(f"Published message, {count} subscribers received")
            
            # メッセージ受信を待つ
            time.sleep(0.5)
            
            # 購読解除
            subscriber.unsubscribe(channel_name)
            
            assert len(received_messages) >= 1, "No messages received"
            assert received_messages[0][1] == "test message"
            self.log("Message received successfully via Pub/Sub")
            
        finally:
            subscriber.close()
            publisher.close()
    
    def test_session_id_generation(self) -> None:
        """セッションID生成テスト"""
        from lib.channel_config import generate_session_id, validate_session_id
        
        session_id = generate_session_id()
        self.log(f"Generated session ID: {session_id}")
        
        # フォーマット検証
        assert validate_session_id(session_id), f"Invalid session ID format: {session_id}"
        
        # 一意性確認
        ids = [generate_session_id() for _ in range(10)]
        assert len(set(ids)) == 10, "Session IDs are not unique"
        self.log("Session ID generation verified")
    
    def test_channel_name_generation(self) -> None:
        """チャンネル名生成テスト"""
        config = ChannelConfig.create_session()
        
        # 各チャンネル名を確認
        assert config.task_queue.startswith("mas:queue:task:")
        assert config.completion_queue.startswith("mas:queue:completion:")
        assert config.terminate_channel.startswith("mas:channel:terminate:")
        assert config.notification_channel.startswith("mas:channel:notify:")
        
        self.log(f"Task queue: {config.task_queue}")
        self.log(f"Completion queue: {config.completion_queue}")
    
    def test_agent_channel_configs(self) -> None:
        """エージェント別チャンネル設定テスト"""
        config = ChannelConfig.create_session()
        
        # 親エージェント用
        parent_channels = config.get_parent_channels()
        assert config.completion_queue in parent_channels["listen"]
        assert config.task_queue in parent_channels["publish"]
        self.log(f"Parent channels: {parent_channels}")
        
        # 子エージェント用
        child_channels = config.get_child_channels()
        assert config.task_queue in child_channels["listen"]
        assert config.completion_queue in child_channels["publish"]
        self.log(f"Child channels: {child_channels}")
    
    def test_logger_basic(self) -> None:
        """ロガー基本テスト"""
        output = io.StringIO()
        logger = AgentLogger(
            agent_id="test-001",
            agent_type="test",
            level=LogLevel.DEBUG,
            output=output,
        )
        
        logger.info("テストメッセージ", key="value")
        
        output_str = output.getvalue()
        assert "テストメッセージ" in output_str
        assert "test-001" in output_str
        self.log(f"Logger output: {output_str.strip()}")
    
    def test_logger_level_filter(self) -> None:
        """ロガーレベルフィルタテスト"""
        output = io.StringIO()
        logger = AgentLogger(
            agent_id="test-002",
            agent_type="test",
            level=LogLevel.WARNING,
            output=output,
        )
        
        logger.debug("DEBUG message")
        logger.info("INFO message")
        logger.warning("WARNING message")
        logger.error("ERROR message")
        
        output_str = output.getvalue()
        assert "DEBUG message" not in output_str
        assert "INFO message" not in output_str
        assert "WARNING message" in output_str
        assert "ERROR message" in output_str
        self.log("Level filtering works correctly")
    
    def test_parent_agent_init(self) -> None:
        """親エージェント初期化テスト"""
        from parent_agent import ParentAgent
        
        agent = ParentAgent(
            session_id="test-session",
            agent_id="parent-test",
            redis_config=RedisConfig(
                host=self.redis_host,
                port=self.redis_port,
            ),
        )
        
        assert agent.session_id == "test-session"
        assert agent.agent_id == "parent-test"
        assert agent._channels is not None
        assert agent._logger is not None
        self.log("ParentAgent initialized successfully")
    
    def test_child_agent_init(self) -> None:
        """子エージェント初期化テスト"""
        from child_agent import ChildAgent
        
        agent = ChildAgent(
            session_id="test-session",
            agent_id="child-1",
            redis_host=self.redis_host,
            redis_port=self.redis_port,
        )
        
        assert agent.session_id == "test-session"
        assert agent.agent_id == "child-1"
        assert agent.channels is not None
        assert agent.logger is not None
        self.log("ChildAgent initialized successfully")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(
        description="Redis マルチエージェントシステム統合テスト",
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
        "-v", "--verbose",
        action="store_true",
        help="詳細ログを出力",
    )
    return parser.parse_args()


def main() -> int:
    """メインエントリーポイント"""
    args = parse_args()
    
    test = IntegrationTest(
        redis_host=args.redis_host,
        redis_port=args.redis_port,
        verbose=args.verbose,
    )
    
    success = test.run_all()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
