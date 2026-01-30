"""
Error Logger Module for Redis Monitor

エラーログ機能を提供するモジュール。
ログファイルはローテーション機能付きで /tmp/redis-monitor-error.log に出力される。
"""

import logging
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


# ログファイルの設定
LOG_FILE_PATH = Path("/tmp/redis-monitor-error.log")
MAX_BYTES = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 3  # 3世代保持


class ErrorLogger:
    """エラーログを管理するクラス"""
    
    _instance: "ErrorLogger | None" = None
    _logger: logging.Logger | None = None
    
    def __new__(cls) -> "ErrorLogger":
        """シングルトンパターンでインスタンスを管理"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_logger()
        return cls._instance
    
    def _initialize_logger(self) -> None:
        """ロガーを初期化"""
        self._logger = logging.getLogger("redis_monitor_error")
        self._logger.setLevel(logging.ERROR)
        
        # 既存のハンドラをクリア（重複防止）
        self._logger.handlers.clear()
        
        # ローテーションハンドラを設定
        handler = RotatingFileHandler(
            LOG_FILE_PATH,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        
        # フォーマッタを設定
        formatter = logging.Formatter(
            "%(message)s"  # カスタムフォーマットを使用するため、メッセージのみ
        )
        handler.setFormatter(formatter)
        
        self._logger.addHandler(handler)
    
    def log_error(
        self,
        error: Exception,
        location: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        エラーをログファイルに記録する
        
        Args:
            error: 発生した例外
            location: エラーの発生場所（メソッド名など）
            context: 関連するコンテキスト情報（セッションIDなど）
        """
        if self._logger is None:
            return
        
        # タイムスタンプ（ISO 8601形式）
        timestamp = datetime.now().isoformat()
        
        # スタックトレースを取得
        stack_trace = traceback.format_exc()
        
        # ログメッセージを構築
        log_lines = [
            "=" * 80,
            f"Timestamp: {timestamp}",
            f"Location: {location}",
            f"Error Type: {type(error).__name__}",
            f"Error Message: {error}",
        ]
        
        # コンテキスト情報を追加
        if context:
            log_lines.append("Context:")
            for key, value in context.items():
                log_lines.append(f"  {key}: {value}")
        
        # スタックトレースを追加
        log_lines.append("Stack Trace:")
        log_lines.append(stack_trace)
        log_lines.append("")  # 空行で区切り
        
        # ログに出力
        log_message = "\n".join(log_lines)
        self._logger.error(log_message)
    
    @classmethod
    def get_instance(cls) -> "ErrorLogger":
        """シングルトンインスタンスを取得"""
        return cls()


# 便利な関数として公開
def log_error(
    error: Exception,
    location: str,
    context: dict[str, Any] | None = None,
) -> None:
    """
    エラーをログファイルに記録する（モジュールレベル関数）
    
    Args:
        error: 発生した例外
        location: エラーの発生場所（メソッド名など）
        context: 関連するコンテキスト情報（セッションIDなど）
    
    Example:
        try:
            # 何らかの処理
            pass
        except Exception as e:
            log_error(e, "MyClass._my_method", {"session_id": "abc123"})
    """
    ErrorLogger.get_instance().log_error(error, location, context)
