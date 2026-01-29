"""
orchestration.py の単体テスト

オーケストレーション初期化、設定取得、クリーンアップのテスト。
"""

import pytest

from app.orchestration import (
    OrchestrationConfig,
    initialize_orchestration,
    initialize_summoner_orchestration,
    get_config,
    cleanup_session,
    get_default_prefix,
    generate_session_id,
    generate_uuid_session_id,
)


class TestOrchestrationConfig:
    """OrchestrationConfig のテスト"""
    
    def test_to_dict(self):
        """辞書変換が正しく行われること"""
        config = OrchestrationConfig(
            session_id="test-session",
            prefix="test-prefix",
            max_children=5,
            created_at="2024-01-01T00:00:00+0900",
            parent_to_child_lists=["p2c:1", "p2c:2"],
            child_to_parent_lists=["c2p:1", "c2p:2"],
            mode="normal",
        )
        
        d = config.to_dict()
        
        assert d["session_id"] == "test-session"
        assert d["prefix"] == "test-prefix"
        assert d["max_children"] == 5
        assert d["mode"] == "normal"
        assert "p2c:1" in d["parent_to_child_lists"]
    
    def test_to_json_and_from_json(self):
        """JSON変換が正しく行われること"""
        config = OrchestrationConfig(
            session_id="test-session",
            prefix="test-prefix",
            max_children=3,
            created_at="2024-01-01T00:00:00+0900",
            mode="summoner",
        )
        
        json_str = config.to_json()
        parsed = OrchestrationConfig.from_json(json_str)
        
        assert parsed.session_id == config.session_id
        assert parsed.prefix == config.prefix
        assert parsed.mode == config.mode


class TestHelperFunctions:
    """ヘルパー関数のテスト"""
    
    def test_get_default_prefix(self, monkeypatch):
        """デフォルトプレフィックスが正しく生成されること"""
        monkeypatch.setenv("PROJECT_NAME", "myproject")
        monkeypatch.setenv("HOSTNAME", "worker01")
        
        prefix = get_default_prefix()
        
        assert prefix == "myproject-worker01"
    
    def test_get_default_prefix_long_hostname(self, monkeypatch):
        """長いホスト名が切り詰められること"""
        monkeypatch.setenv("PROJECT_NAME", "proj")
        monkeypatch.setenv("HOSTNAME", "very-long-hostname-that-exceeds-limit")
        
        prefix = get_default_prefix()
        
        # ホスト名は12文字に切り詰められる
        assert len(prefix.split("-", 1)[1]) <= 12
    
    def test_generate_session_id(self):
        """セッションIDが生成されること"""
        session_id = generate_session_id()
        
        assert "-" in session_id
        parts = session_id.split("-")
        assert len(parts) == 2
        assert parts[0].isdigit()  # タイムスタンプ
        assert parts[1].isdigit()  # PID
    
    def test_generate_uuid_session_id(self):
        """UUID形式のセッションIDが生成されること"""
        session_id = generate_uuid_session_id()
        
        # UUID形式: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        parts = session_id.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12


class TestInitializeOrchestration:
    """initialize_orchestration 関数のテスト"""
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_initialize(self, redis_host: str, redis_port: int, cleanup_lists: list[str]):
        """通常モードの初期化が正しく行われること"""
        config = initialize_orchestration(
            host=redis_host,
            port=redis_port,
            max_children=3,
            ttl=60,
        )
        
        # クリーンアップ対象を登録
        cleanup_lists.extend(config.parent_to_child_lists)
        cleanup_lists.extend(config.child_to_parent_lists)
        cleanup_lists.append(config.status_stream)
        cleanup_lists.append(config.result_stream)
        cleanup_lists.append(config.control_list)
        cleanup_lists.append(f"{config.prefix}:config")
        
        assert config.mode == "normal"
        assert config.max_children == 3
        assert len(config.parent_to_child_lists) == 3
        assert len(config.child_to_parent_lists) == 3
        assert ":p2c:" in config.parent_to_child_lists[0]
        assert ":c2p:" in config.child_to_parent_lists[0]
        
        # クリーンアップ
        cleanup_session(host=redis_host, port=redis_port, config=config)
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_initialize_with_sequence(self, redis_host: str, redis_port: int):
        """シーケンス番号指定での初期化が正しく行われること"""
        config = initialize_orchestration(
            host=redis_host,
            port=redis_port,
            prefix="test-seq",
            sequence=99,
            max_children=2,
            ttl=60,
        )
        
        try:
            assert "-099:" in config.parent_to_child_lists[0]
        finally:
            cleanup_session(host=redis_host, port=redis_port, config=config)


