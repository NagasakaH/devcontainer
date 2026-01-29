#!/usr/bin/env python3
"""
オーケストレーションセッションをクリーンアップするスクリプト

Usage:
    python cleanup.py <session_prefix>
    python cleanup.py --list-all  # 全セッションをリスト

Examples:
    python cleanup.py devcontainer-4c606c3024b0-001
"""

import argparse
import socket
import sys


def send_redis_command(host: str, port: int, *args: str) -> str:
    """RESPプロトコルでRedisコマンドを送信"""
    cmd_parts = [f"*{len(args)}"]
    for arg in args:
        encoded = arg.encode("utf-8")
        cmd_parts.append(f"${len(encoded)}")
        cmd_parts.append(arg)
    command = "\r\n".join(cmd_parts) + "\r\n"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(10)
        sock.connect((host, port))
        sock.sendall(command.encode("utf-8"))

        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
            if b"\r\n" in response:
                # 配列レスポンスの場合は完全に読み取る
                if response.startswith(b"*"):
                    # 簡易的な完了判定
                    import time
                    sock.settimeout(0.5)
                    try:
                        more = sock.recv(4096)
                        response += more
                    except socket.timeout:
                        break
                else:
                    break

    return response.decode("utf-8").strip()


def parse_array_response(response: str) -> list[str]:
    """Redis配列レスポンスをパース"""
    if response == "*0":
        return []
    
    lines = response.split("\r\n")
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("$"):
            # 次の行がデータ
            if i + 1 < len(lines):
                result.append(lines[i + 1])
                i += 2
            else:
                i += 1
        else:
            i += 1
    return result


def list_sessions(host: str, port: int, prefix_pattern: str = "*") -> list[str]:
    """オーケストレーションセッション一覧を取得"""
    response = send_redis_command(host, port, "KEYS", f"{prefix_pattern}:config")
    keys = parse_array_response(response)
    # :config を除去してプレフィックスのみ返す
    return [k.replace(":config", "") for k in keys]


def cleanup_session(host: str, port: int, session_prefix: str) -> int:
    """セッションの全キーを削除"""
    # このセッションに関連する全キーを検索
    response = send_redis_command(host, port, "KEYS", f"{session_prefix}:*")
    keys = parse_array_response(response)
    
    if not keys:
        return 0
    
    # 各キーを削除
    for key in keys:
        send_redis_command(host, port, "DEL", key)
    
    return len(keys)


def main():
    parser = argparse.ArgumentParser(
        description="オーケストレーションセッションをクリーンアップ",
    )
    parser.add_argument(
        "session_prefix",
        nargs="?",
        help="削除するセッションプレフィックス",
    )
    parser.add_argument(
        "--host",
        default="redis",
        help="Redisホスト (default: redis)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=6379,
        help="Redisポート (default: 6379)",
    )
    parser.add_argument(
        "--list-all",
        action="store_true",
        help="全セッションをリスト",
    )
    parser.add_argument(
        "--cleanup-all",
        action="store_true",
        help="全セッションを削除（危険）",
    )

    args = parser.parse_args()

    try:
        if args.list_all:
            sessions = list_sessions(args.host, args.port)
            if sessions:
                print(f"アクティブなセッション ({len(sessions)}):")
                for s in sorted(sessions):
                    print(f"  - {s}")
            else:
                print("アクティブなセッションはありません")
            return
        
        if args.cleanup_all:
            sessions = list_sessions(args.host, args.port)
            total = 0
            for session in sessions:
                count = cleanup_session(args.host, args.port, session)
                print(f"  Deleted {count} keys for {session}")
                total += count
            print(f"✓ 合計 {total} キーを削除しました")
            return
        
        if not args.session_prefix:
            parser.error("session_prefix が必要です（または --list-all を使用）")
        
        count = cleanup_session(args.host, args.port, args.session_prefix)
        if count > 0:
            print(f"✓ {count} キーを削除しました: {args.session_prefix}")
        else:
            print(f"セッションが見つかりません: {args.session_prefix}")

    except ConnectionRefusedError:
        print(f"✗ Error: Cannot connect to Redis at {args.host}:{args.port}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
