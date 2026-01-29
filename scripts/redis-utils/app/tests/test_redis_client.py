"""
redis_client.py の単体テスト

RespRedisClient と RedisClient のテスト。
"""

import pytest

from app.config import RedisConfig
from app.redis_client import (
    RespRedisClient,
    RedisClient,
    RedisConnectionError,
    RedisCommandError,
    create_client,
)


class TestRespRedisClient:
    """RespRedisClient のテスト"""
    
    def test_init_with_config(self):
        """configからの初期化が正しく行われること"""
        config = RedisConfig(host="test-host", port=1234, socket_timeout=20.0)
        client = RespRedisClient(config=config)
        
        assert client.host == "test-host"
        assert client.port == 1234
        assert client.timeout == 20.0
    
    def test_init_without_config(self):
        """個別パラメータからの初期化が正しく行われること"""
        client = RespRedisClient(host="my-host", port=5678, timeout=15.0)
        
        assert client.host == "my-host"
        assert client.port == 5678
        assert client.timeout == 15.0
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_ping(self, resp_client: RespRedisClient):
        """ping が成功すること"""
        assert resp_client.ping() is True
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_set_and_get(self, resp_client: RespRedisClient, cleanup_list: str):
        """set/get が正しく動作すること"""
        key = cleanup_list
        resp_client.set(key, "test-value")
        
        value = resp_client.get(key)
        assert value == "test-value"
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_set_with_ttl(self, resp_client: RespRedisClient, cleanup_list: str):
        """TTL付きset が正しく動作すること"""
        key = cleanup_list
        result = resp_client.set(key, "test-value", ttl=60)
        
        assert result is True
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_get_nonexistent(self, resp_client: RespRedisClient):
        """存在しないキーのget がNoneを返すこと"""
        value = resp_client.get("nonexistent-key-12345")
        assert value is None
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_exists(self, resp_client: RespRedisClient, cleanup_list: str):
        """exists が正しく動作すること"""
        key = cleanup_list
        
        assert resp_client.exists(key) is False
        resp_client.set(key, "value")
        assert resp_client.exists(key) is True
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_delete(self, resp_client: RespRedisClient, cleanup_list: str):
        """delete が正しく動作すること"""
        key = cleanup_list
        resp_client.set(key, "value")
        
        deleted = resp_client.delete(key)
        assert deleted == 1
        assert resp_client.exists(key) is False
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_rpush_and_llen(self, resp_client: RespRedisClient, cleanup_list: str):
        """rpush と llen が正しく動作すること"""
        list_name = cleanup_list
        
        length1 = resp_client.rpush(list_name, "item1")
        length2 = resp_client.rpush(list_name, "item2", "item3")
        
        assert length1 == 1
        assert length2 == 3
        assert resp_client.llen(list_name) == 3
    
    def test_connection_error_invalid_host(self):
        """無効なホストへの接続でエラーが発生すること"""
        client = RespRedisClient(host="invalid-host-12345", port=6379, timeout=1.0)
        
        with pytest.raises(RedisConnectionError):
            client.ping()


class TestRedisClient:
    """RedisClient (redis-py) のテスト"""
    
    def test_init_with_config(self, redis_config: RedisConfig):
        """configからの初期化が正しく行われること"""
        client = RedisClient(config=redis_config)
        
        assert client.host == redis_config.host
        assert client.port == redis_config.port
        assert client.db == redis_config.db
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_ping(self, redis_client: RedisClient):
        """ping が成功すること"""
        assert redis_client.ping() is True
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_set_and_get(self, redis_client: RedisClient, cleanup_list: str):
        """set/get が正しく動作すること"""
        key = cleanup_list
        redis_client.set(key, "redis-py-value")
        
        value = redis_client.get(key)
        assert value == "redis-py-value"
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_rpush_and_llen(self, redis_client: RedisClient, cleanup_list: str):
        """rpush と llen が正しく動作すること"""
        list_name = cleanup_list
        
        length = redis_client.rpush(list_name, "a", "b", "c")
        assert length == 3
        assert redis_client.llen(list_name) == 3
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_blpop(self, redis_client: RedisClient, cleanup_list: str):
        """blpop が正しく動作すること"""
        list_name = cleanup_list
        redis_client.rpush(list_name, "first", "second")
        
        result = redis_client.blpop(list_name, timeout=1)
        assert result is not None
        assert result[0] == list_name
        assert result[1] == "first"
        
        result = redis_client.blpop(list_name, timeout=1)
        assert result is not None
        assert result[1] == "second"
    
    @pytest.mark.usefixtures("skip_without_redis")
    def test_blpop_timeout(self, redis_client: RedisClient, cleanup_list: str):
        """blpop でタイムアウト時にNoneを返すこと"""
        list_name = cleanup_list + "-empty"
        
        result = redis_client.blpop(list_name, timeout=1)
        assert result is None


class TestCreateClient:
    """create_client ファクトリ関数のテスト"""
    
    def test_create_redis_py_client(self, redis_config: RedisConfig):
        """redis-pyクライアントが作成されること"""
        client = create_client(use_redis_py=True, config=redis_config)
        assert isinstance(client, RedisClient)
    
    def test_create_resp_client(self, redis_config: RedisConfig):
        """RESPクライアントが作成されること"""
        client = create_client(use_redis_py=False, config=redis_config)
        assert isinstance(client, RespRedisClient)
