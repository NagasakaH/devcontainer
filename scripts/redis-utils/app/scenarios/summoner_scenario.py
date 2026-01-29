#!/usr/bin/env python3
"""
Summonerシナリオスクリプト

Summonerエージェントの動作をシミュレートする。
- オーケストレーションセッションの初期化
- moogleとchocoboへの接続情報の提供
- セッションのクリーンアップ

Usage:
    python -m app.scenarios.summoner_scenario [--host HOST] [--port PORT] [--max-children N]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict
from typing import Optional

from app.orchestration import (
    initialize_summoner_orchestration,
    get_config,
    cleanup_session,
    OrchestrationConfig,
)
from app.redis_client import RespRedisClient, RedisConnectionError


@dataclass
class SummonerResult:
    """Summonerシナリオの実行結果"""
    success: bool
    session_id: str = ""
    config_json: str = ""
    error: Optional[str] = None
    duration_ms: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class SummonerScenario:
    """
    Summonerシナリオクラス
    
    Summonerエージェントの動作をシミュレートする。
    オーケストレーションセッションの初期化、設定の提供、クリーンアップを行う。
    
    Attributes:
        host: Redisホスト名
        port: Redisポート番号
        max_children: 最大子エージェント数
        ttl: セッションのTTL（秒）
        config: 初期化後のオーケストレーション設定
    """
    
    def __init__(
        self,
        host: str = "redis",
        port: int = 6379,
        max_children: int = 5,
        ttl: int = 3600,
    ):
        """
        Summonerシナリオを初期化
        
        Args:
            host: Redisホスト名
            port: Redisポート番号
            max_children: 最大子エージェント（chocobo）数
            ttl: セッションのTTL（秒）
        """
        self.host = host
        self.port = port
        self.max_children = max_children
        self.ttl = ttl
        self.config: Optional[OrchestrationConfig] = None
    
    def initialize(self, session_id: Optional[str] = None) -> SummonerResult:
        """
        オーケストレーションセッションを初期化
        
        Args:
            session_id: 指定するセッションID（Noneの場合は自動生成）
        
        Returns:
            SummonerResult: 初期化結果
        """
        start_time = time.time()
        
        try:
            self.config = initialize_summoner_orchestration(
                host=self.host,
                port=self.port,
                max_children=self.max_children,
                session_id=session_id,
                ttl=self.ttl,
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return SummonerResult(
                success=True,
                session_id=self.config.session_id,
                config_json=self.config.to_json(indent=2),
                duration_ms=duration_ms,
            )
        
        except ConnectionRefusedError as e:
            return SummonerResult(
                success=False,
                error=f"Redis connection refused: {e}",
            )
        except Exception as e:
            return SummonerResult(
                success=False,
                error=str(e),
            )
    
    def get_moogle_info(self) -> dict:
        """
        moogle用の接続情報を取得
        
        Returns:
            moogleに渡す設定情報の辞書
        """
        if self.config is None:
            raise RuntimeError("Session not initialized. Call initialize() first.")
        
        return {
            "session_id": self.config.session_id,
            "mode": "moogle",
            "task_queues": self.config.parent_to_child_lists,
            "report_queue": self.config.child_to_parent_lists[0],
            "monitor_channel": self.config.monitor_channel,
            "max_children": self.config.max_children,
            "redis_host": self.host,
            "redis_port": self.port,
        }
    
    def get_chocobo_info(self, child_id: int) -> dict:
        """
        chocobo用の接続情報を取得
        
        Args:
            child_id: 子エージェントID（1始まり）
        
        Returns:
            chocoboに渡す設定情報の辞書
        """
        if self.config is None:
            raise RuntimeError("Session not initialized. Call initialize() first.")
        
        if child_id < 1 or child_id > self.max_children:
            raise ValueError(f"child_id must be 1-{self.max_children}, got {child_id}")
        
        return {
            "session_id": self.config.session_id,
            "mode": "chocobo",
            "child_id": child_id,
            "task_queue": self.config.parent_to_child_lists[child_id - 1],
            "report_queue": self.config.child_to_parent_lists[0],
            "monitor_channel": self.config.monitor_channel,
            "redis_host": self.host,
            "redis_port": self.port,
        }
    
    def verify_session(self) -> bool:
        """
        セッションがRedisに存在するか確認
        
        Returns:
            セッションが存在すればTrue
        """
        if self.config is None:
            return False
        
        try:
            retrieved = get_config(
                host=self.host,
                port=self.port,
                session_id=self.config.session_id,
            )
            return retrieved is not None
        except Exception:
            return False
    
    def cleanup(self) -> bool:
        """
        セッションをクリーンアップ
        
        Returns:
            クリーンアップ成功時True
        """
        if self.config is None:
            return False
        
        try:
            result = cleanup_session(
                host=self.host,
                port=self.port,
                config=self.config,
            )
            if result:
                self.config = None
            return result
        except Exception:
            return False
    
    def run_full_scenario(self) -> SummonerResult:
        """
        完全なシナリオを実行
        
        1. セッション初期化
        2. moogle/chocobo情報の生成
        3. セッション検証
        4. 情報を出力
        
        Returns:
            SummonerResult: シナリオ実行結果
        """
        print("=== Summoner Scenario ===")
        print()
        
        # 1. 初期化
        print("1. Initializing orchestration session...")
        result = self.initialize()
        
        if not result.success:
            print(f"   ERROR: {result.error}")
            return result
        
        print(f"   Session ID: {result.session_id}")
        print(f"   Duration: {result.duration_ms}ms")
        print()
        
        # 2. moogle情報
        print("2. Moogle connection info:")
        moogle_info = self.get_moogle_info()
        print(f"   Task Queues: {len(moogle_info['task_queues'])} queues")
        print(f"   Report Queue: {moogle_info['report_queue']}")
        print()
        
        # 3. chocobo情報（各子エージェント）
        print(f"3. Chocobo connection info ({self.max_children} workers):")
        for i in range(1, self.max_children + 1):
            info = self.get_chocobo_info(i)
            print(f"   Chocobo {i}: {info['task_queue']}")
        print()
        
        # 4. セッション検証
        print("4. Verifying session...")
        if self.verify_session():
            print("   Session verified: OK")
        else:
            print("   Session verified: FAILED")
        print()
        
        print("=== Summoner scenario completed ===")
        print()
        print("Configuration JSON:")
        print(result.config_json)
        
        return result


def _try_host(host: str, port: int) -> str:
    """利用可能なホストを試行"""
    import socket
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            return host
    except Exception:
        pass
    
    return host


def main():
    """メインエントリポイント"""
    parser = argparse.ArgumentParser(
        description="Summoner scenario - Initialize orchestration session"
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Redis host (default: auto-detect 'redis' or 'localhost')",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=6379,
        help="Redis port (default: 6379)",
    )
    parser.add_argument(
        "--max-children",
        type=int,
        default=5,
        help="Maximum number of child agents (default: 5)",
    )
    parser.add_argument(
        "--ttl",
        type=int,
        default=3600,
        help="Session TTL in seconds (default: 3600)",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Specify session ID (default: auto-generate UUID)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON only",
    )
    
    args = parser.parse_args()
    
    # ホストの自動検出
    if args.host is None:
        args.host = _try_host("redis", args.port)
        if args.host == "redis":
            # redisが見つからない場合はlocalhostを試す
            import socket
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                if sock.connect_ex(("redis", args.port)) != 0:
                    args.host = "localhost"
                sock.close()
            except Exception:
                args.host = "localhost"
    
    scenario = SummonerScenario(
        host=args.host,
        port=args.port,
        max_children=args.max_children,
        ttl=args.ttl,
    )
    
    if args.json:
        result = scenario.initialize(session_id=args.session_id)
        print(result.to_json())
        sys.exit(0 if result.success else 1)
    else:
        result = scenario.run_full_scenario()
        sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
