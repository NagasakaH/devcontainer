#!/bin/bash
# Redis Agent Monitor 起動スクリプト (TUI版)
#
# Usage:
#   ./run_monitor.sh
#
# 終了: q または Ctrl+C

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

echo "🚀 Redis Agent Monitor (TUI) を起動します..."
echo "   終了するには 'q' キーを押すか Ctrl+C"
echo ""

# 仮想環境のpythonでTUIアプリを起動
.venv/bin/python -m app.monitor.tui_main
