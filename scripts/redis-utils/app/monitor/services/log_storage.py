"""
ログストレージサービス

セッション毎のメッセージをJSONL形式でファイルに保存・読み込みする。
保存先: /tmp/redis-utils/monitor/logs/<セッションID>/messages.jsonl
"""

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


LOG_BASE_DIR = Path("/tmp/redis-utils/monitor/logs")


@dataclass
class LogEntry:
    """ログエントリ"""
    timestamp: str
    session_id: str
    msg_type: str
    sender: str
    content: str
    raw_data: Optional[dict[str, Any]] = None
    
    def to_dict(self) -> dict[str, Any]:
        """辞書に変換"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LogEntry":
        """辞書から生成"""
        return cls(
            timestamp=data.get("timestamp", ""),
            session_id=data.get("session_id", ""),
            msg_type=data.get("msg_type", "unknown"),
            sender=data.get("sender", "unknown"),
            content=data.get("content", ""),
            raw_data=data.get("raw_data"),
        )


class LogStorage:
    """ログストレージ
    
    セッション毎のメッセージをJSONL形式でファイルに保存・読み込みする。
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        初期化
        
        Args:
            base_dir: ログ保存先のベースディレクトリ（デフォルト: /tmp/redis-utils/monitor/logs）
        """
        self.base_dir = base_dir or LOG_BASE_DIR
    
    def _get_session_dir(self, session_id: str) -> Path:
        """セッション用のディレクトリパスを取得"""
        return self.base_dir / session_id
    
    def _get_log_file_path(self, session_id: str) -> Path:
        """ログファイルパスを取得"""
        return self._get_session_dir(session_id) / "messages.jsonl"
    
    def _ensure_session_dir(self, session_id: str) -> Path:
        """セッションディレクトリを作成（存在しない場合）"""
        session_dir = self._get_session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir
    
    def save_message(
        self,
        session_id: str,
        msg_type: str,
        sender: str,
        content: str,
        raw_data: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        メッセージをログファイルに保存
        
        Args:
            session_id: セッションID
            msg_type: メッセージタイプ（task/report/status等）
            sender: 送信者
            content: メッセージ内容
            raw_data: 生のメッセージデータ（オプション）
        
        Returns:
            保存成功時True
        """
        try:
            self._ensure_session_dir(session_id)
            log_file = self._get_log_file_path(session_id)
            
            entry = LogEntry(
                timestamp=datetime.now().isoformat(),
                session_id=session_id,
                msg_type=msg_type,
                sender=sender,
                content=content,
                raw_data=raw_data,
            )
            
            # JSONL形式で追記
            with open(log_file, "a", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, ensure_ascii=False)
                f.write("\n")
            
            return True
        
        except Exception:
            return False
    
    def load_messages(self, session_id: str) -> list[LogEntry]:
        """
        セッションのログを読み込み
        
        Args:
            session_id: セッションID
        
        Returns:
            ログエントリのリスト
        """
        log_file = self._get_log_file_path(session_id)
        
        if not log_file.exists():
            return []
        
        entries: list[LogEntry] = []
        
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entries.append(LogEntry.from_dict(data))
                    except json.JSONDecodeError:
                        continue
        except Exception:
            return []
        
        return entries
    
    def list_sessions(self) -> list[str]:
        """
        ログがあるセッションID一覧を取得
        
        Returns:
            セッションIDのリスト
        """
        if not self.base_dir.exists():
            return []
        
        sessions: list[str] = []
        
        try:
            for item in self.base_dir.iterdir():
                if item.is_dir():
                    log_file = item / "messages.jsonl"
                    if log_file.exists():
                        sessions.append(item.name)
        except Exception:
            return []
        
        return sorted(sessions)
    
    def get_session_message_count(self, session_id: str) -> int:
        """
        セッションのメッセージ数を取得
        
        Args:
            session_id: セッションID
        
        Returns:
            メッセージ数
        """
        log_file = self._get_log_file_path(session_id)
        
        if not log_file.exists():
            return 0
        
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                return sum(1 for line in f if line.strip())
        except Exception:
            return 0
    
    def clear_session_logs(self, session_id: str) -> bool:
        """
        セッションのログをクリア
        
        Args:
            session_id: セッションID
        
        Returns:
            成功時True
        """
        log_file = self._get_log_file_path(session_id)
        
        if not log_file.exists():
            return True
        
        try:
            log_file.unlink()
            return True
        except Exception:
            return False
