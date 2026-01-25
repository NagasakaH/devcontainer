---
name: build-fix
description: ビルドエラーを段階的に修正するワークフロー。TypeScript、Python、C#などのビルド・コンパイルエラー修正時に使用。「ビルドエラーを直して」「コンパイルが通らない」「TSエラーを修正」「型エラーを修正」などのフレーズでトリガーされる。
---

# ビルド＆修正

TypeScript、Python、C# などのビルドエラーを段階的に修正するワークフロー。

## 言語自動検出

プロジェクトのファイル構成から言語を自動検出します：

| 検出条件 | 言語 |
|----------|------|
| `package.json` + `.ts`/`.tsx`ファイルが存在 | TypeScript |
| `pyproject.toml` または `requirements.txt` が存在 | Python |
| `.csproj` または `.sln` が存在 | C# |

言語が検出できない場合は、ユーザーに確認してください。

## ワークフロー

### 1. ビルドを実行

言語・プロジェクト構成に応じてコマンドを実行：

#### TypeScript/JavaScript

```bash
npm run build
# または
pnpm build
yarn build

# 型チェックのみ
npx tsc --noEmit
```

#### Python

```bash
# 型チェック（mypyを使用）
mypy src/

# 厳格モード
mypy --strict src/

# リントチェック
ruff check src/

# パッケージビルド
python -m build
```

#### C#

```bash
# 基本的なビルド
dotnet build

# Releaseビルド
dotnet build -c Release

# 警告をエラーとして扱う
dotnet build /warnaserror
```

> 📖 詳細なコマンドオプションは `reference/{language}/commands.md` を参照してください。

### 2. エラー出力を解析

- ファイルごとにグループ化
- 重要度順にソート

### 3. 各エラーを修正

1つずつ順番に修正する：

1. **エラーコンテキストを表示** - 前後5行を含めて確認
2. **問題を説明** - 何が原因かを特定
3. **修正案を提示** - 解決方法を検討
4. **修正を適用** - コードを変更
5. **ビルドを再実行** - 修正結果を確認
6. **エラー解消を確認** - 新たな問題がないか検証

### 4. 停止条件

以下の場合は修正を中断する：

- 修正が新たなエラーを引き起こした場合
- 同じエラーが3回の試行後も解消しない場合
- ユーザーが一時停止を要求した場合

### 5. サマリーを表示

修正完了後、以下を報告：

- ✅ 修正したエラーの数
- ⚠️ 残っているエラーの数
- ❌ 新たに発生したエラーの数

## 重要な原則

**安全のため、エラーは1つずつ修正すること！**

複数のエラーを一度に修正しようとすると：

- どの修正がどのエラーに対応するか追跡が困難になる
- 修正同士が干渉する可能性がある
- 新たなエラーの原因特定が難しくなる

## 言語別リファレンス

より詳細な情報は、各言語のリファレンスを参照してください：

- [TypeScript リファレンス](reference/typescript/commands.md)
- [Python リファレンス](reference/python/commands.md)
- [C# リファレンス](reference/csharp/commands.md)
