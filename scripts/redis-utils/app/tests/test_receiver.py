"""
receiver.py の単体テスト

MessageReceiver と受信関数のテスト。
"""

import json
import pytest
import time

from app.config import RedisConfig
from app.receiver import (
    ReceivedMessage,
    MessageReceiver,
    receive_message,
    receive_messages,
    receive_task,
    receive_report,
    receive_any_message,
    wait_for_shutdown,
)
from app.sender import RedisSender
from app.messages import (
    TaskMessage,
    ReportMessage,
    ShutdownMessage,
    StatusMessage,
)


class TestReceivedMessage:
    """ReceivedMessage のテスト"""
    
    def test_to_dict(self):
        """辞書変換が正しく行われること"""
        msg = ReceivedMessage(
            list_name="test-list",
            raw_data='{"key": "value"}',
            timestamp="2024-01-01T00:00:00+0900",
            index=1,
        )
        
        d = msg.to_dict()
        
        assert d["list"] == "test-list"
        assert d["message"] == '{"key": "value"}'
        assert d["timestamp"] == "2024-01-01T00:00:00+0900"
        assert d["index"] == 1
    
    def test_to_dict_with_parsed(self):
        """パース済みメッセージがある場合の辞書変換"""
        task = TaskMessage.create(
            prompt="test",
            session_id="s1",
            child_id=1,
        )
        msg = ReceivedMessage(
            list_name="test-list",
            raw_data=task.to_json(),
            timestamp="2024-01-01T00:00:00+0900",
            parsed=task,
        )
        
        d = msg.to_dict()
        
        assert d["parsed_type"] == "task"
    
    def test_to_json(self):
        """JSON変換が正しく行われること"""
        msg = ReceivedMessage(
            list_name="test-list",
            raw_data="test",
            timestamp="2024-01-01T00:00:00+0900",
        )
        
        json_str = msg.to_json()
        data = json.loads(json_str)
        
        assert data["list"] == "test-list"
    
    def test_as_json_data(self):
        """raw_data のJSONパースが正しく行われること"""
        msg = ReceivedMessage(
            list_name="test-list",
            raw_data='{"key": "value", "num": 123}',
            timestamp="2024-01-01T00:00:00+0900",
        )
        
        data = msg.as_json_data()
        
        assert data is not None
        assert data["key"] == "value"
        assert data["num"] == 123
    
    def test_as_json_data_invalid(self):
        """無効なJSONの場合にNoneを返すこと"""
        msg = ReceivedMessage(
            list_name="test-list",
            raw_data="not json",
            timestamp="2024-01-01T00:00:00+0900",
        )
        
        data = msg.as_json_data()
        
        assert data is None


