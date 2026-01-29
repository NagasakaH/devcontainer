"""
pytest fixtures for Redis-related tests.

Provides fixtures for Redis connection, orchestration setup, and cleanup.
"""

import os
import socket
import pytest
from typing import Generator, Optional

from app.config import RedisConfig
from app.redis_client import RedisClient, RespRedisClient, RedisConnectionError
from app.orchestration import (
    initialize_orchestration,
    initialize_summoner_orchestration,
    cleanup_session,
    OrchestrationConfig,
)


def _try_connect_redis(host: str, port: int, timeout: float = 2.0) -> bool:
    """Redisへの接続を試行"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def _get_redis_host() -> str:
    """利用可能なRedisホストを取得
    
    docker compose環境では 'redis' 、ローカル環境では 'localhost' を試行。
    """
    # 環境変数を優先
    if env_host := os.environ.get("REDIS_HOST"):
        return env_host
    
    # docker compose環境
    if _try_connect_redis("redis", 6379):
        return "redis"
    
    # ローカル環境
    if _try_connect_redis("localhost", 6379):
        return "localhost"
    
    # デフォルト
    return "redis"


@pytest.fixture(scope="session")
def redis_host() -> str:
    """Redis ホスト名を提供するfixture"""
    return _get_redis_host()


@pytest.fixture(scope="session")
def redis_port() -> int:
    """Redis ポート番号を提供するfixture"""
    return int(os.environ.get("REDIS_PORT", "6379"))


@pytest.fixture(scope="session")
def redis_available(redis_host: str, redis_port: int) -> bool:
    """Redisが利用可能かどうかを確認するfixture"""
    return _try_connect_redis(redis_host, redis_port)


@pytest.fixture
def skip_without_redis(redis_available: bool):
    """Redisが利用できない場合にテストをスキップするfixture"""
    if not redis_available:
        pytest.skip("Redis is not available")


@pytest.fixture
def redis_config(redis_host: str, redis_port: int) -> RedisConfig:
    """Redis設定を提供するfixture"""
    return RedisConfig(
        host=redis_host,
        port=redis_port,
        db=0,
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
    )


@pytest.fixture
def resp_client(
    redis_config: RedisConfig,
    skip_without_redis,
) -> Generator[RespRedisClient, None, None]:
    """RespRedisClientインスタンスを提供するfixture"""
    client = RespRedisClient(config=redis_config)
    yield client


@pytest.fixture
def redis_client(
    redis_config: RedisConfig,
    skip_without_redis,
) -> Generator[RedisClient, None, None]:
    """RedisClientインスタンスを提供するfixture"""
    client = RedisClient(config=redis_config)
    yield client


@pytest.fixture
def test_session_id() -> str:
    """テスト用のユニークなセッションIDを生成"""
    import time
    return f"test-{int(time.time() * 1000)}-{os.getpid()}"


@pytest.fixture
def orchestration_config(
    redis_host: str,
    redis_port: int,
    test_session_id: str,
    skip_without_redis,
) -> Generator[OrchestrationConfig, None, None]:
    """通常モードのオーケストレーション設定を提供するfixture
    
    テスト後に自動でクリーンアップを行う。
    """
    config = initialize_orchestration(
        host=redis_host,
        port=redis_port,
        max_children=3,
        ttl=60,  # テスト用に短いTTL
    )
    
    yield config
    
    # クリーンアップ
    try:
        cleanup_session(
            host=redis_host,
            port=redis_port,
            config=config,
        )
    except Exception:
        pass


@pytest.fixture
def summoner_config(
    redis_host: str,
    redis_port: int,
    test_session_id: str,
    skip_without_redis,
) -> Generator[OrchestrationConfig, None, None]:
    """Summonerモードのオーケストレーション設定を提供するfixture
    
    テスト後に自動でクリーンアップを行う。
    """
    config = initialize_summoner_orchestration(
        host=redis_host,
        port=redis_port,
        max_children=3,
        ttl=60,  # テスト用に短いTTL
    )
    
    yield config
    
    # クリーンアップ
    try:
        cleanup_session(
            host=redis_host,
            port=redis_port,
            config=config,
        )
    except Exception:
        pass


@pytest.fixture
def unique_list_name(test_session_id: str) -> str:
    """テスト用のユニークなリスト名を生成するfixture"""
    return f"test-list:{test_session_id}"


@pytest.fixture
def cleanup_list(
    redis_host: str,
    redis_port: int,
    unique_list_name: str,
    redis_available: bool,
) -> Generator[str, None, None]:
    """テスト後にリストをクリーンアップするfixture"""
    yield unique_list_name
    
    if redis_available:
        try:
            client = RespRedisClient(host=redis_host, port=redis_port)
            client.delete(unique_list_name)
        except Exception:
            pass


@pytest.fixture
def cleanup_lists(
    redis_host: str,
    redis_port: int,
    redis_available: bool,
) -> Generator[list[str], None, None]:
    """複数リストのクリーンアップ用fixture
    
    使用例:
        def test_something(cleanup_lists):
            cleanup_lists.append("my-list-1")
            cleanup_lists.append("my-list-2")
            # テスト実行
    """
    lists: list[str] = []
    yield lists
    
    if redis_available and lists:
        try:
            client = RespRedisClient(host=redis_host, port=redis_port)
            client.delete(*lists)
        except Exception:
            pass
