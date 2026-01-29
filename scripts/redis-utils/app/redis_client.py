"""
Redis接続・操作の共通クライアントモジュール

RESPプロトコルによる直接接続とredis-pyライブラリを使った接続の両方をサポート。
"""

import json
import socket
from typing import Any, Optional, Union

from .config import RedisConfig, get_default_config


class RedisConnectionError(Exception):
    """Redis接続エラー"""
    pass


class RedisCommandError(Exception):
    """Redisコマンドエラー"""
    pass


class RespRedisClient:
    """
    RESPプロトコルによるRedisクライアント
    
    ソケットを使用してRedisと直接通信する。
    外部ライブラリに依存しない軽量な実装。
    
    Attributes:
        host: Redisホスト名
        port: Redisポート番号
        timeout: ソケットタイムアウト（秒）
    """
    
    def __init__(
        self,
        host: str = "redis",
        port: int = 6379,
        timeout: float = 10.0,
        config: Optional[RedisConfig] = None,
    ):
        """
        クライアントを初期化
        
        Args:
            host: Redisホスト名（configが指定された場合は無視）
            port: Redisポート番号（configが指定された場合は無視）
            timeout: ソケットタイムアウト（configが指定された場合は無視）
            config: Redis設定オブジェクト（指定された場合はこちらを優先）
        """
        if config:
            self.host = config.host
            self.port = config.port
            self.timeout = config.socket_timeout
        else:
            self.host = host
            self.port = port
            self.timeout = timeout
    
    def _send_command(self, *args: str) -> str:
        """
        RESPプロトコルでRedisコマンドを送信
        
        Args:
            *args: コマンドと引数
        
        Returns:
            Redisからのレスポンス文字列
        
        Raises:
            RedisConnectionError: 接続エラー
            RedisCommandError: コマンド実行エラー
        """
        # RESPプロトコルでコマンドを構築
        cmd_parts = [f"*{len(args)}"]
        for arg in args:
            encoded = str(arg).encode("utf-8")
            cmd_parts.append(f"${len(encoded)}")
            cmd_parts.append(str(arg))
        command = "\r\n".join(cmd_parts) + "\r\n"
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                sock.connect((self.host, self.port))
                sock.sendall(command.encode("utf-8"))
                
                response = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    if b"\r\n" in response:
                        break
            
            return response.decode("utf-8").strip()
        
        except ConnectionRefusedError:
            raise RedisConnectionError(
                f"Cannot connect to Redis at {self.host}:{self.port}"
            )
        except socket.gaierror:
            raise RedisConnectionError(
                f"Cannot resolve hostname '{self.host}'"
            )
        except socket.timeout:
            raise RedisConnectionError(
                f"Connection to {self.host}:{self.port} timed out"
            )
    
    def _parse_integer_response(self, response: str) -> int:
        """整数レスポンスをパース"""
        if response.startswith(":"):
            return int(response[1:])
        elif response.startswith("-"):
            raise RedisCommandError(f"Redis error: {response[1:]}")
        else:
            raise RedisCommandError(f"Unexpected response: {response}")
    
    def _parse_string_response(self, response: str) -> Optional[str]:
        """文字列レスポンスをパース"""
        if response.startswith("+"):
            return response[1:]
        elif response.startswith("$-1"):
            return None  # null bulk string
        elif response.startswith("$"):
            # Bulk string: $<length>\r\n<data>\r\n
            parts = response.split("\r\n", 2)
            if len(parts) >= 2:
                return parts[1]
            return response
        elif response.startswith("-"):
            raise RedisCommandError(f"Redis error: {response[1:]}")
        else:
            return response
    
    def ping(self) -> bool:
        """
        Redisへの接続を確認
        
        Returns:
            接続成功時True
        
        Raises:
            RedisConnectionError: 接続失敗時
        """
        response = self._send_command("PING")
        return response == "+PONG"
    
    def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        キーに値を設定
        
        Args:
            key: キー名
            value: 値
            ttl: 有効期限（秒）
        
        Returns:
            設定成功時True
        """
        if ttl:
            response = self._send_command("SET", key, value, "EX", str(ttl))
        else:
            response = self._send_command("SET", key, value)
        return response == "+OK"
    
    def get(self, key: str) -> Optional[str]:
        """
        キーの値を取得
        
        Args:
            key: キー名
        
        Returns:
            値（キーが存在しない場合はNone）
        """
        response = self._send_command("GET", key)
        return self._parse_string_response(response)
    
    def exists(self, key: str) -> bool:
        """
        キーの存在を確認
        
        Args:
            key: キー名
        
        Returns:
            キーが存在すればTrue
        """
        response = self._send_command("EXISTS", key)
        return self._parse_integer_response(response) == 1
    
    def expire(self, key: str, ttl: int) -> bool:
        """
        キーの有効期限を設定
        
        Args:
            key: キー名
            ttl: 有効期限（秒）
        
        Returns:
            設定成功時True（キーが存在しない場合はFalse）
        """
        response = self._send_command("EXPIRE", key, str(ttl))
        return self._parse_integer_response(response) == 1
    
    def delete(self, *keys: str) -> int:
        """
        キーを削除
        
        Args:
            *keys: 削除するキー名
        
        Returns:
            削除されたキーの数
        """
        response = self._send_command("DEL", *keys)
        return self._parse_integer_response(response)
    
    def rpush(self, list_name: str, *messages: str) -> int:
        """
        リストの末尾にメッセージを追加
        
        Args:
            list_name: リスト名
            *messages: 追加するメッセージ
        
        Returns:
            追加後のリスト長
        """
        response = self._send_command("RPUSH", list_name, *messages)
        return self._parse_integer_response(response)
    
    def lpush(self, list_name: str, *messages: str) -> int:
        """
        リストの先頭にメッセージを追加
        
        Args:
            list_name: リスト名
            *messages: 追加するメッセージ
        
        Returns:
            追加後のリスト長
        """
        response = self._send_command("LPUSH", list_name, *messages)
        return self._parse_integer_response(response)
    
    def llen(self, list_name: str) -> int:
        """
        リストの長さを取得
        
        Args:
            list_name: リスト名
        
        Returns:
            リストの要素数
        """
        response = self._send_command("LLEN", list_name)
        return self._parse_integer_response(response)
    
    def publish(self, channel: str, message: str) -> int:
        """
        Pub/Subチャンネルにメッセージを送信
        
        Args:
            channel: チャンネル名
            message: 送信するメッセージ
        
        Returns:
            メッセージを受信したサブスクライバーの数
        """
        response = self._send_command("PUBLISH", channel, message)
        return self._parse_integer_response(response)
    
    def xadd(
        self,
        stream: str,
        fields: dict[str, str],
        message_id: str = "*",
    ) -> str:
        """
        ストリームにエントリを追加
        
        Args:
            stream: ストリーム名
            fields: フィールドと値の辞書
            message_id: メッセージID（"*"で自動生成）
        
        Returns:
            生成されたメッセージID
        """
        args = ["XADD", stream, message_id]
        for k, v in fields.items():
            args.extend([k, str(v)])
        response = self._send_command(*args)
        return self._parse_string_response(response) or ""


class RedisClient:
    """
    redis-pyライブラリを使用したRedisクライアント
    
    redis-pyがインストールされている場合に使用可能。
    BLPOPなどのブロッキング操作をサポート。
    
    Attributes:
        config: Redis設定
        client: redis.Redisインスタンス
    """
    
    def __init__(
        self,
        host: str = "redis",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True,
        config: Optional[RedisConfig] = None,
    ):
        """
        クライアントを初期化
        
        Args:
            host: Redisホスト名（configが指定された場合は無視）
            port: Redisポート番号（configが指定された場合は無視）
            db: データベース番号（configが指定された場合は無視）
            password: パスワード（configが指定された場合は無視）
            decode_responses: レスポンスをデコードするか
            config: Redis設定オブジェクト（指定された場合はこちらを優先）
        
        Raises:
            ImportError: redis-pyがインストールされていない場合
        """
        try:
            import redis
        except ImportError:
            raise ImportError(
                "redis-py is not installed. "
                "Install with: pip install redis"
            )
        
        if config:
            self.host = config.host
            self.port = config.port
            self.db = config.db
            self.password = config.password
            self.decode_responses = config.decode_responses
            socket_timeout = config.socket_timeout
            socket_connect_timeout = config.socket_connect_timeout
        else:
            self.host = host
            self.port = port
            self.db = db
            self.password = password
            self.decode_responses = decode_responses
            socket_timeout = 10.0
            socket_connect_timeout = 10.0
        
        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=self.decode_responses,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
        )
    
    def ping(self) -> bool:
        """
        Redisへの接続を確認
        
        Returns:
            接続成功時True
        """
        try:
            return self.client.ping()
        except Exception as e:
            raise RedisConnectionError(f"Cannot connect to Redis: {e}")
    
    def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        キーに値を設定
        
        Args:
            key: キー名
            value: 値
            ttl: 有効期限（秒）
        
        Returns:
            設定成功時True
        """
        if ttl:
            return bool(self.client.set(key, value, ex=ttl))
        else:
            return bool(self.client.set(key, value))
    
    def get(self, key: str) -> Optional[str]:
        """
        キーの値を取得
        
        Args:
            key: キー名
        
        Returns:
            値（キーが存在しない場合はNone）
        """
        result = self.client.get(key)
        return str(result) if result is not None else None
    
    def exists(self, key: str) -> bool:
        """
        キーの存在を確認
        
        Args:
            key: キー名
        
        Returns:
            キーが存在すればTrue
        """
        return bool(self.client.exists(key))
    
    def expire(self, key: str, ttl: int) -> bool:
        """
        キーの有効期限を設定
        
        Args:
            key: キー名
            ttl: 有効期限（秒）
        
        Returns:
            設定成功時True
        """
        return bool(self.client.expire(key, ttl))
    
    def delete(self, *keys: str) -> int:
        """
        キーを削除
        
        Args:
            *keys: 削除するキー名
        
        Returns:
            削除されたキーの数
        """
        return self.client.delete(*keys)
    
    def rpush(self, list_name: str, *messages: str) -> int:
        """
        リストの末尾にメッセージを追加
        
        Args:
            list_name: リスト名
            *messages: 追加するメッセージ
        
        Returns:
            追加後のリスト長
        """
        return self.client.rpush(list_name, *messages)
    
    def lpush(self, list_name: str, *messages: str) -> int:
        """
        リストの先頭にメッセージを追加
        
        Args:
            list_name: リスト名
            *messages: 追加するメッセージ
        
        Returns:
            追加後のリスト長
        """
        return self.client.lpush(list_name, *messages)
    
    def blpop(
        self,
        list_name: Union[str, list[str]],
        timeout: int = 0,
    ) -> Optional[tuple[str, str]]:
        """
        リストからブロッキングポップ
        
        Args:
            list_name: リスト名（または複数リスト名のリスト）
            timeout: タイムアウト秒数（0は無限待機）
        
        Returns:
            (リスト名, メッセージ)のタプル、タイムアウト時はNone
        """
        result = self.client.blpop(list_name, timeout=timeout)
        if result:
            return (str(result[0]), str(result[1]))
        return None
    
    def brpop(
        self,
        list_name: Union[str, list[str]],
        timeout: int = 0,
    ) -> Optional[tuple[str, str]]:
        """
        リストからブロッキング右ポップ
        
        Args:
            list_name: リスト名（または複数リスト名のリスト）
            timeout: タイムアウト秒数（0は無限待機）
        
        Returns:
            (リスト名, メッセージ)のタプル、タイムアウト時はNone
        """
        result = self.client.brpop(list_name, timeout=timeout)
        if result:
            return (str(result[0]), str(result[1]))
        return None
    
    def llen(self, list_name: str) -> int:
        """
        リストの長さを取得
        
        Args:
            list_name: リスト名
        
        Returns:
            リストの要素数
        """
        return self.client.llen(list_name)
    
    def publish(self, channel: str, message: str) -> int:
        """
        Pub/Subチャンネルにメッセージを送信
        
        Args:
            channel: チャンネル名
            message: 送信するメッセージ
        
        Returns:
            メッセージを受信したサブスクライバーの数
        """
        return self.client.publish(channel, message)
    
    def xadd(
        self,
        stream: str,
        fields: dict[str, Any],
        message_id: str = "*",
    ) -> str:
        """
        ストリームにエントリを追加
        
        Args:
            stream: ストリーム名
            fields: フィールドと値の辞書
            message_id: メッセージID（"*"で自動生成）
        
        Returns:
            生成されたメッセージID
        """
        result = self.client.xadd(stream, fields, id=message_id)
        return str(result) if result else ""
    
    def xread(
        self,
        streams: dict[str, str],
        count: Optional[int] = None,
        block: Optional[int] = None,
    ) -> Optional[list]:
        """
        ストリームからエントリを読み取り
        
        Args:
            streams: {ストリーム名: 最後に読んだID}の辞書
            count: 読み取る最大エントリ数
            block: ブロッキングタイムアウト（ミリ秒）
        
        Returns:
            読み取ったエントリのリスト
        """
        return self.client.xread(streams, count=count, block=block)


def create_client(
    use_redis_py: bool = True,
    config: Optional[RedisConfig] = None,
) -> Union[RedisClient, RespRedisClient]:
    """
    Redisクライアントを作成するファクトリ関数
    
    Args:
        use_redis_py: redis-pyを使用するか（Falseの場合はRESP直接）
        config: Redis設定（Noneの場合はデフォルト設定を使用）
    
    Returns:
        RedisClient または RespRedisClient のインスタンス
    """
    if config is None:
        config = get_default_config()
    
    if use_redis_py:
        try:
            return RedisClient(config=config)
        except ImportError:
            # redis-pyがない場合はRESP実装にフォールバック
            return RespRedisClient(config=config)
    else:
        return RespRedisClient(config=config)