class TestMessageReceiver:
    """MessageReceiver のテスト"""
    
    def test_init_with_config(self, redis_config: RedisConfig):
        """configでの初期化が正しく行われること"""
        receiver = MessageReceiver(config=redis_config)
        
        assert receiver.client.host == redis_config.host
        assert receiver.client.port == redis_config.port
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_ping(self, redis_host: str, redis_port: int):
        """ping が成功すること"""
        receiver = MessageReceiver(host=redis_host, port=redis_port)
        
        assert receiver.ping() is True
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_receive(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """単一メッセージの受信が正しく行われること"""
        sender = RedisSender(host=redis_host, port=redis_port)
        sender.send_message(cleanup_list, "test message")
        
        receiver = MessageReceiver(host=redis_host, port=redis_port)
        received = receiver.receive(cleanup_list, timeout=1)
        
        assert received is not None
        assert received.list_name == cleanup_list
        assert received.raw_data == "test message"
        assert received.index == 1
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_receive_timeout(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """タイムアウト時にNoneを返すこと"""
        receiver = MessageReceiver(host=redis_host, port=redis_port)
        empty_list = cleanup_list + "-empty"
        
        received = receiver.receive(empty_list, timeout=1)
        
        assert received is None
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_receive_many(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """複数メッセージの受信が正しく行われること"""
        sender = RedisSender(host=redis_host, port=redis_port)
        sender.send_messages(cleanup_list, ["msg1", "msg2", "msg3"])
        
        receiver = MessageReceiver(host=redis_host, port=redis_port)
        received = receiver.receive_many(cleanup_list, count=5, timeout=1)
        
        assert len(received) == 3
        assert received[0].raw_data == "msg1"
        assert received[1].raw_data == "msg2"
        assert received[2].raw_data == "msg3"
        assert received[0].index == 1
        assert received[1].index == 2
        assert received[2].index == 3
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_receive_iter(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """イテレータ受信が正しく行われること"""
        sender = RedisSender(host=redis_host, port=redis_port)
        sender.send_messages(cleanup_list, ["a", "b", "c"])
        
        receiver = MessageReceiver(host=redis_host, port=redis_port)
        messages = []
        
        for msg in receiver.receive_iter(cleanup_list, timeout=1):
            messages.append(msg.raw_data)
            if len(messages) >= 3:
                break
        
        assert messages == ["a", "b", "c"]
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_receive_and_parse(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """受信とパースが正しく行われること"""
        task = TaskMessage.create(
            prompt="test task",
            session_id="s1",
            child_id=1,
        )
        
        sender = RedisSender(host=redis_host, port=redis_port)
        sender.send_task(cleanup_list, task)
        
        receiver = MessageReceiver(host=redis_host, port=redis_port)
        result = receiver.receive_and_parse(cleanup_list, timeout=1)
        
        assert result is not None
        received, parsed = result
        assert parsed is not None
        assert isinstance(parsed, TaskMessage)
        assert parsed.prompt == "test task"
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_receive_and_parse_invalid(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """無効なJSONの場合にパース結果がNoneになること"""
        sender = RedisSender(host=redis_host, port=redis_port)
        sender.send_message(cleanup_list, "not json")
        
        receiver = MessageReceiver(host=redis_host, port=redis_port)
        result = receiver.receive_and_parse(cleanup_list, timeout=1)
        
        assert result is not None
        received, parsed = result
        assert received.raw_data == "not json"
        assert parsed is None


class TestModuleFunctions:
    """モジュールレベル関数のテスト"""
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_receive_message_function(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """receive_message 関数が正しく動作すること"""
        sender = RedisSender(host=redis_host, port=redis_port)
        sender.send_message(cleanup_list, "test")
        
        received = receive_message(
            cleanup_list,
            timeout=1,
            host=redis_host,
            port=redis_port,
        )
        
        assert received is not None
        assert received.raw_data == "test"
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_receive_messages_function(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """receive_messages 関数が正しく動作すること"""
        sender = RedisSender(host=redis_host, port=redis_port)
        sender.send_messages(cleanup_list, ["a", "b"])
        
        received = receive_messages(
            cleanup_list,
            count=5,
            timeout=1,
            host=redis_host,
            port=redis_port,
        )
        
        assert len(received) == 2
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_receive_task_function(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """receive_task 関数が正しく動作すること"""
        task = TaskMessage.create(
            prompt="task prompt",
            session_id="s1",
            child_id=1,
        )
        
        sender = RedisSender(host=redis_host, port=redis_port)
        sender.send_task(cleanup_list, task)
        
        received = receive_task(
            cleanup_list,
            timeout=1,
            host=redis_host,
            port=redis_port,
        )
        
        assert received is not None
        assert received.prompt == "task prompt"
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_receive_report_function(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """receive_report 関数が正しく動作すること"""
        report = ReportMessage.success(
            task_id="t1",
            session_id="s1",
            child_id=1,
            result="done",
        )
        
        sender = RedisSender(host=redis_host, port=redis_port)
        sender.send_report(cleanup_list, report)
        
        received = receive_report(
            cleanup_list,
            timeout=1,
            host=redis_host,
            port=redis_port,
        )
        
        assert received is not None
        assert received.status == "success"
        assert received.result == "done"
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_receive_any_message_function(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """receive_any_message 関数が正しく動作すること"""
        status = StatusMessage.create(
            session_id="s1",
            child_id=1,
            event="ready",
        )
        
        sender = RedisSender(host=redis_host, port=redis_port)
        sender.send_any_message(cleanup_list, status)
        
        result = receive_any_message(
            cleanup_list,
            timeout=1,
            host=redis_host,
            port=redis_port,
        )
        
        assert result is not None
        received, parsed = result
        assert isinstance(parsed, StatusMessage)
        assert parsed.event == "ready"
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_wait_for_shutdown_function(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """wait_for_shutdown 関数が正しく動作すること"""
        shutdown = ShutdownMessage.create(
            session_id="s1",
            reason="test",
        )
        
        sender = RedisSender(host=redis_host, port=redis_port)
        sender.send_any_message(cleanup_list, shutdown)
        
        received = wait_for_shutdown(
            cleanup_list,
            timeout=1,
            host=redis_host,
            port=redis_port,
        )
        
        assert received is not None
        assert received.reason == "test"
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_wait_for_shutdown_skips_other_messages(
        self,
        redis_host: str,
        redis_port: int,
        cleanup_list: str,
    ):
        """wait_for_shutdown が他のメッセージを無視すること"""
        task = TaskMessage.create(
            prompt="task",
            session_id="s1",
            child_id=1,
        )
        shutdown = ShutdownMessage.create(
            session_id="s1",
            reason="final",
        )
        
        sender = RedisSender(host=redis_host, port=redis_port)
        sender.send_task(cleanup_list, task)
        sender.send_any_message(cleanup_list, shutdown)
        
        received = wait_for_shutdown(
            cleanup_list,
            timeout=1,
            host=redis_host,
            port=redis_port,
        )
        
        assert received is not None
        assert received.reason == "final"
