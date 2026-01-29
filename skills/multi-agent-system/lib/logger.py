"""
ロギングモジュール

構造化ログ出力とエージェントID付きロギング機能を提供します。

使用例:
    >>> from lib.logger import AgentLogger, LogLevel
    >>> 
    >>> # エージェント用ロガーの作成
    >>> logger = AgentLogger("child-001", agent_type="child")
    >>> 
    >>> # ログ出力
    >>> logger.info("タスクを開始", task_id="task-001")
    >>> logger.error("エラーが発生", error_code="E001", details={"file": "test.py"})
    >>> 
    >>> # 構造化ログ（JSON形式）
    >>> logger.set_format("json")
    >>> logger.info("JSONフォーマットのログ", key="value")
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, IntEnum
from typing import Any, Callable, Optional, TextIO
import json
import sys
import threading


class LogLevel(IntEnum):
    """ログレベル"""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    @classmethod
    def from_string(cls, level_str: str) -> "LogLevel":
        """文字列からログレベルを取得"""
        level_str = level_str.upper()
        mapping = {
            "DEBUG": cls.DEBUG,
            "INFO": cls.INFO,
            "WARNING": cls.WARNING,
            "WARN": cls.WARNING,
            "ERROR": cls.ERROR,
            "CRITICAL": cls.CRITICAL,
            "FATAL": cls.CRITICAL
        }
        return mapping.get(level_str, cls.INFO)


class LogFormat(str, Enum):
    """ログフォーマット"""
    TEXT = "text"      # 人間が読みやすいテキスト形式
    JSON = "json"      # 構造化JSON形式
    COMPACT = "compact"  # コンパクトなテキスト形式


@dataclass
class LogEntry:
    """ログエントリ"""
    timestamp: str
    level: LogLevel
    agent_id: str
    agent_type: str
    message: str
    extra: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """辞書に変換"""
        result = {
            "timestamp": self.timestamp,
            "level": self.level.name,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "message": self.message
        }
        if self.extra:
            result["extra"] = self.extra
        return result
    
    def to_json(self) -> str:
        """JSON文字列に変換"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    def to_text(self) -> str:
        """テキスト形式に変換"""
        level_str = f"[{self.level.name:8}]"
        agent_str = f"[{self.agent_type}:{self.agent_id}]"
        
        extra_str = ""
        if self.extra:
            extra_parts = [f"{k}={v}" for k, v in self.extra.items()]
            extra_str = " | " + ", ".join(extra_parts)
        
        return f"{self.timestamp} {level_str} {agent_str} {self.message}{extra_str}"
    
    def to_compact(self) -> str:
        """コンパクト形式に変換"""
        # タイムスタンプを短縮
        time_short = self.timestamp[11:19] if len(self.timestamp) > 19 else self.timestamp
        level_char = self.level.name[0]  # D, I, W, E, C
        
        extra_str = ""
        if self.extra:
            extra_parts = [f"{k}={v}" for k, v in self.extra.items()]
            extra_str = " " + " ".join(extra_parts)
        
        return f"{time_short} {level_char} [{self.agent_id}] {self.message}{extra_str}"


