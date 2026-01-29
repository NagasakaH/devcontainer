"""
Redis 操作ラッパー

Redis への接続管理、キュー操作（RPUSH/BLPOP）、Pub/Sub 操作を提供します。

使用例:
    >>> from lib.redis_client import RedisClient, RedisConfig
    >>> config = RedisConfig(host="localhost", port=6379)
    >>> client = RedisClient(config)
    >>> client.connect()
    >>> client.rpush("my_queue", '{"message": "hello"}')
    >>> message = client.blpop("my_queue", timeout=10)
    >>> client.close()
"""

from dataclasses import dataclass, field
from typing import Callable, Optional
import json
import socket
import threading
import time


@dataclass
class RedisConfig:
    """Redis接続設定"""
    host: str = "localhost"
    port: int = 6379
    socket_timeout: float = 10.0
    retry_on_timeout: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0
    decode_responses: bool = True


class RedisError(Exception):
    """Redis操作エラーの基底クラス"""
    pass


class RedisConnectionError(RedisError):
    """Redis接続エラー"""
    pass


class RedisCommandError(RedisError):
    """Redisコマンド実行エラー"""
    pass


class RESPParser:
    """RESP (Redis Serialization Protocol) パーサー"""

    @staticmethod
    def encode(*args: str) -> bytes:
        """コマンドをRESPプロトコル形式にエンコード"""
        cmd_parts = [f"*{len(args)}"]
        for arg in args:
            encoded = arg if isinstance(arg, str) else str(arg)
            cmd_parts.append(f"${len(encoded.encode('utf-8'))}")
            cmd_parts.append(encoded)
        return ("\r\n".join(cmd_parts) + "\r\n").encode("utf-8")

    @staticmethod
    def decode(response: bytes, decode_strings: bool = True) -> any:
        """RESPレスポンスをデコード"""
        if not response:
            return None
        
        text = response.decode("utf-8")
        lines = text.split("\r\n")
        return RESPParser._parse_line(lines, 0, decode_strings)[0]

    @staticmethod
    def _parse_line(lines: list[str], idx: int, decode_strings: bool) -> tuple[any, int]:
        """再帰的にRESPレスポンスをパース"""
        if idx >= len(lines):
            return None, idx
        
        line = lines[idx]
        if not line:
            return None, idx + 1
        
        prefix = line[0]
        content = line[1:]
        
        if prefix == "+":  # Simple string
            return content, idx + 1
        elif prefix == "-":  # Error
            raise RedisCommandError(content)
        elif prefix == ":":  # Integer
            return int(content), idx + 1
        elif prefix == "$":  # Bulk string
            length = int(content)
            if length == -1:
                return None, idx + 1
            return lines[idx + 1], idx + 2
        elif prefix == "*":  # Array
            count = int(content)
            if count == -1:
                return None, idx + 1
            result = []
            current_idx = idx + 1
            for _ in range(count):
                item, current_idx = RESPParser._parse_line(lines, current_idx, decode_strings)
                result.append(item)
            return result, current_idx
        else:
            return line, idx + 1


