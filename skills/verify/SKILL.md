---
name: verify
description: コードベースの包括的な検証を実行するスキル。ビルドチェック、型チェック、リントチェック、テスト実行、console.log監査、Git状態確認を順番に実行し、PR準備状況をレポートする。「検証」「verify」「ビルド確認」「型チェック」「テスト実行」「PR準備」などのフレーズでトリガーされる。
---

# 検証コマンド

現在のコードベース状態に対して包括的な検証を実行する。

## 実行手順

以下の順序で検証を実行すること：

1. **ビルドチェック**
   - プロジェクトのビルドコマンドを実行
   - 失敗した場合、エラーを報告して**停止**

2. **型チェック**
   - TypeScript/型チェッカーを実行
   - すべてのエラーを `ファイル名:行番号` 形式で報告

3. **リントチェック**
   - リンターを実行
   - 警告とエラーを報告

4. **テストスイート**
   - すべてのテストを実行
   - 成功/失敗の件数を報告
   - カバレッジのパーセンテージを報告

5. **console.log監査**
   - ソースファイル内のconsole.logを検索
   - 検出箇所を報告

6. **Git状態**
   - コミットされていない変更を表示
   - 最後のコミット以降に変更されたファイルを表示

## 出力形式

簡潔な検証レポートを生成すること：

```
検証結果: [合格/不合格]

ビルド:     [OK/失敗]
型チェック: [OK/X件のエラー]
リント:     [OK/X件の問題]
テスト:     [X/Y件 合格, カバレッジZ%]
シークレット: [OK/X件 検出]
ログ出力:   [OK/X件のconsole.log]

PR準備完了: [はい/いいえ]
```

重大な問題がある場合は、修正提案と共にリストアップすること。

## 引数

`{ARGUMENTS}` には以下を指定可能：

| 引数 | 説明 |
|------|------|
| `quick` | ビルド + 型チェックのみ実行 |
| `full` | すべてのチェックを実行（デフォルト） |
| `pre-commit` | コミット前に必要なチェックを実行 |
| `pre-pr` | すべてのチェック + セキュリティスキャンを実行 |

## プロジェクト別コマンド例

### Node.js/TypeScript プロジェクト

```bash
# ビルド
npm run build

# 型チェック
npx tsc --noEmit

# リント
npm run lint

# テスト
npm test -- --coverage
```

### Python プロジェクト

```bash
# 型チェック
mypy .

# リント
ruff check .

# テスト
pytest --cov
```

### Go プロジェクト

```bash
# ビルド
go build ./...

# リント
golangci-lint run

# テスト
go test -cover ./...
```

## console.log検索パターン

```bash
# TypeScript/JavaScript
grep -rn "console\.log" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" src/

# Python (print文)
grep -rn "print(" --include="*.py" src/
```

## Git状態確認

```bash
# 未コミットの変更
git status --short

# 最後のコミットからの差分
git diff --stat HEAD~1
```
