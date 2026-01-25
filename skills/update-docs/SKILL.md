---
name: update-docs
description: ドキュメント更新ガイド。ソースコードの信頼できる情報源（Single Source of Truth）からドキュメントを同期・更新する。package.json、pyproject.toml、.csprojなどから自動的にドキュメントを生成し、古いドキュメントを特定する。「ドキュメント更新」「docs更新」「ドキュメント同期」などのフレーズで発動。
variables:
  language: auto  # auto | typescript | python | csharp
---

# ドキュメント更新（Update Documentation）

信頼できる情報源からドキュメントを同期・更新するためのガイド。

## このスキルの目的

ソースコードの信頼できる情報源（Single Source of Truth）からドキュメントを自動的に生成・更新し、ドキュメントとコードの整合性を保つ。

---

## 🌐 言語自動検出

`{{language}}` が `auto` の場合、以下の順序でプロジェクトの言語を検出する：

1. **メタデータファイルの存在確認:**
   - `package.json` or `tsconfig.json` → TypeScript/Node.js
   - `pyproject.toml`, `setup.py`, or `requirements.txt` → Python
   - `*.csproj`, `*.sln`, or `global.json` → C#/.NET

2. **ユーザーの指定:** ユーザーが明示的に言語を指定した場合はそれを使用

3. **デフォルト:** TypeScript/Node.js

---

## 信頼できる情報源（言語別）

| 言語 | メタデータファイル | スクリプト | 依存関係 |
|------|-------------------|------------|----------|
| **TypeScript/Node.js** | `package.json` | `scripts` セクション | `dependencies`, `devDependencies` |
| **Python** | `pyproject.toml` / `setup.py` | `[project.scripts]`, `[tool.poetry.scripts]` | `[project.dependencies]` |
| **C#/.NET** | `*.csproj` | `dotnet` コマンド, MSBuild ターゲット | `PackageReference` 要素 |

### 言語別リファレンス

- [📦 TypeScript/Node.js メタデータガイド](./reference/typescript/typescript_metadata.md)
- [🐍 Python メタデータガイド](./reference/python/python_metadata.md)
- [🔷 C# メタデータガイド](./reference/csharp/csharp_metadata.md)

## ワークフロー

### ステップ1: メタデータファイルを読み取る

言語を検出し、適切なメタデータファイルからスクリプトと依存関係を抽出する。

#### TypeScript/Node.js の場合

`package.json` の `scripts` セクションから以下を生成する：

```markdown
## 利用可能なスクリプト

| スクリプト | 説明 |
|-----------|------|
| `npm run build` | プロジェクトをビルド |
| `npm run test` | テストを実行 |
| `npm run lint` | リンターを実行 |
```

#### Python の場合

`pyproject.toml` または `setup.py` からスクリプトを抽出する：

```markdown
## 利用可能なスクリプト

| スクリプト | 説明 |
|-----------|------|
| `poetry run my-cli` | CLI ツールを実行 |
| `pytest` | テストを実行 |
| `black .` | コードフォーマット |
```

#### C#/.NET の場合

標準的な `dotnet` コマンドとカスタムターゲットを抽出する：

```markdown
## 利用可能なコマンド

| コマンド | 説明 |
|----------|------|
| `dotnet build` | プロジェクトをビルド |
| `dotnet test` | テストを実行 |
| `dotnet run` | アプリケーションを実行 |
```

### ステップ2: .env.example を読み取る

`.env.example` から以下を抽出する：

- すべての環境変数を抽出
- 目的と形式をドキュメント化

```markdown
## 環境変数

| 変数名 | 説明 | 形式 |
|--------|------|------|
| `DATABASE_URL` | データベース接続文字列 | `postgresql://...` |
| `API_KEY` | API認証キー | 文字列 |
```

### ステップ3: docs/CONTRIB.md を生成

以下の内容を含むコントリビューションガイドを生成する：

- 開発ワークフロー
- 利用可能なスクリプト
- 環境セットアップ
- テスト手順

### ステップ4: docs/RUNBOOK.md を生成

以下の内容を含む運用手順書を生成する：

- デプロイ手順
- 監視とアラート
- よくある問題と解決策
- ロールバック手順

### ステップ5: 古いドキュメントの特定

陳腐化したドキュメントを特定する：

- 90日以上更新されていないドキュメントを検索
- 手動レビュー用にリストアップ

```bash
# 90日以上更新されていないドキュメントを検索
find docs -name "*.md" -mtime +90 -type f
```

### ステップ6: 差分サマリーを表示

更新内容の差分サマリーを表示する：

- 追加・変更・削除された内容
- 影響を受けるファイル

## ドキュメントテンプレート

### CONTRIB.md テンプレート（言語別）

#### TypeScript/Node.js

```markdown
# コントリビューションガイド

## 開発環境のセットアップ

1. リポジトリをクローン
2. 依存関係をインストール: `npm install`
3. 環境変数を設定: `.env.example` を `.env` にコピー

## 開発ワークフロー

### 利用可能なスクリプト

{package.json scripts から自動生成}

## テスト

`npm test` を実行

## 環境変数

{.env.example から自動生成}
```

#### Python

```markdown
# コントリビューションガイド

## 開発環境のセットアップ

1. リポジトリをクローン
2. 仮想環境を作成: `python -m venv .venv`
3. 仮想環境を有効化: `source .venv/bin/activate`
4. 依存関係をインストール: `pip install -e ".[dev]"` または `poetry install`
5. 環境変数を設定: `.env.example` を `.env` にコピー

## 開発ワークフロー

### 利用可能なスクリプト

{pyproject.toml scripts から自動生成}

## テスト

`pytest` を実行

## 環境変数

{.env.example から自動生成}
```

#### C#/.NET

```markdown
# コントリビューションガイド

## 開発環境のセットアップ

1. リポジトリをクローン
2. 依存関係を復元: `dotnet restore`
3. 環境変数を設定: `appsettings.Development.json` または `.env`

## 開発ワークフロー

### 利用可能なコマンド

| コマンド | 説明 |
|----------|------|
| `dotnet build` | プロジェクトをビルド |
| `dotnet test` | テストを実行 |
| `dotnet run` | アプリケーションを実行 |
| `dotnet watch run` | ホットリロード付きで実行 |

## テスト

`dotnet test` を実行

## 環境変数

{appsettings.json から自動生成}
```

### RUNBOOK.md テンプレート

```markdown
# 運用手順書（Runbook）

## デプロイ手順

### 本番環境へのデプロイ
{デプロイ手順}

### ステージング環境へのデプロイ
{デプロイ手順}

## 監視とアラート

### 監視項目
- {監視項目1}
- {監視項目2}

### アラート対応
{アラート対応手順}

## よくある問題と解決策

### 問題1: {問題の説明}
**症状**: {症状}
**原因**: {原因}
**解決策**: {解決策}

## ロールバック手順

### 即座のロールバック
{ロールバック手順}

### データベースのロールバック
{データベースロールバック手順}
```

## 重要な注意事項

1. **信頼できる情報源を優先**: ドキュメントはメタデータファイル（`package.json`, `pyproject.toml`, `*.csproj` など）と `.env.example` の内容を反映する
2. **言語の自動検出**: プロジェクトの言語を自動検出し、適切なリファレンスを参照する
3. **定期的な同期**: コード変更後はドキュメントも更新する
4. **古いドキュメントの管理**: 90日以上更新されていないドキュメントはレビュー対象
5. **差分の確認**: 更新前に必ず差分を確認し、意図しない変更がないか確認する
