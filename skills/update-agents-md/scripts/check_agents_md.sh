#!/bin/bash
# AGENTS.md/CLAUDE.mdの状態を確認するスクリプト
#
# 使い方:
#   ./check_agents_md.sh [リポジトリルート]
#
# 引数なしの場合はカレントディレクトリを使用

set -e

REPO_ROOT="${1:-.}"

echo "=== AGENTS.md/CLAUDE.md 状態確認 ==="
echo "リポジトリルート: $REPO_ROOT"
echo ""

AGENTS_FILE="$REPO_ROOT/AGENTS.md"
CLAUDE_FILE="$REPO_ROOT/CLAUDE.md"

# AGENTS.mdの確認
if [ -f "$AGENTS_FILE" ]; then
    echo "✅ AGENTS.md: 存在します"
    echo "   サイズ: $(wc -c < "$AGENTS_FILE") bytes"
    echo "   行数: $(wc -l < "$AGENTS_FILE") lines"
else
    echo "❌ AGENTS.md: 存在しません"
fi
echo ""

# CLAUDE.mdの確認
if [ -L "$CLAUDE_FILE" ]; then
    TARGET=$(readlink "$CLAUDE_FILE")
    if [ "$TARGET" = "AGENTS.md" ]; then
        echo "✅ CLAUDE.md: AGENTS.mdへのシンボリックリンクです"
    else
        echo "⚠️ CLAUDE.md: シンボリックリンクですが、対象が異なります ($TARGET)"
    fi
elif [ -f "$CLAUDE_FILE" ]; then
    echo "⚠️ CLAUDE.md: 通常ファイルとして存在します（シンボリックリンクではありません）"
    echo "   サイズ: $(wc -c < "$CLAUDE_FILE") bytes"
else
    echo "❌ CLAUDE.md: 存在しません"
fi
echo ""

# 推奨アクション
echo "=== 推奨アクション ==="
if [ ! -f "$AGENTS_FILE" ]; then
    echo "- AGENTS.mdを作成してください"
fi

if [ ! -L "$CLAUDE_FILE" ] && [ -f "$CLAUDE_FILE" ]; then
    echo "- CLAUDE.mdをシンボリックリンクに変換することを推奨します:"
    echo "    mv $CLAUDE_FILE ${CLAUDE_FILE}.bak"
    echo "    ln -s AGENTS.md $CLAUDE_FILE"
fi

if [ ! -f "$CLAUDE_FILE" ] && [ -f "$AGENTS_FILE" ]; then
    echo "- CLAUDE.mdをシンボリックリンクとして作成してください:"
    echo "    ln -s AGENTS.md $CLAUDE_FILE"
fi

if [ -f "$AGENTS_FILE" ] && [ -L "$CLAUDE_FILE" ]; then
    TARGET=$(readlink "$CLAUDE_FILE")
    if [ "$TARGET" = "AGENTS.md" ]; then
        echo "✅ 設定は正常です"
    fi
fi
