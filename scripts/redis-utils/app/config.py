"""
Redis接続設定モジュール

環境変数からの設定読み込みとデフォルト値の管理を行う。
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RedisConfig:
    """
    Redis接続設定
    
    Attributes:
        host: Redisホスト名
        port: Redisポート番号
        db: データベース番号
        password: 認証パスワード（オプション）
        socket_timeout: ソケットタイムアウト（秒）
        socket_connect_timeout: 接続タイムアウト（秒）
        decode_responses: レスポンスをデコードするか
        default_ttl: デフォルトのTTL（秒）
    """
    host: str = "redis"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    socket_timeout: float = 10.0
    socket_connect_timeout: float = 10.0
    decode_responses: bool = True
    default_ttl: int = 3600  # 1時間
    
    @classmethod
    def from_env(cls) -> "RedisConfig":
        """
        環境変数から設定を読み込む
        
        環境変数:
            REDIS_HOST: Redisホスト名 (default: redis)
            REDIS_PORT: Redisポート番号 (default: 6379)
            REDIS_DB: データベース番号 (default: 0)
            REDIS_PASSWORD: 認証パスワード (default: None)
            REDIS_TIMEOUT: ソケットタイムアウト秒 (default: 10)
            REDIS_TTL: デフォルトTTL秒 (default: 3600)
        
        Returns:
            RedisConfig: 設定インスタンス
        """
        return cls(
            host=os.environ.get("REDIS_HOST", "redis"),
            port=int(os.environ.get("REDIS_PORT", "6379")),
            db=int(os.environ.get("REDIS_DB", "0")),
            password=os.environ.get("REDIS_PASSWORD"),
            socket_timeout=float(os.environ.get("REDIS_TIMEOUT", "10")),
            socket_connect_timeout=float(os.environ.get("REDIS_TIMEOUT", "10")),
            default_ttl=int(os.environ.get("REDIS_TTL", "3600")),
        )


@dataclass
class OrchestrationConfig:
    """
    オーケストレーション設定
    
    Attributes:
        session_id: セッション識別子
        prefix: キー名プレフィックス
        max_children: 最大子エージェント数
        created_at: 作成日時（ISO 8601形式）
        parent_to_child_lists: 親→子タスクキュー名リスト
        child_to_parent_lists: 子→親レポートキュー名リスト
        status_stream: 状態管理ストリーム名
        result_stream: 結果収集ストリーム名
        control_list: 制御用リスト名
        monitor_channel: モニタリング用Pub/Subチャンネル名
        mode: モード（"normal" or "summoner"）
    """
    session_id: str
    prefix: str
    max_children: int
    created_at: str
    parent_to_child_lists: list[str] = field(default_factory=list)
    child_to_parent_lists: list[str] = field(default_factory=list)
    status_stream: str = ""
    result_stream: str = ""
    control_list: str = ""
    monitor_channel: str = ""
    mode: str = "normal"
    
    def get_task_queue(self, child_id: int) -> str:
        """
        指定した子エージェント用のタスクキュー名を取得
        
        Args:
            child_id: 子エージェントID（1始まり）
        
        Returns:
            タスクキュー名
        
        Raises:
            IndexError: child_idが範囲外の場合
        """
        if child_id < 1 or child_id > len(self.parent_to_child_lists):
            raise IndexError(f"child_id must be 1-{len(self.parent_to_child_lists)}, got {child_id}")
        return self.parent_to_child_lists[child_id - 1]
    
    def get_report_queue(self, child_id: int = 1) -> str:
        """
        レポートキュー名を取得
        
        summonerモードでは共有キュー、normalモードでは子エージェント別キュー
        
        Args:
            child_id: 子エージェントID（1始まり、normalモードのみ使用）
        
        Returns:
            レポートキュー名
        """
        if self.mode == "summoner":
            return self.child_to_parent_lists[0]
        if child_id < 1 or child_id > len(self.child_to_parent_lists):
            raise IndexError(f"child_id must be 1-{len(self.child_to_parent_lists)}, got {child_id}")
        return self.child_to_parent_lists[child_id - 1]


# シングルトン的なデフォルト設定インスタンス
_default_config: Optional[RedisConfig] = None


def get_default_config() -> RedisConfig:
    """
    デフォルトのRedis設定を取得（環境変数から読み込み）
    
    初回呼び出し時に環境変数から設定を読み込み、以後はキャッシュを返す。
    
    Returns:
        RedisConfig: デフォルト設定
    """
    global _default_config
    if _default_config is None:
        _default_config = RedisConfig.from_env()
    return _default_config


def reset_default_config() -> None:
    """
    デフォルト設定をリセット（テスト用）
    """
    global _default_config
    _default_config = None
