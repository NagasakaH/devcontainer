#!/usr/bin/env python3
"""
オーケストレーション設定を取得するスクリプト

Usage:
    python get_config.py <session_prefix>

Examples:
    python get_config.py devcontainer-4c606c3024b0-001
"""

import argparse
import json
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
            # バルク文字列のレスポンスを完全に読み取る
            if response.startswith(b"$"):
                try:
                    first_line_end = response.index(b"\r\n")
                    length = int(response[1:first_line_end])
                    if length == -1:
                        break  # nil
                    expected_len = first_line_end + 2 + length + 2
                    if len(response) >= expected_len:
                        break
                except (ValueError, IndexError):
                    pass
            elif b"\r\n" in response:
                break

    return response.decode("utf-8").strip()


def get_config(host: str, port: int, session_prefix: str) -> dict:
    """オーケストレーション設定を取得"""
    config_key = f"{session_prefix}:config"
    response = send_redis_command(host, port, "GET", config_key)
    
    if response == "$-1":
        raise ValueError(f"Config not found: {config_key}")
    
    # バルク文字列からJSONを抽出
    if response.startswith("$"):
        first_line_end = response.index("\r\n")
        json_str = response[first_line_end + 2:]
        if json_str.endswith("\r\n"):
            json_str = json_str[:-2]
        return json.loads(json_str)
    
    raise ValueError(f"Unexpected response: {response}")


def main():
    parser = argparse.ArgumentParser(
        description="オーケストレーション設定を取得",
    )
    parser.add_argument(
        "session_prefix",
        help="セッションプレフィックス (例: devcontainer-4c606c3024b0-001)",
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
        "--json",
        action="store_true",
        help="JSON形式で出力",
    )

    args = parser.parse_args()

    try:
        config = get_config(args.host, args.port, args.session_prefix)
        
        if args.json:
            print(json.dumps(config, ensure_ascii=False, indent=2))
        else:
            print(f"セッション: {config['prefix']}")
            print(f"セッションID: {config['session_id']}")
            print(f"最大子数: {config['max_children']}")
            print(f"作成日時: {config['created_at']}")
            print()
            print("リスト/ストリーム:")
            print(f"  親→子: {', '.join(config['parent_to_child_lists'][:3])}...")
            print(f"  子→親: {', '.join(config['child_to_parent_lists'][:3])}...")
            print(f"  状態: {config['status_stream']}")
            print(f"  結果: {config['result_stream']}")
            print(f"  制御: {config['control_list']}")

    except ConnectionRefusedError:
        print(f"✗ Error: Cannot connect to Redis at {args.host}:{args.port}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