class AgentLogger:
    """
    エージェント用ロガー
    
    エージェントID付きの構造化ログ出力を提供します。
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str = "unknown",
        level: LogLevel = LogLevel.INFO,
        format: LogFormat = LogFormat.TEXT,
        output: Optional[TextIO] = None,
        include_timestamp: bool = True
    ):
        """
        ロガーを初期化
        
        Args:
            agent_id: エージェントID
            agent_type: エージェントタイプ（god, parent, child）
            level: 出力するログレベルの最小値
            format: ログフォーマット
            output: 出力先（デフォルトはstderr）
            include_timestamp: タイムスタンプを含めるか
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.level = level
        self.format = format
        self.output = output or sys.stderr
        self.include_timestamp = include_timestamp
        self._lock = threading.Lock()
        self._handlers: list[Callable[[LogEntry], None]] = []

    def set_level(self, level: LogLevel) -> None:
        """ログレベルを設定"""
        self.level = level

    def set_format(self, format: LogFormat) -> None:
        """ログフォーマットを設定"""
        if isinstance(format, str):
            format = LogFormat(format)
        self.format = format

    def add_handler(self, handler: Callable[[LogEntry], None]) -> None:
        """カスタムハンドラを追加"""
        self._handlers.append(handler)

    def remove_handler(self, handler: Callable[[LogEntry], None]) -> None:
        """カスタムハンドラを削除"""
        if handler in self._handlers:
            self._handlers.remove(handler)

    def _create_entry(
        self,
        level: LogLevel,
        message: str,
        **kwargs: Any
    ) -> LogEntry:
        """ログエントリを作成"""
        timestamp = ""
        if self.include_timestamp:
            timestamp = datetime.now(timezone.utc).isoformat()
        
        return LogEntry(
            timestamp=timestamp,
            level=level,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            message=message,
            extra=kwargs
        )

    def _format_entry(self, entry: LogEntry) -> str:
        """ログエントリをフォーマット"""
        if self.format == LogFormat.JSON:
            return entry.to_json()
        elif self.format == LogFormat.COMPACT:
            return entry.to_compact()
        else:  # TEXT
            return entry.to_text()

    def _write(self, entry: LogEntry) -> None:
        """ログを出力"""
        if entry.level < self.level:
            return
        
        with self._lock:
            # 標準出力に書き込み
            formatted = self._format_entry(entry)
            self.output.write(formatted + "\n")
            self.output.flush()
            
            # カスタムハンドラを呼び出し
            for handler in self._handlers:
                try:
                    handler(entry)
                except Exception:
                    pass  # ハンドラのエラーは無視

    def log(self, level: LogLevel, message: str, **kwargs: Any) -> None:
        """
        指定レベルでログを出力
        
        Args:
            level: ログレベル
            message: メッセージ
            **kwargs: 追加のキーワード引数（構造化データ）
        """
        entry = self._create_entry(level, message, **kwargs)
        self._write(entry)

    def debug(self, message: str, **kwargs: Any) -> None:
        """DEBUGレベルでログを出力"""
        self.log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """INFOレベルでログを出力"""
        self.log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """WARNINGレベルでログを出力"""
        self.log(LogLevel.WARNING, message, **kwargs)

    def warn(self, message: str, **kwargs: Any) -> None:
        """WARNINGレベルでログを出力（エイリアス）"""
        self.warning(message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """ERRORレベルでログを出力"""
        self.log(LogLevel.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """CRITICALレベルでログを出力"""
        self.log(LogLevel.CRITICAL, message, **kwargs)

    def fatal(self, message: str, **kwargs: Any) -> None:
        """CRITICALレベルでログを出力（エイリアス）"""
        self.critical(message, **kwargs)

    # ==================== コンテキスト付きログ ====================

    def task_started(self, task_id: str, task_type: str = "", **kwargs: Any) -> None:
        """タスク開始ログ"""
        self.info(
            f"タスク開始: {task_id}",
            task_id=task_id,
            task_type=task_type,
            event="TASK_STARTED",
            **kwargs
        )

    def task_completed(
        self,
        task_id: str,
        status: str = "SUCCESS",
        duration_ms: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        """タスク完了ログ"""
        extra = {"task_id": task_id, "status": status, "event": "TASK_COMPLETED"}
        if duration_ms is not None:
            extra["duration_ms"] = duration_ms
        extra.update(kwargs)
        
        level = LogLevel.INFO if status == "SUCCESS" else LogLevel.WARNING
        self.log(level, f"タスク完了: {task_id} ({status})", **extra)

    def task_failed(
        self,
        task_id: str,
        error_message: str,
        error_code: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """タスク失敗ログ"""
        extra = {
            "task_id": task_id,
            "error_message": error_message,
            "event": "TASK_FAILED"
        }
        if error_code:
            extra["error_code"] = error_code
        extra.update(kwargs)
        
        self.error(f"タスク失敗: {task_id} - {error_message}", **extra)

    def message_sent(
        self,
        message_type: str,
        destination: str,
        message_id: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """メッセージ送信ログ"""
        self.debug(
            f"メッセージ送信: {message_type} -> {destination}",
            message_type=message_type,
            destination=destination,
            message_id=message_id,
            event="MESSAGE_SENT",
            **kwargs
        )

    def message_received(
        self,
        message_type: str,
        source: str,
        message_id: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """メッセージ受信ログ"""
        self.debug(
            f"メッセージ受信: {message_type} <- {source}",
            message_type=message_type,
            source=source,
            message_id=message_id,
            event="MESSAGE_RECEIVED",
            **kwargs
        )

    def agent_started(self, **kwargs: Any) -> None:
        """エージェント起動ログ"""
        self.info(
            f"エージェント起動: {self.agent_id}",
            event="AGENT_STARTED",
            **kwargs
        )

    def agent_stopped(self, reason: str = "normal", **kwargs: Any) -> None:
        """エージェント終了ログ"""
        self.info(
            f"エージェント終了: {self.agent_id} ({reason})",
            reason=reason,
            event="AGENT_STOPPED",
            **kwargs
        )

    # ==================== 子ロガー ====================

    def child(self, suffix: str) -> "AgentLogger":
        """
        子ロガーを作成
        
        Args:
            suffix: エージェントIDに追加するサフィックス
            
        Returns:
            新しいロガーインスタンス
        """
        return AgentLogger(
            agent_id=f"{self.agent_id}.{suffix}",
            agent_type=self.agent_type,
            level=self.level,
            format=self.format,
            output=self.output,
            include_timestamp=self.include_timestamp
        )


# ==================== グローバルロガー ====================

_global_logger: Optional[AgentLogger] = None
_global_lock = threading.Lock()


def get_logger() -> AgentLogger:
    """グローバルロガーを取得"""
    global _global_logger
    with _global_lock:
        if _global_logger is None:
            _global_logger = AgentLogger("default", "system")
        return _global_logger


def set_logger(logger: AgentLogger) -> None:
    """グローバルロガーを設定"""
    global _global_logger
    with _global_lock:
        _global_logger = logger


def configure_logging(
    agent_id: str,
    agent_type: str = "unknown",
    level: LogLevel = LogLevel.INFO,
    format: LogFormat = LogFormat.TEXT
) -> AgentLogger:
    """
    グローバルロガーを設定して返す
    
    Args:
        agent_id: エージェントID
        agent_type: エージェントタイプ
        level: ログレベル
        format: ログフォーマット
        
    Returns:
        設定されたロガー
    """
    logger = AgentLogger(
        agent_id=agent_id,
        agent_type=agent_type,
        level=level,
        format=format
    )
    set_logger(logger)
    return logger


# ==================== ファイル出力ハンドラ ====================

class FileHandler:
    """ファイル出力ハンドラ"""
    
    def __init__(self, filepath: str, format: LogFormat = LogFormat.JSON):
        """
        ファイルハンドラを初期化
        
        Args:
            filepath: 出力先ファイルパス
            format: ログフォーマット
        """
        self.filepath = filepath
        self.format = format
        self._lock = threading.Lock()
    
    def __call__(self, entry: LogEntry) -> None:
        """ログエントリを処理"""
        with self._lock:
            with open(self.filepath, "a", encoding="utf-8") as f:
                if self.format == LogFormat.JSON:
                    f.write(entry.to_json() + "\n")
                elif self.format == LogFormat.COMPACT:
                    f.write(entry.to_compact() + "\n")
                else:
                    f.write(entry.to_text() + "\n")


class RotatingFileHandler(FileHandler):
    """ローテーション機能付きファイルハンドラ"""
    
    def __init__(
        self,
        filepath: str,
        format: LogFormat = LogFormat.JSON,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        """
        ローテーションハンドラを初期化
        
        Args:
            filepath: 出力先ファイルパス
            format: ログフォーマット
            max_bytes: ファイルの最大サイズ（バイト）
            backup_count: 保持するバックアップファイル数
        """
        super().__init__(filepath, format)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self._current_size = 0
        
        # 既存ファイルのサイズを取得
        try:
            import os
            if os.path.exists(filepath):
                self._current_size = os.path.getsize(filepath)
        except:
            pass
    
    def __call__(self, entry: LogEntry) -> None:
        """ログエントリを処理（ローテーション付き）"""
        with self._lock:
            self._maybe_rotate()
            
            with open(self.filepath, "a", encoding="utf-8") as f:
                if self.format == LogFormat.JSON:
                    line = entry.to_json() + "\n"
                elif self.format == LogFormat.COMPACT:
                    line = entry.to_compact() + "\n"
                else:
                    line = entry.to_text() + "\n"
                
                f.write(line)
                self._current_size += len(line.encode("utf-8"))
    
    def _maybe_rotate(self) -> None:
        """必要に応じてログファイルをローテート"""
        import os
        
        if self._current_size < self.max_bytes:
            return
        
        # バックアップファイルを移動
        for i in range(self.backup_count - 1, 0, -1):
            src = f"{self.filepath}.{i}"
            dst = f"{self.filepath}.{i + 1}"
            if os.path.exists(src):
                if os.path.exists(dst):
                    os.remove(dst)
                os.rename(src, dst)
        
        # 現在のファイルを .1 に移動
        if os.path.exists(self.filepath):
            dst = f"{self.filepath}.1"
            if os.path.exists(dst):
                os.remove(dst)
            os.rename(self.filepath, dst)
        
        self._current_size = 0