class TestInitializeSummonerOrchestration:
    """initialize_summoner_orchestration 関数のテスト"""
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_initialize_summoner(self, redis_host: str, redis_port: int):
        """Summonerモードの初期化が正しく行われること"""
        config = initialize_summoner_orchestration(
            host=redis_host,
            port=redis_port,
            max_children=3,
            ttl=60,
        )
        
        try:
            assert config.mode == "summoner"
            assert config.max_children == 3
            assert len(config.parent_to_child_lists) == 3
            # Summonerモードでは共有レポートキュー
            assert len(config.child_to_parent_lists) == 1
            assert "summoner:" in config.prefix
            assert ":tasks:" in config.parent_to_child_lists[0]
            assert ":reports" in config.child_to_parent_lists[0]
            assert config.monitor_channel != ""
        finally:
            cleanup_session(host=redis_host, port=redis_port, config=config)
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_initialize_summoner_with_session_id(self, redis_host: str, redis_port: int):
        """指定したセッションIDでの初期化が正しく行われること"""
        custom_id = "custom-test-id-12345"
        config = initialize_summoner_orchestration(
            host=redis_host,
            port=redis_port,
            session_id=custom_id,
            max_children=2,
            ttl=60,
        )
        
        try:
            assert config.session_id == custom_id
            assert custom_id in config.prefix
        finally:
            cleanup_session(host=redis_host, port=redis_port, config=config)


class TestGetConfig:
    """get_config 関数のテスト"""
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_get_config_by_prefix(self, orchestration_config: OrchestrationConfig, redis_host: str, redis_port: int):
        """プレフィックスで設定を取得できること"""
        retrieved = get_config(
            host=redis_host,
            port=redis_port,
            prefix=orchestration_config.prefix,
        )
        
        assert retrieved is not None
        assert retrieved.session_id == orchestration_config.session_id
        assert retrieved.mode == "normal"
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_get_config_by_session_id(self, summoner_config: OrchestrationConfig, redis_host: str, redis_port: int):
        """セッションIDで設定を取得できること"""
        retrieved = get_config(
            host=redis_host,
            port=redis_port,
            session_id=summoner_config.session_id,
        )
        
        assert retrieved is not None
        assert retrieved.session_id == summoner_config.session_id
        assert retrieved.mode == "summoner"
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_get_config_not_found(self, redis_host: str, redis_port: int):
        """存在しない設定はNoneを返すこと"""
        retrieved = get_config(
            host=redis_host,
            port=redis_port,
            session_id="nonexistent-session-id-12345",
        )
        
        assert retrieved is None
    
    def test_get_config_without_args(self):
        """prefix と session_id の両方がNoneの場合にValueErrorが発生すること"""
        with pytest.raises(ValueError, match="Either prefix or session_id"):
            get_config(host="localhost", port=6379)


class TestCleanupSession:
    """cleanup_session 関数のテスト"""
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_cleanup_with_config(self, redis_host: str, redis_port: int):
        """設定オブジェクトでクリーンアップできること"""
        config = initialize_orchestration(
            host=redis_host,
            port=redis_port,
            max_children=2,
            ttl=60,
        )
        
        result = cleanup_session(
            host=redis_host,
            port=redis_port,
            config=config,
        )
        
        assert result is True
        
        # 設定が削除されていることを確認
        retrieved = get_config(
            host=redis_host,
            port=redis_port,
            prefix=config.prefix,
        )
        assert retrieved is None
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_cleanup_summoner(self, redis_host: str, redis_port: int):
        """Summonerモードのクリーンアップができること"""
        config = initialize_summoner_orchestration(
            host=redis_host,
            port=redis_port,
            max_children=2,
            ttl=60,
        )
        
        result = cleanup_session(
            host=redis_host,
            port=redis_port,
            config=config,
        )
        
        assert result is True
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_cleanup_nonexistent(self, redis_host: str, redis_port: int):
        """存在しないセッションのクリーンアップはFalseを返すこと"""
        result = cleanup_session(
            host=redis_host,
            port=redis_port,
            session_id="nonexistent-session-12345",
        )
        
        assert result is False
