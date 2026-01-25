---
sidebar_position: 1769331678
date: 2026-01-25T09:01:18+00:00
---

# TypeScript - デッドコード検出ツール

## 推奨ツール

| ツール | 検出対象 | インストール |
|--------|----------|--------------|
| knip | 未使用エクスポート・ファイル | `npm install -D knip` |
| ts-prune | 未使用TypeScriptエクスポート | `npm install -D ts-prune` |
| depcheck | 未使用依存関係 | `npm install -D depcheck` |
| eslint-plugin-unused-imports | 未使用インポート | `npm install -D eslint-plugin-unused-imports` |

## コマンド例

### knip（推奨）

```bash
# プロジェクト全体をスキャン
npx knip

# 設定ファイルを指定
npx knip --config knip.json

# 特定の項目のみチェック
npx knip --include files,exports,dependencies

# 自動修正（未使用エクスポートの削除）
npx knip --fix
```

### ts-prune

```bash
# 未使用エクスポートをリスト
npx ts-prune

# プロジェクトパスを指定
npx ts-prune -p tsconfig.json

# エラーとして扱う（CI用）
npx ts-prune --error
```

### depcheck

```bash
# 未使用依存関係をチェック
npx depcheck

# 特定のパーサーを無視
npx depcheck --ignores="@types/*"

# JSON形式で出力
npx depcheck --json
```

### ESLint（未使用インポート）

```bash
# 未使用インポートをチェック
npx eslint . --rule 'unused-imports/no-unused-imports: error'

# 自動修正
npx eslint . --rule 'unused-imports/no-unused-imports: error' --fix
```

## 設定ファイル例

### knip.json（推奨）

```json
{
  "$schema": "https://unpkg.com/knip@latest/schema.json",
  "entry": ["src/index.ts", "src/main.ts"],
  "project": ["src/**/*.ts"],
  "ignore": [
    "**/*.test.ts",
    "**/*.spec.ts",
    "**/__tests__/**"
  ],
  "ignoreDependencies": [
    "@types/*"
  ],
  "ignoreExportsUsedInFile": true
}
```

### package.json（knip設定埋め込み）

```json
{
  "knip": {
    "entry": ["src/index.ts"],
    "project": ["src/**/*.ts"],
    "ignore": ["**/*.test.ts"]
  }
}
```

### .eslintrc.js（未使用インポート検出）

```javascript
module.exports = {
  plugins: ['unused-imports'],
  rules: {
    'unused-imports/no-unused-imports': 'error',
    'unused-imports/no-unused-vars': [
      'warn',
      {
        vars: 'all',
        varsIgnorePattern: '^_',
        args: 'after-used',
        argsIgnorePattern: '^_'
      }
    ]
  }
};
```

### tsconfig.json（コンパイラによる検出）

```json
{
  "compilerOptions": {
    "noUnusedLocals": true,
    "noUnusedParameters": true
  }
}
```

## 検出項目の分類

### knipで検出可能な項目

| 項目 | 説明 |
|------|------|
| files | 未使用のファイル |
| exports | 未使用のエクスポート |
| nsExports | 未使用の名前空間エクスポート |
| types | 未使用の型エクスポート |
| duplicates | 重複するエクスポート |
| dependencies | 未使用の依存関係 |
| devDependencies | 未使用の開発依存関係 |
| unlisted | package.jsonに未記載の依存関係 |

## CI/CD統合例

### GitHub Actions

```yaml
- name: Check for dead code
  run: |
    npm ci
    npx knip --no-exit-code
    npx depcheck

- name: Strict dead code check
  run: npx knip
  continue-on-error: false
```

### package.json scripts

```json
{
  "scripts": {
    "dead-code": "knip",
    "dead-code:fix": "knip --fix",
    "unused-deps": "depcheck",
    "lint:unused": "eslint . --rule 'unused-imports/no-unused-imports: error'"
  }
}
```

## 注意事項

- **動的インポート**: `import()` や `require()` で動的に読み込まれるモジュールは検出困難
- **バレルファイル**: `index.ts` での再エクスポートは knip の設定で調整が必要
- **フレームワーク**: Next.js/Nuxt.js などのファイルベースルーティングは設定で除外
- **設定ファイル**: `*.config.ts` や `*.config.js` は entry に含める
- **テストファイル**: テストで使用される関数は ignore パターンで調整
