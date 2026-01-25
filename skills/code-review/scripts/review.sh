#!/bin/bash
# code-review スキル用の簡易レビュースクリプト
# コミットされていない変更に対して基本的なチェックを実行します

set -e

echo "=== コードレビュー開始 ==="
echo ""

# 変更されたファイルを取得
CHANGED_FILES=$(git diff --name-only HEAD 2>/dev/null || echo "")
STAGED_FILES=$(git diff --cached --name-only 2>/dev/null || echo "")

ALL_FILES=$(echo -e "${CHANGED_FILES}\n${STAGED_FILES}" | sort -u | grep -v '^$' || true)

if [ -z "$ALL_FILES" ]; then
    echo "✓ 変更されたファイルはありません"
    exit 0
fi

echo "変更されたファイル:"
echo "$ALL_FILES" | while read -r file; do
    [ -n "$file" ] && echo "  - $file"
done
echo ""

# カウンター初期化
CRITICAL_COUNT=0
HIGH_COUNT=0
MEDIUM_COUNT=0

echo "=== セキュリティチェック（CRITICAL）==="

# ハードコードされた認証情報のチェック
for file in $ALL_FILES; do
    if [ -f "$file" ]; then
        # APIキー、シークレット、パスワードのパターン
        if grep -nE "(api[_-]?key|secret|password|token|credential)\s*[:=]\s*['\"][^'\"]+['\"]" "$file" 2>/dev/null; then
            echo "⚠️  CRITICAL: $file にハードコードされた認証情報の可能性"
            ((CRITICAL_COUNT++)) || true
        fi
    fi
done

echo ""
echo "=== コード品質チェック（HIGH）==="

# console.log のチェック（JavaScriptファイル）
for file in $ALL_FILES; do
    if [ -f "$file" ] && [[ "$file" =~ \.(js|ts|jsx|tsx)$ ]]; then
        if grep -n "console\.log" "$file" 2>/dev/null; then
            echo "⚠️  HIGH: $file に console.log が残存"
            ((HIGH_COUNT++)) || true
        fi
    fi
done

# TODO/FIXME のチェック
for file in $ALL_FILES; do
    if [ -f "$file" ]; then
        if grep -nE "(TODO|FIXME)" "$file" 2>/dev/null; then
            echo "ℹ️  MEDIUM: $file に TODO/FIXME コメント"
            ((MEDIUM_COUNT++)) || true
        fi
    fi
done

echo ""
echo "=== レビュー結果 ==="
echo "CRITICAL: $CRITICAL_COUNT"
echo "HIGH: $HIGH_COUNT"
echo "MEDIUM: $MEDIUM_COUNT"
echo ""

if [ $CRITICAL_COUNT -gt 0 ]; then
    echo "❌ CRITICAL な問題が見つかりました。コミット前に修正してください。"
    exit 1
elif [ $HIGH_COUNT -gt 0 ]; then
    echo "⚠️  HIGH な問題が見つかりました。修正を推奨します。"
    exit 0
else
    echo "✓ 重大な問題は見つかりませんでした"
    exit 0
fi
