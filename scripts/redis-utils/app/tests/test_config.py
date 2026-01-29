"""
config.py の単体テスト

RedisConfig と OrchestrationConfig のテスト。
"""

import os
import pytest

from app.config import (
    RedisConfig,
    OrchestrationConfig,
    get_default_config,
    reset_default_config,
)


class TestRedisConfig:
    """RedisConfig のテスト"""
    
    def test_default_values(self):
        """デフォルト値が正しく設定されること"""
        config = RedisConfig()
        assert config.host == "redis"
        assert config.port == 6379
        assert config.db == 0
        assert config.password is None
        assert config.socket_timeout == 10.0
        assert config.socket_connect_timeout == 10.0
        assert config.decode_responses is True
        assert config.default_ttl == 3600
    
    def test_custom_values(self):
        """カスタム値が正しく設定されること"""
        config = RedisConfig(
            host="localhost",
            port=6380,
            db=1,
            password="secret",
            socket_timeout=5.0,
        )
        assert config.host == "localhost"
        assert config.port == 6380
        assert config.db == 1
        assert config.password == "secret"
        assert config.socket_timeout == 5.0
    
    def test_from_env(self, monkeypatch):
        """環境変数から設定を読み込むこと"""
        monkeypatch.setenv("REDIS_HOST", "env-host")
        monkeypatch.setenv("REDIS_PORT", "6381")
        monkeypatch.setenv("REDIS_DB", "2")
        monkeypatch.setenv("REDIS_PASSWORD", "env-secret")
        monkeypatch.setenv("REDIS_TIMEOUT", "15")
        monkeypatch.setenv("REDIS_TTL", "7200")
        
        config = RedisConfig.from_env()
        
        assert config.host == "env-host"
        assert config.port == 6381
        assert config.db == 2
        assert config.password == "env-secret"
        assert config.socket_timeout == 15.0
        assert config.default_ttl == 7200
    
    def test_from_env_defaults(self, monkeypatch):
        """環境変数が設定されていない場合はデフォルト値を使用すること"""
        # 環境変数をクリア
        for key in ["REDIS_HOST", "REDIS_PORT", "REDIS_DB", "REDIS_PASSWORD", "REDIS_TIMEOUT", "REDIS_TTL"]:
            monkeypatch.delenv(key, raising=False)
        
        config = RedisConfig.from_env()
        
        assert config.host == "redis"
        assert config.port == 6379
        assert config.password is None


class TestOrchestrationConfig:
    """OrchestrationConfig のテスト"""
    
    def test_get_task_queue(self):
        """タスクキュー名を正しく取得できること"""
        config = OrchestrationConfig(
            session_id="test-session",
            prefix="test-prefix",
            max_children=3,
            created_at="2024-01-01T00:00:00+0900",
            parent_to_child_lists=["queue:1", "queue:2", "queue:3"],
            child_to_parent_lists=["report:1", "report:2", "report:3"],
        )
        
        assert config.get_task_queue(1) == "queue:1"
        assert config.get_task_queue(2) == "queue:2"
        assert config.get_task_queue(3) == "queue:3"
    
    def test_get_task_queue_invalid_id(self):
        """無効な child_id で IndexError が発生すること"""
        config = OrchestrationConfig(
            session_id="test-session",
            prefix="test-prefix",
            max_children=3,
            created_at="2024-01-01T00:00:00+0900",
            parent_to_child_lists=["queue:1", "queue:2", "queue:3"],
        )
        
        with pytest.raises(IndexError):
            config.get_task_queue(0)
        
        with pytest.raises(IndexError):
            config.get_task_queue(4)
    
    def test_get_report_queue_normal_mode(self):
        """通常モードでレポートキュー名を正しく取得できること"""
        config = OrchestrationConfig(
            session_id="test-session",
            prefix="test-prefix",
            max_children=3,
            created_at="2024-01-01T00:00:00+0900",
            child_to_parent_lists=["report:1", "report:2", "report:3"],
            mode="normal",
        )
        
        assert config.get_report_queue(1) == "report:1"
        assert config.get_report_queue(2) == "report:2"
    
    def test_get_report_queue_summoner_mode(self):
        """Summonerモードでは共有レポートキューを取得すること"""
        config = OrchestrationConfig(
            session_id="test-session",
            prefix="test-prefix",
            max_children=3,
            created_at="2024-01-01T00:00:00+0900",
            child_to_parent_lists=["shared-report"],
            mode="summoner",
        )
        
        # Summonerモードでは child_id に関係なく共有キューを返す
        assert config.get_report_queue(1) == "shared-report"
        assert config.get_report_queue(2) == "shared-report"


class TestGetDefaultConfig:
    """get_default_config 関数のテスト"""
    
    def setup_method(self):
        """各テストの前にデフォルト設定をリセット"""
        reset_default_config()
    
    def teardown_method(self):
        """各テストの後にデフォルト設定をリセット"""
        reset_default_config()
    
    def test_returns_cached_config(self, monkeypatch):
        """キャッシュされた設定を返すこと"""
        # 環境変数をクリア
        for key in ["REDIS_HOST", "REDIS_PORT"]:
            monkeypatch.delenv(key, raising=False)
        
        config1 = get_default_config()
        config2 = get_default_config()
        
        assert config1 is config2  # 同じインスタンスが返される
    
    def test_reset_clears_cache(self, monkeypatch):
        """reset_default_config でキャッシュがクリアされること"""
        # 環境変数をクリア
        for key in ["REDIS_HOST", "REDIS_PORT"]:
            monkeypatch.delenv(key, raising=False)
        
        config1 = get_default_config()
        reset_default_config()
        config2 = get_default_config()
        
        assert config1 is not config2  # 異なるインスタンスが返される
