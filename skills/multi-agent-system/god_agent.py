#!/usr/bin/env python3
"""
神エージェント（God Agent）

システム全体を管理するオーケストレーター。
- Redis接続の確立とチャンネル/キューの初期化
- 親エージェント1個と子エージェント5個の起動
- ユーザーからの作業指示を親エージェントに転送
- 全エージェントの終了を監視してクリーンアップ

Usage:
    python god_agent.py --task "ユーザーからの作業指示"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 共通ライブラリ
try:
    import sys
    _lib_path = str(__file__).rsplit("/", 2)[0]
    if _lib_path not in sys.path:
        sys.path.insert(0, _lib_path)
    
    from lib.redis_client import RedisClient, RedisConfig
    from lib.message import (
        Message,
        MessageType,
        create_startup_info,
        create_user_notification,
        NotificationEvent,
        AgentRole,
        ChannelsConfig,
        AgentConfig,
        PROTOCOL_VERSION,
    )
    from lib.channel_config import ChannelConfig
    from lib.logger import AgentLogger, LogLevel
    HAS_LIB = True
except ImportError as e:
    # 共通ライブラリが未実装の場合のフォールバック
    HAS_LIB = False
    RedisClient = None
    PROTOCOL_VERSION = "1.0.0"

# 定数
NUM_CHILD_AGENTS = 5
DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_MAX_RETRIES = 3


# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
logger = logging.getLogger("god-agent")


class GodAgent:
    """神エージェント - システム全体のオーケストレーター"""

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        working_directory: str | None = None,
        docs_root: str | None = None,
    ) -> None:
        """
        神エージェントを初期化する。

        Args:
            redis_host: Redisサーバーのホスト名
            redis_port: Redisサーバーのポート番号
            working_directory: 作業ディレクトリパス
            docs_root: ドキュメント出力ルートパス
        """
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.working_directory = working_directory or os.getcwd()
        self.docs_root = docs_root or os.environ.get("DOCS_ROOT", "")

        # セッションID生成
        self.session_id = self._generate_session_id()
        self.agent_id = f"god-agent-{self.session_id[:8]}"

        # Redis接続（遅延初期化）
        self._redis: Any = None

        # チャンネル/キュー名
        self.channels = self._initialize_channel_names()

        # サブプロセス管理
        self.parent_process: subprocess.Popen | None = None
        self.child_processes: list[subprocess.Popen] = []

        # 終了フラグ
        self._shutdown_event = asyncio.Event()

        logger.info(f"God Agent initialized with session_id={self.session_id}")

    def _generate_session_id(self) -> str:
        """
        セッションIDを生成する。

        Returns:
            フォーマット: {timestamp}-{random}
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        random_part = uuid.uuid4().hex[:8]
        return f"{timestamp}-{random_part}"

    def _initialize_channel_names(self) -> dict[str, str]:
        """
        Redis チャンネル/キュー名を初期化する。

        Returns:
            チャンネル/キュー名の辞書
        """
        session = self.session_id
        return {
            # キュー（List構造）
            "task_queue": f"mas:queue:task:{session}",
            "completion_queue": f"mas:queue:completion:{session}",
            # Pub/Subチャンネル
            "terminate_channel": f"mas:channel:terminate:{session}",
            "notify_channel": f"mas:channel:notify:{session}",
            # 親エージェント用のタスク受信キュー
            "parent_inbox": f"mas:queue:parent-inbox:{session}",
        }

    async def connect_redis(self) -> None:
        """Redis接続を確立する。"""
        if RedisClient is not None:
            # 共通ライブラリを使用
            self._redis = await RedisClient.create(
                host=self.redis_host,
                port=self.redis_port,
            )
        else:
            # フォールバック: redis-pyを直接使用
            try:
                import redis.asyncio as aioredis

                self._redis = await aioredis.from_url(
                    f"redis://{self.redis_host}:{self.redis_port}",
                    encoding="utf-8",
                    decode_responses=True,
                )
                logger.info(f"Connected to Redis at {self.redis_host}:{self.redis_port}")
            except ImportError:
                logger.error("redis package not installed. Run: pip install redis")
                raise

    async def disconnect_redis(self) -> None:
        """Redis接続を切断する。"""
        if self._redis is not None:
            await self._redis.close()
            logger.info("Disconnected from Redis")

    async def cleanup_redis_resources(self) -> None:
        """
        Redisリソースをクリーンアップする。
        セッションに関連するキー/チャンネルを削除。
        """
        if self._redis is None:
            return

        keys_to_delete = list(self.channels.values())
        for key in keys_to_delete:
            try:
                await self._redis.delete(key)
                logger.debug(f"Deleted Redis key: {key}")
            except Exception as e:
                logger.warning(f"Failed to delete key {key}: {e}")

        logger.info("Redis resources cleaned up")

    def _create_message(
        self,
        message_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        プロトコル準拠のメッセージを作成する。

        Args:
            message_type: メッセージタイプ
            payload: ペイロード

        Returns:
            メッセージ辞書
        """
        return {
            "protocol_version": PROTOCOL_VERSION,
            "message_type": message_type,
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sender_id": self.agent_id,
            "payload": payload,
        }

    def _create_startup_info(
        self,
        agent_id: str,
        role: str,
        listen_channels: list[str],
        publish_channels: list[str],
        custom_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        STARTUP_INFO メッセージを作成する。

        Args:
            agent_id: 割り当てるエージェントID
            role: エージェントの役割（"parent" or "child"）
            listen_channels: 購読するチャンネル/リスト
            publish_channels: 発行先チャンネル/リスト
            custom_params: カスタムパラメータ

        Returns:
            STARTUP_INFO メッセージ
        """
        payload = {
            "agent_id": agent_id,
            "role": role,
            "channels": {
                "listen": listen_channels,
                "publish": publish_channels,
            },
            "config": {
                "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
                "max_retries": DEFAULT_MAX_RETRIES,
                "working_directory": self.working_directory,
                "docs_root": self.docs_root,
                "custom_params": custom_params or {},
            },
        }
        return self._create_message("STARTUP_INFO", payload)

    def _create_user_notification(
        self,
        event_type: str,
        title: str,
        message: str,
        severity: str = "INFO",
        task_id: str | None = None,
        progress: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        USER_NOTIFICATION メッセージを作成する。

        Args:
            event_type: イベント種別
            title: 通知タイトル
            message: 通知メッセージ本文
            severity: 重要度
            task_id: 関連するタスクID
            progress: 進捗情報

        Returns:
            USER_NOTIFICATION メッセージ
        """
        payload = {
            "event_type": event_type,
            "severity": severity,
            "details": {
                "title": title,
                "message": message,
                "task_id": task_id,
                "progress": progress,
                "actions": [],
            },
        }
        return self._create_message("USER_NOTIFICATION", payload)

    async def publish_notification(
        self,
        event_type: str,
        title: str,
        message: str,
        severity: str = "INFO",
    ) -> None:
        """
        ユーザー通知をPublishする。

        Args:
            event_type: イベント種別
            title: 通知タイトル
            message: 通知メッセージ
            severity: 重要度
        """
        if self._redis is None:
            return

        notification = self._create_user_notification(
            event_type=event_type,
            title=title,
            message=message,
            severity=severity,
        )
        await self._redis.publish(
            self.channels["notify_channel"],
            json.dumps(notification, ensure_ascii=False),
        )
        logger.info(f"Published notification: {event_type} - {title}")

    def _get_agent_script_path(self, agent_type: str) -> Path:
        """
        エージェントスクリプトのパスを取得する。

        Args:
            agent_type: "parent" or "child"

        Returns:
            スクリプトのパス
        """
        base_dir = Path(__file__).parent
        return base_dir / f"{agent_type}_agent.py"

    async def start_parent_agent(self, task: str) -> subprocess.Popen:
        """
        親エージェントをサブプロセスとして起動する。

        Args:
            task: ユーザーからの作業指示

        Returns:
            起動したサブプロセス
        """
        agent_id = f"parent-agent-{self.session_id[:8]}"

        # 起動情報メッセージ作成
        startup_info = self._create_startup_info(
            agent_id=agent_id,
            role="parent",
            listen_channels=[
                self.channels["parent_inbox"],
                self.channels["completion_queue"],
            ],
            publish_channels=[
                self.channels["task_queue"],
                self.channels["notify_channel"],
                self.channels["terminate_channel"],
            ],
            custom_params={
                "max_concurrent_children": NUM_CHILD_AGENTS,
                "session_id": self.session_id,
            },
        )

        # 起動情報をRedis経由で配信（またはコマンドライン引数で渡す）
        startup_info_json = json.dumps(startup_info, ensure_ascii=False)

        script_path = self._get_agent_script_path("parent")
        cmd = [
            sys.executable,
            str(script_path),
            "--startup-info",
            startup_info_json,
            "--task",
            task,
        ]

        logger.info(f"Starting parent agent: {agent_id}")
        process = subprocess.Popen(
            cmd,
            cwd=self.working_directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.parent_process = process
        return process

    async def start_child_agents(self) -> list[subprocess.Popen]:
        """
        子エージェント5個をサブプロセスとして同時起動する。

        Returns:
            起動したサブプロセスのリスト
        """
        processes: list[subprocess.Popen] = []
        script_path = self._get_agent_script_path("child")

        for i in range(1, NUM_CHILD_AGENTS + 1):
            agent_id = f"child-agent-{self.session_id[:8]}-{i:02d}"

            # 起動情報メッセージ作成
            startup_info = self._create_startup_info(
                agent_id=agent_id,
                role="child",
                listen_channels=[
                    self.channels["task_queue"],
                    self.channels["terminate_channel"],
                ],
                publish_channels=[
                    self.channels["completion_queue"],
                    self.channels["notify_channel"],
                ],
                custom_params={
                    "child_index": i,
                    "session_id": self.session_id,
                },
            )

            startup_info_json = json.dumps(startup_info, ensure_ascii=False)

            cmd = [
                sys.executable,
                str(script_path),
                "--startup-info",
                startup_info_json,
            ]

            logger.info(f"Starting child agent: {agent_id}")
            process = subprocess.Popen(
                cmd,
                cwd=self.working_directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            processes.append(process)

        self.child_processes = processes
        logger.info(f"Started {len(processes)} child agents")
        return processes

    async def transfer_task_to_parent(self, task: str) -> None:
        """
        ユーザーからの作業指示を親エージェントに転送する。

        Args:
            task: 作業指示
        """
        if self._redis is None:
            logger.error("Redis not connected")
            return

        # タスクメッセージを親エージェントのinboxに送信
        task_message = self._create_message(
            "TASK_INSTRUCTION",
            {
                "instruction": task,
                "session_id": self.session_id,
                "working_directory": self.working_directory,
                "docs_root": self.docs_root,
            },
        )

        await self._redis.rpush(
            self.channels["parent_inbox"],
            json.dumps(task_message, ensure_ascii=False),
        )
        logger.info("Task instruction transferred to parent agent")

    async def wait_for_completion(self, timeout: float | None = None) -> bool:
        """
        親エージェントからの終了信号を待機する。

        Args:
            timeout: タイムアウト秒数（Noneで無限待機）

        Returns:
            正常終了の場合True
        """
        if self.parent_process is None:
            logger.warning("No parent process to wait for")
            return False

        try:
            if timeout is not None:
                # タイムアウト付きで待機
                return_code = self.parent_process.wait(timeout=timeout)
            else:
                return_code = self.parent_process.wait()

            logger.info(f"Parent agent exited with code: {return_code}")
            return return_code == 0

        except subprocess.TimeoutExpired:
            logger.warning("Parent agent did not complete within timeout")
            return False

    async def terminate_all_agents(self, timeout: float = 30.0) -> None:
        """
        全エージェントを終了させる。

        Args:
            timeout: 終了待機タイムアウト（秒）
        """
        # 親エージェントの終了
        if self.parent_process is not None and self.parent_process.poll() is None:
            logger.info("Terminating parent agent...")
            self.parent_process.terminate()
            try:
                self.parent_process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                logger.warning("Parent agent did not terminate, killing...")
                self.parent_process.kill()

        # 子エージェントの終了
        for i, process in enumerate(self.child_processes):
            if process.poll() is None:
                logger.info(f"Terminating child agent {i + 1}...")
                process.terminate()

        # 全子エージェントの終了待機
        for i, process in enumerate(self.child_processes):
            try:
                process.wait(timeout=timeout / NUM_CHILD_AGENTS)
            except subprocess.TimeoutExpired:
                logger.warning(f"Child agent {i + 1} did not terminate, killing...")
                process.kill()

        logger.info("All agents terminated")

    async def run(self, task: str) -> int:
        """
        神エージェントのメイン実行ループ。

        Args:
            task: ユーザーからの作業指示

        Returns:
            終了コード（0: 成功, 1: 失敗）
        """
        exit_code = 1

        try:
            # 1. Redis接続
            await self.connect_redis()

            # 2. ユーザー通知: 作業開始
            await self.publish_notification(
                event_type="INFO",
                title="システム起動",
                message=f"マルチエージェントシステムを起動しています (session: {self.session_id})",
            )

            # 3. 子エージェント5個を同時起動
            await self.start_child_agents()

            # 子エージェントの起動を少し待つ
            await asyncio.sleep(1.0)

            # 4. 親エージェント1個を起動
            await self.start_parent_agent(task)

            # 5. タスクを親エージェントに転送
            await self.transfer_task_to_parent(task)

            # 6. ユーザー通知: エージェント起動完了
            await self.publish_notification(
                event_type="INFO",
                title="エージェント起動完了",
                message=f"親エージェント1個、子エージェント{NUM_CHILD_AGENTS}個を起動しました",
            )

            # 7. 親エージェントの終了を待機
            success = await self.wait_for_completion()

            # 8. ユーザー通知: 作業完了
            if success:
                await self.publish_notification(
                    event_type="INFO",
                    title="作業完了",
                    message="全てのタスクが正常に完了しました",
                )
                exit_code = 0
            else:
                await self.publish_notification(
                    event_type="ERROR",
                    title="作業失敗",
                    message="タスクの実行中にエラーが発生しました",
                    severity="ERROR",
                )

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            await self.publish_notification(
                event_type="WARNING",
                title="中断",
                message="ユーザーによる中断を受信しました",
                severity="WARN",
            )

        except Exception as e:
            logger.exception(f"Error in God Agent: {e}")
            await self.publish_notification(
                event_type="ERROR",
                title="システムエラー",
                message=str(e),
                severity="CRITICAL",
            )

        finally:
            # 9. 全エージェントの終了確認
            await self.terminate_all_agents()

            # 10. Redisリソースのクリーンアップ
            await self.cleanup_redis_resources()
            await self.disconnect_redis()

        return exit_code


def parse_args() -> argparse.Namespace:
    """コマンドライン引数をパースする。"""
    parser = argparse.ArgumentParser(
        description="神エージェント（God Agent）- マルチエージェントシステムオーケストレーター",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python god_agent.py --task "コードレビューを実行してください"
  python god_agent.py --task "テストを実行してカバレッジを確認" --redis-host redis.local
        """,
    )
    parser.add_argument(
        "--task",
        type=str,
        required=True,
        help="ユーザーからの作業指示",
    )
    parser.add_argument(
        "--redis-host",
        type=str,
        default=os.environ.get("REDIS_HOST", "localhost"),
        help="Redisサーバーのホスト名 (default: localhost or $REDIS_HOST)",
    )
    parser.add_argument(
        "--redis-port",
        type=int,
        default=int(os.environ.get("REDIS_PORT", "6379")),
        help="Redisサーバーのポート番号 (default: 6379 or $REDIS_PORT)",
    )
    parser.add_argument(
        "--working-dir",
        type=str,
        default=os.getcwd(),
        help="作業ディレクトリパス (default: current directory)",
    )
    parser.add_argument(
        "--docs-root",
        type=str,
        default=os.environ.get("DOCS_ROOT", ""),
        help="ドキュメント出力ルートパス (default: $DOCS_ROOT)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="詳細ログを出力",
    )
    return parser.parse_args()


async def main() -> int:
    """エントリーポイント。"""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    agent = GodAgent(
        redis_host=args.redis_host,
        redis_port=args.redis_port,
        working_directory=args.working_dir,
        docs_root=args.docs_root,
    )

    # シグナルハンドラ設定
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(agent.terminate_all_agents()))

    return await agent.run(args.task)


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
