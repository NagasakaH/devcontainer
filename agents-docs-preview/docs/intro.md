---
sidebar_position: 1
---

# Agents Docs Preview

AIエージェントが生成したドキュメントのプレビューサイトへようこそ。

## 概要

このサイトでは、AIエージェントによって自動生成されたドキュメントをプレビューできます。

## ドキュメントの追加

新しいドキュメントを追加するには、`docs/` ディレクトリにMarkdownファイルを配置してください。

### ファイル形式

```markdown
---
sidebar_position: 1
---

# ドキュメントタイトル

ドキュメントの内容...
```

## 開発サーバーの起動

```bash
cd agents-docs-preview
npm run start
```

サイトは http://localhost:3000/ で確認できます。
