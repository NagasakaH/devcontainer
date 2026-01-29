"""
sender.py の単体テスト

RedisSender と送信関数のテスト。
"""

import json
import pytest

from app.config import RedisConfig
from app.sender import (
    RedisSender,
    SendResult,
    create_publish_payload,
    send_message,
    send_messages,
    send_with_publish,
)
from app.messages import TaskMessage, ReportMessage, ShutdownMessage
from app.redis_client import RespRedisClient


class TestSendResult:
    """SendResult のテスト"""
    
    def test_success_result(self):
        """成功結果が正しく作成されること"""
        result = SendResult(
            success=True,
            list_length=5,
            message_count=2,
            published=True,
            subscribers=3,
        )
        
        assert result.success is True
        assert result.list_length == 5
        assert result.message_count == 2
        assert result.published is True
        assert result.subscribers == 3
        assert result.error is None
    
    def test_failure_result(self):
        """失敗結果が正しく作成されること"""
        result = SendResult(
            success=False,
            error="Connection refused",
        )
        
        assert result.success is False
        assert result.error == "Connection refused"
    
    def test_repr(self):
        """repr が正しくフォーマットされること"""
        result = SendResult(success=True, list_length=10, message_count=1)
        repr_str = repr(result)
        
        assert "success=True" in repr_str
        assert "list_length=10" in repr_str


class TestCreatePublishPayload:
    """create_publish_payload 関数のテスト"""
    
    def test_payload_format(self):
        """ペイロードが正しいフォーマットで作成されること"""
        payload = create_publish_payload("test-queue", '{"msg": "hello"}')
        
        data = json.loads(payload)
        
        assert data["queue"] == "test-queue"
        assert data["message"] == '{"msg": "hello"}'
        assert "timestamp" in data


class TestRedisSender:
    """RedisSender のテスト"""
    
    def test_init_with_config(self, redis_config: RedisConfig):
        """configでの初期化が正しく行われること"""
        sender = RedisSender(config=redis_config)
        
        assert sender.client.host == redis_config.host
        assert sender.client.port == redis_config.port
    
    def test_init_without_config(self):
        """個別パラメータでの初期化が正しく行われること"""
        sender = RedisSender(host="my-host", port=1234, timeout=5.0)
        
        assert sender.client.host == "my-host"
        assert sender.client.port == 1234
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_send_message(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """単一メッセージの送信が正しく行われること"""
        sender = RedisSender(host=redis_host, port=redis_port)
        
        result = sender.send_message(cleanup_list, "test message")
        
        assert result.success is True
        assert result.list_length == 1
        assert result.message_count == 1
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_send_messages(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """複数メッセージの送信が正しく行われること"""
        sender = RedisSender(host=redis_host, port=redis_port)
        
        result = sender.send_messages(cleanup_list, ["msg1", "msg2", "msg3"])
        
        assert result.success is True
        assert result.list_length == 3
        assert result.message_count == 3
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_send_messages_empty(
        self,
        redis_host: str,
        redis_port: int,
    ):
        """空のメッセージリストの送信が正しく行われること"""
        sender = RedisSender(host=redis_host, port=redis_port)
        
        result = sender.send_messages("any-list", [])
        
        assert result.success is True
        assert result.message_count == 0
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_send_task(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """TaskMessage の送信が正しく行われること"""
        sender = RedisSender(host=redis_host, port=redis_port)
        task = TaskMessage.create(
            prompt="Test task",
            session_id="test-session",
            child_id=1,
        )
        
        result = sender.send_task(cleanup_list, task)
        
        assert result.success is True
        assert result.message_count == 1
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_send_report(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """ReportMessage の送信が正しく行われること"""
        sender = RedisSender(host=redis_host, port=redis_port)
        report = ReportMessage.success(
            task_id="task-1",
            session_id="test-session",
            child_id=1,
            result="completed",
        )
        
        result = sender.send_report(cleanup_list, report)
        
        assert result.success is True
        assert result.message_count == 1
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_send_any_message(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """任意のBaseMessage派生オブジェクトの送信が正しく行われること"""
        sender = RedisSender(host=redis_host, port=redis_port)
        shutdown = ShutdownMessage.create(session_id="test-session")
        
        result = sender.send_any_message(cleanup_list, shutdown)
        
        assert result.success is True
        assert result.message_count == 1
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_send_with_publish(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """RPUSH + PUBLISH が正しく行われること"""
        sender = RedisSender(host=redis_host, port=redis_port)
        channel = f"{cleanup_list}:monitor"
        
        result = sender.send_with_publish(cleanup_list, "test message", channel)
        
        assert result.success is True
        assert result.published is True
    
    def test_send_message_connection_error(self):
        """接続エラー時に失敗結果が返ること"""
        sender = RedisSender(host="invalid-host", port=6379, timeout=1.0)
        
        result = sender.send_message("test-list", "message")
        
        assert result.success is False
        assert result.error is not None


class TestModuleFunctions:
    """モジュールレベル関数のテスト"""
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_send_message_function(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """send_message 関数が正しく動作すること"""
        result = send_message(
            cleanup_list,
            "test message",
            host=redis_host,
            port=redis_port,
        )
        
        assert result.success is True
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_send_messages_function(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """send_messages 関数が正しく動作すること"""
        result = send_messages(
            cleanup_list,
            ["m1", "m2"],
            host=redis_host,
            port=redis_port,
        )
        
        assert result.success is True
        assert result.message_count == 2
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_send_with_publish_function(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """send_with_publish 関数が正しく動作すること"""
        channel = f"{cleanup_list}:channel"
        
        result = send_with_publish(
            cleanup_list,
            "test",
            channel,
            host=redis_host,
            port=redis_port,
        )
        
        assert result.success is True
        assert result.published is True