class RedisClient:
    """
    Redis操作ラッパークラス
    
    キュー操作（RPUSH/BLPOP）とPub/Sub操作を提供します。
    接続プール管理と自動再接続をサポートします。
    """

    def __init__(self, config: Optional[RedisConfig] = None):
        """
        RedisClientを初期化
        
        Args:
            config: Redis接続設定。Noneの場合はデフォルト設定を使用
        """
        self.config = config or RedisConfig()
        self._socket: Optional[socket.socket] = None
        self._pubsub_socket: Optional[socket.socket] = None
        self._pubsub_thread: Optional[threading.Thread] = None
        self._pubsub_running = False
        self._pubsub_callbacks: dict[str, Callable[[str, str], None]] = {}
        self._lock = threading.Lock()

    def connect(self) -> None:
        """
        Redisに接続
        
        Raises:
            RedisConnectionError: 接続に失敗した場合
        """
        try:
            self._socket = self._create_socket()
            # 接続確認
            self._send_command("PING")
        except (socket.error, socket.timeout) as e:
            raise RedisConnectionError(
                f"Cannot connect to Redis at {self.config.host}:{self.config.port}: {e}"
            )

    def close(self) -> None:
        """接続を閉じる"""
        self._stop_pubsub()
        if self._socket:
            try:
                self._socket.close()
            except:
                pass
            self._socket = None
        if self._pubsub_socket:
            try:
                self._pubsub_socket.close()
            except:
                pass
            self._pubsub_socket = None

    def _create_socket(self) -> socket.socket:
        """ソケットを作成して接続"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.config.socket_timeout)
        sock.connect((self.config.host, self.config.port))
        return sock

    def _send_command(self, *args: str) -> any:
        """
        Redisコマンドを送信して結果を取得
        
        Args:
            *args: コマンドと引数
            
        Returns:
            コマンドの実行結果
            
        Raises:
            RedisCommandError: コマンド実行に失敗した場合
        """
        if not self._socket:
            raise RedisConnectionError("Not connected to Redis")

        with self._lock:
            retries = 0
            while retries <= self.config.max_retries:
                try:
                    # コマンドを送信
                    command = RESPParser.encode(*args)
                    self._socket.sendall(command)
                    
                    # レスポンスを受信
                    response = self._receive_response(self._socket)
                    return RESPParser.decode(response, self.config.decode_responses)
                    
                except (socket.error, socket.timeout) as e:
                    retries += 1
                    if retries > self.config.max_retries:
                        raise RedisCommandError(f"Command failed after {retries} retries: {e}")
                    if self.config.retry_on_timeout:
                        time.sleep(self.config.retry_delay)
                        try:
                            self._socket.close()
                            self._socket = self._create_socket()
                        except:
                            pass

    def _receive_response(self, sock: socket.socket) -> bytes:
        """ソケットからレスポンスを完全に受信"""
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
            # 完全なレスポンスが受信できたか確認
            if self._is_complete_response(response):
                break
        return response

    def _is_complete_response(self, data: bytes) -> bool:
        """RESPレスポンスが完全か確認"""
        if not data:
            return False
        
        text = data.decode("utf-8", errors="ignore")
        # 簡易チェック: CRLFで終わっているか
        if not text.endswith("\r\n"):
            return False
        
        prefix = text[0]
        if prefix in ("+", "-", ":"):
            return True
        elif prefix == "$":
            # Bulk string の場合、長さを確認
            try:
                lines = text.split("\r\n")
                length = int(lines[0][1:])
                if length == -1:
                    return True
                # データ部分 + CRLF があるか
                return len(lines) >= 2 and len(lines[1]) >= length
            except:
                return True
        elif prefix == "*":
            # Array の場合は複雑なので、CRLFで終わっていれば完了と見なす
            return True
        
        return True

    # ==================== キュー操作 ====================

    def rpush(self, key: str, *values: str) -> int:
        """
        リストの末尾に値を追加 (RPUSH)
        
        Args:
            key: リストのキー名
            *values: 追加する値（複数可）
            
        Returns:
            操作後のリストの長さ
        """
        return self._send_command("RPUSH", key, *values)

    def lpush(self, key: str, *values: str) -> int:
        """
        リストの先頭に値を追加 (LPUSH)
        
        Args:
            key: リストのキー名
            *values: 追加する値（複数可）
            
        Returns:
            操作後のリストの長さ
        """
        return self._send_command("LPUSH", key, *values)

    def blpop(self, *keys: str, timeout: int = 0) -> Optional[tuple[str, str]]:
        """
        ブロッキングでリストの先頭から値を取得 (BLPOP)
        
        Args:
            *keys: 監視するリストのキー名（複数可）
            timeout: タイムアウト秒数。0は無限待機
            
        Returns:
            (キー名, 値) のタプル、またはタイムアウト時は None
        """
        # BLPOPはブロッキングするのでタイムアウトを調整
        if self._socket:
            self._socket.settimeout(timeout + 5 if timeout > 0 else None)
        
        try:
            result = self._send_command("BLPOP", *keys, str(timeout))
            if result is None:
                return None
            return (result[0], result[1]) if isinstance(result, list) and len(result) >= 2 else None
        finally:
            if self._socket:
                self._socket.settimeout(self.config.socket_timeout)

    def brpop(self, *keys: str, timeout: int = 0) -> Optional[tuple[str, str]]:
        """
        ブロッキングでリストの末尾から値を取得 (BRPOP)
        
        Args:
            *keys: 監視するリストのキー名（複数可）
            timeout: タイムアウト秒数。0は無限待機
            
        Returns:
            (キー名, 値) のタプル、またはタイムアウト時は None
        """
        if self._socket:
            self._socket.settimeout(timeout + 5 if timeout > 0 else None)
        
        try:
            result = self._send_command("BRPOP", *keys, str(timeout))
            if result is None:
                return None
            return (result[0], result[1]) if isinstance(result, list) and len(result) >= 2 else None
        finally:
            if self._socket:
                self._socket.settimeout(self.config.socket_timeout)

    def llen(self, key: str) -> int:
        """
        リストの長さを取得 (LLEN)
        
        Args:
            key: リストのキー名
            
        Returns:
            リストの長さ
        """
        return self._send_command("LLEN", key)

    def lrange(self, key: str, start: int = 0, stop: int = -1) -> list[str]:
        """
        リストの指定範囲の値を取得 (LRANGE)
        
        Args:
            key: リストのキー名
            start: 開始インデックス
            stop: 終了インデックス（-1で最後まで）
            
        Returns:
            値のリスト
        """
        return self._send_command("LRANGE", key, str(start), str(stop))

    # ==================== Pub/Sub 操作 ====================

    def publish(self, channel: str, message: str) -> int:
        """
        チャンネルにメッセージを発行 (PUBLISH)
        
        Args:
            channel: チャンネル名
            message: 発行するメッセージ
            
        Returns:
            メッセージを受信したサブスクライバーの数
        """
        return self._send_command("PUBLISH", channel, message)

    def subscribe(
        self,
        *channels: str,
        callback: Callable[[str, str], None]
    ) -> None:
        """
        チャンネルを購読開始
        
        Args:
            *channels: 購読するチャンネル名（複数可）
            callback: メッセージ受信時のコールバック関数 (channel, message) -> None
            
        Note:
            購読は別スレッドで実行されます。
            停止するには unsubscribe() または close() を呼び出してください。
        """
        for channel in channels:
            self._pubsub_callbacks[channel] = callback
        
        if not self._pubsub_running:
            self._start_pubsub(channels)
        else:
            # 既存のPub/Sub接続にチャンネルを追加
            if self._pubsub_socket:
                command = RESPParser.encode("SUBSCRIBE", *channels)
                self._pubsub_socket.sendall(command)

    def unsubscribe(self, *channels: str) -> None:
        """
        チャンネルの購読を解除
        
        Args:
            *channels: 購読解除するチャンネル名。空の場合は全て解除
        """
        if channels:
            for channel in channels:
                self._pubsub_callbacks.pop(channel, None)
            if self._pubsub_socket:
                command = RESPParser.encode("UNSUBSCRIBE", *channels)
                self._pubsub_socket.sendall(command)
        else:
            self._pubsub_callbacks.clear()
            self._stop_pubsub()

    def _start_pubsub(self, channels: tuple[str, ...]) -> None:
        """Pub/Subスレッドを開始"""
        self._pubsub_socket = self._create_socket()
        self._pubsub_socket.settimeout(1.0)  # 短いタイムアウトでループを制御
        
        # SUBSCRIBEコマンドを送信
        command = RESPParser.encode("SUBSCRIBE", *channels)
        self._pubsub_socket.sendall(command)
        
        self._pubsub_running = True
        self._pubsub_thread = threading.Thread(target=self._pubsub_loop, daemon=True)
        self._pubsub_thread.start()

    def _stop_pubsub(self) -> None:
        """Pub/Subスレッドを停止"""
        self._pubsub_running = False
        if self._pubsub_thread and self._pubsub_thread.is_alive():
            self._pubsub_thread.join(timeout=2.0)

    def _pubsub_loop(self) -> None:
        """Pub/Subメッセージ受信ループ"""
        buffer = b""
        
        while self._pubsub_running and self._pubsub_socket:
            try:
                chunk = self._pubsub_socket.recv(4096)
                if not chunk:
                    continue
                
                buffer += chunk
                
                # メッセージをパース
                while buffer:
                    try:
                        text = buffer.decode("utf-8")
                        if not text.strip():
                            buffer = b""
                            break
                        
                        # Pub/Subメッセージは配列形式: ["message", channel, data]
                        result = RESPParser.decode(buffer)
                        if isinstance(result, list) and len(result) >= 3:
                            msg_type, channel, data = result[0], result[1], result[2]
                            if msg_type == "message" and channel in self._pubsub_callbacks:
                                try:
                                    self._pubsub_callbacks[channel](channel, data)
                                except Exception as e:
                                    pass  # コールバックのエラーは無視
                        
                        # 処理済みデータをバッファから除去
                        # 簡易実装: 一度パースできたらバッファをクリア
                        buffer = b""
                        
                    except Exception:
                        break
                        
            except socket.timeout:
                continue
            except Exception:
                if self._pubsub_running:
                    time.sleep(0.1)
                    continue
                break

    # ==================== ユーティリティ ====================

    def ping(self) -> bool:
        """
        Redis接続の確認
        
        Returns:
            接続が有効な場合はTrue
        """
        try:
            result = self._send_command("PING")
            return result == "PONG"
        except:
            return False

    def delete(self, *keys: str) -> int:
        """
        キーを削除 (DEL)
        
        Args:
            *keys: 削除するキー名（複数可）
            
        Returns:
            削除されたキーの数
        """
        return self._send_command("DEL", *keys)

    def exists(self, *keys: str) -> int:
        """
        キーの存在確認 (EXISTS)
        
        Args:
            *keys: 確認するキー名（複数可）
            
        Returns:
            存在するキーの数
        """
        return self._send_command("EXISTS", *keys)

    def expire(self, key: str, seconds: int) -> bool:
        """
        キーにTTLを設定 (EXPIRE)
        
        Args:
            key: キー名
            seconds: 有効期限（秒）
            
        Returns:
            設定が成功した場合はTrue
        """
        return self._send_command("EXPIRE", key, str(seconds)) == 1

    def __enter__(self) -> "RedisClient":
        """コンテキストマネージャのenter"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """コンテキストマネージャのexit"""
        self.close()
