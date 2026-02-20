#!/usr/bin/env python3
"""
GitLab MCP Skill Executor
=========================
Handles dynamic communication with the GitLab MCP server.
Reads GITLAB_TOKEN from environment, falls back to user prompt.
"""

import json
import sys
import os
import asyncio
import argparse
from pathlib import Path

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    HAS_MCP = True
except ImportError:
    HAS_MCP = False


def get_gitlab_token():
    """Get GitLab token from environment or prompt user."""
    token = os.environ.get("GITLAB_TOKEN")
    if token:
        return token
    # Fallback: prompt user
    print("GITLAB_TOKEN environment variable not set.", file=sys.stderr)
    print("Please enter your GitLab Personal Access Token:", file=sys.stderr)
    token = input().strip()
    if not token:
        print("Error: No token provided.", file=sys.stderr)
        sys.exit(1)
    return token


class MCPExecutor:
    """Execute MCP tool calls dynamically."""

    def __init__(self, server_config):
        if not HAS_MCP:
            raise ImportError("mcp package is required. Install with: pip install mcp")
        self.server_config = server_config
        self.session = None
        self._client_cm = None
        self._session_cm = None

    async def connect(self):
        """Connect to MCP server."""
        token = get_gitlab_token()
        env = dict(self.server_config.get("env", {}))
        env["GITLAB_PERSONAL_ACCESS_TOKEN"] = token
        # Inherit PATH for npx
        env["PATH"] = os.environ.get("PATH", "")
        # Propagate GITLAB_API_URL from environment if set
        api_url = os.environ.get("GITLAB_API_URL")
        if api_url:
            env["GITLAB_API_URL"] = api_url

        server_params = StdioServerParameters(
            command=self.server_config["command"],
            args=self.server_config.get("args", []),
            env=env,
        )

        self._client_cm = stdio_client(server_params)
        read_stream, write_stream = await self._client_cm.__aenter__()
        self._session_cm = ClientSession(read_stream, write_stream)
        self.session = await self._session_cm.__aenter__()
        await self.session.initialize()

    async def list_tools(self):
        """Get list of available tools."""
        if not self.session:
            await self.connect()
        response = await self.session.list_tools()
        return [{"name": tool.name, "description": tool.description} for tool in response.tools]

    async def describe_tool(self, tool_name: str):
        """Get detailed schema for a specific tool."""
        if not self.session:
            await self.connect()
        response = await self.session.list_tools()
        for tool in response.tools:
            if tool.name == tool_name:
                return {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema,
                }
        return None

    async def call_tool(self, tool_name: str, arguments: dict):
        """Execute a tool call."""
        if not self.session:
            await self.connect()
        response = await self.session.call_tool(tool_name, arguments)
        return response.content

    async def close(self):
        """Close MCP connection."""
        if self._session_cm:
            try:
                await self._session_cm.__aexit__(None, None, None)
            except Exception:
                pass
        if self._client_cm:
            try:
                await self._client_cm.__aexit__(None, None, None)
            except Exception:
                pass


async def main():
    parser = argparse.ArgumentParser(description="GitLab MCP Skill Executor")
    parser.add_argument("--call", help="JSON tool call to execute")
    parser.add_argument("--describe", help="Get tool schema by name")
    parser.add_argument("--list", action="store_true", help="List all tools")

    args = parser.parse_args()

    config_path = Path(__file__).parent.parent / "mcp-config.json"
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    if not HAS_MCP:
        print("Error: mcp package not installed", file=sys.stderr)
        print("Install with: pip install mcp", file=sys.stderr)
        sys.exit(1)

    executor = MCPExecutor(config)

    try:
        if args.list:
            tools = await executor.list_tools()
            print(json.dumps(tools, indent=2))

        elif args.describe:
            schema = await executor.describe_tool(args.describe)
            if schema:
                print(json.dumps(schema, indent=2))
            else:
                print(f"Tool not found: {args.describe}", file=sys.stderr)
                sys.exit(1)

        elif args.call:
            call_data = json.loads(args.call)
            result = await executor.call_tool(
                call_data["tool"], call_data.get("arguments", {})
            )
            if isinstance(result, list):
                for item in result:
                    if hasattr(item, "text"):
                        print(item.text)
                    else:
                        print(json.dumps(
                            item.__dict__ if hasattr(item, "__dict__") else item,
                            indent=2,
                        ))
            else:
                print(json.dumps(
                    result.__dict__ if hasattr(result, "__dict__") else result,
                    indent=2,
                ))
        else:
            parser.print_help()

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
    finally:
        await executor.close()


if __name__ == "__main__":
    asyncio.run(main())
