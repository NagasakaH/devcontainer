---
name: test-coverage
description: テストカバレッジ分析と不足テストの生成ガイド。カバレッジレポートを分析し、カバレッジが低いファイルを特定し、不足しているテストを生成する。「カバレッジを上げて」「テストカバレッジ」「未テストのコードにテストを追加」「80%カバレッジを達成」などのフレーズで発動。
---

# テストカバレッジ分析（Test Coverage）

テストカバレッジを分析し、不足しているテストを生成するためのガイド。

## このスキルの目的

1. **カバレッジの測定** - 現在のテストカバレッジを把握
2. **不足箇所の特定** - カバレッジが低いファイル・関数を洗い出す
3. **テストの生成** - 不足しているテストを自動生成
4. **目標達成の確認** - 80%以上のカバレッジを目指す

## 言語自動検出

プロジェクトのファイル構成から言語を自動検出します：

| 検出条件 | 言語 |
|----------|------|
| `package.json` + `.ts`/`.tsx`ファイルが存在 | TypeScript |
| `pyproject.toml` または `requirements.txt` が存在 | Python |
| `.csproj` または `.sln` が存在 | C# |

言語が検出できない場合は、ユーザーに確認してください。

## ワークフロー

### ステップ1: カバレッジ付きでテストを実行

プロジェクトの言語・パッケージマネージャーに応じてコマンドを実行：

#### TypeScript/JavaScript

```bash
# npm
npm test -- --coverage

# pnpm
pnpm test --coverage

# yarn
yarn test --coverage
```

#### Python

```bash
# pytest + coverage.py（推奨）
pytest --cov --cov-report=term-missing

# JSON形式でレポート生成
pytest --cov --cov-report=json

# poetryプロジェクト
poetry run pytest --cov --cov-report=term-missing
```

#### C#

```bash
# dotnet test + Coverlet
dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=cobertura

# JSON形式で出力
dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=json
```

> 📖 詳細なコマンドオプションは `reference/{language}/commands.md` を参照してください。

### ステップ2: カバレッジレポートを分析

言語ごとのカバレッジレポートを確認し、以下を把握：

#### レポートファイルのパス

| 言語 | 形式 | パス |
|------|------|------|
| TypeScript | JSON Summary | `coverage/coverage-summary.json` |
| TypeScript | LCOV | `coverage/lcov.info` |
| Python | JSON | `coverage.json` |
| Python | HTML | `htmlcov/index.html` |
| C# | Cobertura | `coverage.cobertura.xml` |
| C# | JSON | `coverage.json` |

#### 確認項目

- 全体のカバレッジ率
- ファイルごとのカバレッジ率
- 行カバレッジ、分岐カバレッジ、関数カバレッジ

### ステップ3: 80%未満のファイルを特定

カバレッジ閾値（80%）を下回るファイルをリストアップ：

- 優先度の高いファイル（ビジネスロジック、ユーティリティ）を優先
- テスト不要なファイル（設定ファイル、型定義等）は除外を検討

### ステップ4: 各ファイルのテストを生成

カバレッジが低いファイルごとに以下を実施：

1. **未テストのコードパスを分析**
   - カバーされていない行を特定
   - 分岐条件の未テスト部分を確認

2. **ユニットテストを生成**
   - 個々の関数のテスト
   - 入力と出力の検証

3. **統合テストを生成**（該当する場合）
   - API エンドポイントのテスト
   - モジュール間の連携テスト

4. **E2Eテストを生成**（重要なフローの場合）
   - ユーザーの操作フローのテスト
   - クリティカルパスの検証

### ステップ5: 新しいテストの検証

生成したテストが正常に動作することを確認：

#### TypeScript

```bash
npm test
```

#### Python

```bash
pytest
```

#### C#

```bash
dotnet test
```

### ステップ6: Before/After メトリクスを表示

改善前後のカバレッジを比較表示：

```markdown
| 指標 | Before | After | 変化 |
|------|--------|-------|------|
| 行カバレッジ | 65% | 85% | +20% |
| 分岐カバレッジ | 50% | 78% | +28% |
| 関数カバレッジ | 70% | 90% | +20% |
```

### ステップ7: 目標達成の確認

プロジェクト全体で80%以上のカバレッジを達成していることを確認。

## テスト生成の重点項目

テストを生成する際は、以下のシナリオを重点的にカバー：

### 正常系（Happy Path）

- 期待される入力での正常動作
- 典型的なユースケース

### エラーハンドリング

- 例外のスロー
- エラーメッセージの検証
- エラー時のリカバリー動作

### エッジケース

- `null` / `undefined` / `None` の入力
- 空の配列・オブジェクト・リスト・辞書
- 空文字列

### 境界条件

- 最小値・最大値
- 配列の先頭・末尾
- 数値の境界（0、負数、オーバーフロー）

## 重要な注意事項

- **テストの品質を優先**: カバレッジ数値だけでなく、意味のあるテストを書く
- **モックの適切な使用**: 外部依存はモック化し、テストを独立させる
- **テストの可読性**: テスト名は何をテストしているか明確に記述

## 言語別リファレンス

より詳細な情報は、各言語のリファレンスを参照してください：

- [TypeScript リファレンス](reference/typescript/commands.md)
- [Python リファレンス](reference/python/commands.md)
- [C# リファレンス](reference/csharp/commands.md)
