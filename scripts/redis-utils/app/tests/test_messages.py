"""
messages.py の単体テスト

TaskMessage, ReportMessage, ShutdownMessage, StatusMessage のテスト。
"""

import json
import pytest

from app.messages import (
    MessageType,
    BaseMessage,
    TaskMessage,
    ReportMessage,
    ShutdownMessage,
    StatusMessage,
    parse_message,
)


class TestTaskMessage:
    """TaskMessage のテスト"""
    
    def test_create(self):
        """ファクトリメソッドで正しく作成されること"""
        task = TaskMessage.create(
            prompt="テストタスク",
            session_id="session-123",
            child_id=1,
            context={"key": "value"},
            priority=2,
            timeout=300,
        )
        
        assert task.type == MessageType.TASK.value
        assert task.prompt == "テストタスク"
        assert task.session_id == "session-123"
        assert task.child_id == 1
        assert task.context == {"key": "value"}
        assert task.priority == 2
        assert task.timeout == 300
        assert task.task_id != ""  # 自動生成される
        assert task.timestamp != ""  # 自動生成される
        assert task.message_id != ""  # 自動生成される
    
    def test_to_json_and_from_json(self):
        """JSON変換が正しく行われること"""
        task = TaskMessage.create(
            prompt="テストタスク",
            session_id="session-123",
            child_id=1,
        )
        
        json_str = task.to_json()
        parsed = TaskMessage.from_json(json_str)
        
        assert parsed.prompt == task.prompt
        assert parsed.session_id == task.session_id
        assert parsed.child_id == task.child_id
        assert parsed.task_id == task.task_id
    
    def test_to_dict(self):
        """辞書変換が正しく行われること"""
        task = TaskMessage.create(
            prompt="テスト",
            session_id="s1",
            child_id=2,
        )
        
        d = task.to_dict()
        
        assert d["type"] == "task"
        assert d["prompt"] == "テスト"
        assert d["session_id"] == "s1"
        assert d["child_id"] == 2


class TestReportMessage:
    """ReportMessage のテスト"""
    
    def test_success(self):
        """成功レポートが正しく作成されること"""
        report = ReportMessage.success(
            task_id="task-123",
            session_id="session-123",
            child_id=1,
            result={"output": "completed"},
            duration_ms=1500,
        )
        
        assert report.type == MessageType.REPORT.value
        assert report.task_id == "task-123"
        assert report.status == "success"
        assert report.result == {"output": "completed"}
        assert report.duration_ms == 1500
        assert report.error is None
    
    def test_failure(self):
        """失敗レポートが正しく作成されること"""
        report = ReportMessage.failure(
            task_id="task-123",
            session_id="session-123",
            child_id=1,
            error="Something went wrong",
            duration_ms=500,
        )
        
        assert report.status == "failure"
        assert report.error == "Something went wrong"
        assert report.result is None
    
    def test_to_json_and_from_json(self):
        """JSON変換が正しく行われること"""
        report = ReportMessage.success(
            task_id="task-123",
            session_id="session-123",
            child_id=1,
            result="done",
        )
        
        json_str = report.to_json()
        parsed = ReportMessage.from_json(json_str)
        
        assert parsed.task_id == report.task_id
        assert parsed.status == report.status
        assert parsed.result == report.result


class TestShutdownMessage:
    """ShutdownMessage のテスト"""
    
    def test_create_default(self):
        """デフォルト値で正しく作成されること"""
        msg = ShutdownMessage.create(session_id="session-123")
        
        assert msg.type == MessageType.SHUTDOWN.value
        assert msg.session_id == "session-123"
        assert msg.reason == "normal"
        assert msg.graceful is True
        assert msg.target_child_id is None
    
    def test_create_with_options(self):
        """オプション付きで正しく作成されること"""
        msg = ShutdownMessage.create(
            session_id="session-123",
            reason="timeout",
            graceful=False,
            target_child_id=2,
        )
        
        assert msg.reason == "timeout"
        assert msg.graceful is False
        assert msg.target_child_id == 2
    
    def test_to_json_and_from_json(self):
        """JSON変換が正しく行われること"""
        msg = ShutdownMessage.create(
            session_id="session-123",
            reason="manual",
        )
        
        json_str = msg.to_json()
        parsed = ShutdownMessage.from_json(json_str)
        
        assert parsed.session_id == msg.session_id
        assert parsed.reason == msg.reason


class TestStatusMessage:
    """StatusMessage のテスト"""
    
    def test_create(self):
        """ファクトリメソッドで正しく作成されること"""
        msg = StatusMessage.create(
            session_id="session-123",
            child_id=1,
            event="started",
            details={"worker": "chocobo-1"},
        )
        
        assert msg.type == MessageType.STATUS.value
        assert msg.session_id == "session-123"
        assert msg.child_id == 1
        assert msg.event == "started"
        assert msg.details == {"worker": "chocobo-1"}
    
    def test_to_json_and_from_json(self):
        """JSON変換が正しく行われること"""
        msg = StatusMessage.create(
            session_id="session-123",
            child_id=2,
            event="completed",
        )
        
        json_str = msg.to_json()
        parsed = StatusMessage.from_json(json_str)
        
        assert parsed.child_id == msg.child_id
        assert parsed.event == msg.event


class TestParseMessage:
    """parse_message 関数のテスト"""
    
    def test_parse_task_message(self):
        """TaskMessage が正しくパースされること"""
        task = TaskMessage.create(
            prompt="test",
            session_id="s1",
            child_id=1,
        )
        json_str = task.to_json()
        
        parsed = parse_message(json_str)
        
        assert isinstance(parsed, TaskMessage)
        assert parsed.prompt == "test"
    
    def test_parse_report_message(self):
        """ReportMessage が正しくパースされること"""
        report = ReportMessage.success(
            task_id="t1",
            session_id="s1",
            child_id=1,
            result="ok",
        )
        json_str = report.to_json()
        
        parsed = parse_message(json_str)
        
        assert isinstance(parsed, ReportMessage)
        assert parsed.status == "success"
    
    def test_parse_shutdown_message(self):
        """ShutdownMessage が正しくパースされること"""
        msg = ShutdownMessage.create(session_id="s1")
        json_str = msg.to_json()
        
        parsed = parse_message(json_str)
        
        assert isinstance(parsed, ShutdownMessage)
    
    def test_parse_status_message(self):
        """StatusMessage が正しくパースされること"""
        msg = StatusMessage.create(
            session_id="s1",
            child_id=1,
            event="ready",
        )
        json_str = msg.to_json()
        
        parsed = parse_message(json_str)
        
        assert isinstance(parsed, StatusMessage)
        assert parsed.event == "ready"
    
    def test_parse_unknown_type(self):
        """不明なタイプでValueErrorが発生すること"""
        json_str = json.dumps({"type": "unknown"})
        
        with pytest.raises(ValueError, match="Unknown message type"):
            parse_message(json_str)
    
    def test_parse_invalid_json(self):
        """無効なJSONでエラーが発生すること"""
        with pytest.raises(json.JSONDecodeError):
            parse_message("not a json")
