"""
セッションスキャナー

Redisから summoner:* パターンでキーをスキャンし、
アクティブなセッションを一覧表示する。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import redis

from ...config import RedisConfig, get_default_config


@dataclass
class SessionInfo:
    """セッション情報"""
    session_id: str
    prefix: str
    max_children: int
    created_at: str
    mode: str
    monitor_channel: str
    task_queues: list[str]
    report_queue: str
    is_active: bool = True
    
    @property
    def created_datetime(self) -> Optional[datetime]:
        """作成日時をdatetimeオブジェクトとして取得"""
        try:
            return datetime.fromisoformat(self.created_at)
        except (ValueError, TypeError):
            return None


class SessionScanner:
    """セッションスキャナー"""
    
    def __init__(self, config: Optional[RedisConfig] = None):
        """
        初期化
        
        Args:
            config: Redis設定（Noneの場合はデフォルト設定を使用）
        """
        self.config = config or get_default_config()
        self._client: Optional[redis.Redis] = None
        self._previous_session_ids: set[str] = set()
        self._last_scan_sessions: list[SessionInfo] = []
    
    @property
    def client(self) -> redis.Redis:
        """Redisクライアントを取得（遅延初期化）"""
        if self._client is None:
            self._client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                decode_responses=True,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
            )
        return self._client
    
    def is_connected(self) -> bool:
        """Redis接続を確認"""
        try:
            return self.client.ping()
        except redis.ConnectionError:
            return False
        except Exception:
            return False
    
    def scan_sessions(self) -> list[SessionInfo]:
        """
        アクティブなsummonerセッションをスキャン
        
        Returns:
            セッション情報のリスト（作成日時の降順でソート）
        """
        sessions: list[SessionInfo] = []
        
        try:
            # summoner:*:config パターンでスキャン
            cursor = 0
            config_keys: list[str] = []
            
            while True:
                cursor, keys = self.client.scan(
                    cursor=cursor,
                    match="summoner:*:config",
                    count=100
                )
                config_keys.extend(keys)
                if cursor == 0:
                    break
            
            # 各設定キーから情報を取得
            for config_key in config_keys:
                session_info = self._get_session_info(config_key)
                if session_info:
                    sessions.append(session_info)
            
            # 作成日時の降順でソート
            sessions.sort(
                key=lambda s: s.created_at if s.created_at else "",
                reverse=True
            )
            
        except redis.ConnectionError as e:
            raise ConnectionError(f"Redis接続エラー: {e}")
        except Exception as e:
            raise RuntimeError(f"セッションスキャンエラー: {e}")
        
        return sessions
    
    def _get_session_info(self, config_key: str) -> Optional[SessionInfo]:
        """
        設定キーからセッション情報を取得
        
        Args:
            config_key: 設定キー（例: summoner:xxx:config）
        
        Returns:
            セッション情報（取得できない場合はNone）
        """
        try:
            import json
            
            config_json = self.client.get(config_key)
            if not config_json:
                return None
            
            config = json.loads(config_json)
            
            return SessionInfo(
                session_id=config.get("session_id", ""),
                prefix=config.get("prefix", ""),
                max_children=config.get("max_children", 0),
                created_at=config.get("created_at", ""),
                mode=config.get("mode", "unknown"),
                monitor_channel=config.get("monitor_channel", ""),
                task_queues=config.get("parent_to_child_lists", []),
                report_queue=(
                    config.get("child_to_parent_lists", [""])[0]
                    if config.get("child_to_parent_lists")
                    else ""
                ),
            )
        except (json.JSONDecodeError, TypeError, KeyError):
            return None
    
    def get_queue_lengths(self, session: SessionInfo) -> dict[str, int]:
        """
        セッションのキュー長を取得
        
        Args:
            session: セッション情報
        
        Returns:
            キュー名とその長さの辞書
        """
        queue_lengths: dict[str, int] = {}
        
        try:
            # タスクキュー
            for queue in session.task_queues:
                queue_lengths[queue] = self.client.llen(queue)
            
            # 報告キュー
            if session.report_queue:
                queue_lengths[session.report_queue] = self.client.llen(session.report_queue)
        
        except redis.ConnectionError:
            pass
        except Exception:
            pass
        
        return queue_lengths
    
    def detect_new_sessions(
        self, 
        previous_sessions: list[SessionInfo]
    ) -> list[SessionInfo]:
        """
        前回のスキャン結果と比較して新規セッションを検出
        
        Args:
            previous_sessions: 前回スキャンしたセッション一覧
        
        Returns:
            新しく追加されたセッションのリスト
        """
        previous_ids = {s.session_id for s in previous_sessions}
        current_sessions = self.scan_sessions()
        
        new_sessions = [
            s for s in current_sessions
            if s.session_id not in previous_ids
        ]
        
        return new_sessions
    
    def scan_and_detect_new(
        self
    ) -> tuple[list[SessionInfo], list[SessionInfo]]:
        """
        セッションをスキャンし、新規セッションを検出
        
        内部でキャッシュした前回のスキャン結果と比較して、
        新しく追加されたセッションを検出する。
        初回実行時は全セッションが新規として扱われる。
        
        Returns:
            (全セッション一覧, 新規セッション一覧) のタプル
        """
        all_sessions = self.scan_sessions()
        current_ids = {s.session_id for s in all_sessions}
        
        new_sessions = [
            s for s in all_sessions
            if s.session_id not in self._previous_session_ids
        ]
        
        # キャッシュを更新
        self._previous_session_ids = current_ids
        self._last_scan_sessions = all_sessions
        
        return all_sessions, new_sessions
    
    def get_cached_sessions(self) -> list[SessionInfo]:
        """
        最後にスキャンしたセッション一覧を取得
        
        Returns:
            キャッシュされたセッション一覧（未スキャンの場合は空リスト）
        """
        return self._last_scan_sessions.copy()
    
    def clear_cache(self) -> None:
        """キャッシュをクリア"""
        self._previous_session_ids.clear()
        self._last_scan_sessions.clear()
    
    def close(self) -> None:
        """クライアント接続を閉じる"""
        if self._client:
            self._client.close()
            self._client = None
