---
sidebar_position: 1769331678
date: 2026-01-25T09:01:18+00:00
---

# TypeScript - 検証ツール

## 検証コマンド一覧

### ビルドチェック

```bash
# npm
npm run build

# pnpm
pnpm build

# yarn
yarn build

# tscでビルド
npx tsc
```

### 型チェック

```bash
# 型チェックのみ（出力なし）
npx tsc --noEmit

# 特定のファイルのみ
npx tsc --noEmit src/index.ts

# 設定ファイルを指定
npx tsc --noEmit -p tsconfig.json

# インクリメンタルビルド
npx tsc --noEmit --incremental
```

### リントチェック

```bash
# ESLint
npx eslint .

# 自動修正
npx eslint . --fix

# 特定のファイル/ディレクトリ
npx eslint src/ --ext .ts,.tsx

# Biome（高速な代替）
npx biome check .
```

### テスト実行

```bash
# Jest
npm test

# カバレッジ付き
npm test -- --coverage

# Vitest
npx vitest run

# Vitest カバレッジ付き
npx vitest run --coverage
```

### デバッグ出力検索

```bash
# console.log の検索
grep -rn "console\.log" --include="*.ts" --include="*.tsx" src/

# console.* 全般の検索
grep -rn "console\." --include="*.ts" --include="*.tsx" src/

# debugger文の検索
grep -rn "debugger" --include="*.ts" --include="*.tsx" src/
```

## 設定ファイル例

### tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "exactOptionalPropertyTypes": true,
    "noUncheckedIndexedAccess": true,
    "skipLibCheck": true,
    "declaration": true,
    "outDir": "./dist"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

### eslint.config.js（Flat Config）

```javascript
import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  eslint.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        project: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      'no-console': 'error',
      '@typescript-eslint/no-unused-vars': 'error',
    },
  },
  {
    ignores: ['dist/', 'node_modules/', '*.config.js'],
  }
);
```

### .eslintrc.json（従来形式）

```json
{
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:@typescript-eslint/recommended-type-checked"
  ],
  "parser": "@typescript-eslint/parser",
  "parserOptions": {
    "project": true
  },
  "rules": {
    "no-console": "error",
    "@typescript-eslint/no-unused-vars": "error"
  }
}
```

### package.json scripts

```json
{
  "scripts": {
    "build": "tsc",
    "typecheck": "tsc --noEmit",
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "test": "vitest run",
    "test:coverage": "vitest run --coverage",
    "verify": "npm run typecheck && npm run lint && npm run test",
    "verify:quick": "npm run typecheck && npm run lint",
    "verify:full": "npm run build && npm run typecheck && npm run lint && npm run test:coverage"
  }
}
```

## CI/CD統合例

### GitHub Actions

```yaml
name: Verify TypeScript

on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Build
        run: npm run build
      
      - name: Type check
        run: npx tsc --noEmit
      
      - name: Lint
        run: npm run lint
      
      - name: Test
        run: npm test -- --coverage
      
      - name: Check for console.log
        run: |
          if grep -rn "console\.log" --include="*.ts" --include="*.tsx" src/; then
            echo "Found console.log in source code"
            exit 1
          fi
```

### Biome設定（ESLint代替）

```json
{
  "$schema": "https://biomejs.dev/schemas/1.5.0/schema.json",
  "organizeImports": {
    "enabled": true
  },
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true,
      "suspicious": {
        "noConsoleLog": "error"
      }
    }
  }
}
```

## 検証結果の解釈

| チェック | 成功条件 |
|----------|----------|
| ビルド | エラーなしで完了 |
| 型チェック | tsc --noEmit がエラー0件 |
| リント | ESLint/Biome がエラー0件 |
| テスト | 全テストがパス |
| デバッグ出力 | console.logがsrc/内にない |
