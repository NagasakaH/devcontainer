# TypeScript ビルドコマンドリファレンス

## ビルドコマンド

### tsc（TypeScriptコンパイラ）

```bash
# 基本的なビルド
npx tsc

# 監視モード
npx tsc --watch

# 特定の設定ファイル
npx tsc --project tsconfig.build.json

# 宣言ファイルのみ生成
npx tsc --declaration --emitDeclarationOnly

# エラー時もビルドを継続
npx tsc --noEmitOnError false
```

### npm/pnpm/yarn スクリプト

```bash
# npm
npm run build

# pnpm
pnpm build

# yarn
yarn build
```

### esbuild（高速バンドラー）

```bash
# 基本的なビルド
npx esbuild src/index.ts --outdir=dist --bundle

# 本番用ビルド
npx esbuild src/index.ts --outdir=dist --bundle --minify --sourcemap
```

### Vite

```bash
# ビルド
npx vite build

# プレビュー
npx vite preview
```

### webpack

```bash
# 開発ビルド
npx webpack --mode development

# 本番ビルド
npx webpack --mode production
```

### Rollup

```bash
# ビルド
npx rollup -c rollup.config.js
```

## ビルド出力ディレクトリ

| ツール | デフォルト出力パス |
|--------|-------------------|
| tsc | `outDir`（tsconfig.jsonで指定） |
| esbuild | 指定した`--outdir` |
| Vite | `dist/` |
| webpack | `dist/` |
| Next.js | `.next/` |

## 主要なビルドツール

### コンパイラ・トランスパイラ

- **tsc** - TypeScript公式コンパイラ
- **esbuild** - 超高速バンドラー・トランスパイラ
- **swc** - Rust製の高速トランスパイラ
- **Babel** - JavaScript変換ツール

### バンドラー

- **Vite** - 次世代フロントエンドビルドツール
- **webpack** - 汎用モジュールバンドラー
- **Rollup** - ESモジュール向けバンドラー
- **Turbopack** - Vercel製の高速バンドラー

## 設定ファイル例

### tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "**/*.test.ts"]
}
```

### package.json スクリプト例

```json
{
  "scripts": {
    "build": "tsc",
    "build:watch": "tsc --watch",
    "build:prod": "tsc && npm run bundle",
    "typecheck": "tsc --noEmit",
    "clean": "rm -rf dist"
  }
}
```

## 一般的なエラーと解決方法

### TS2307: モジュールが見つからない

```bash
# 依存関係をインストール
npm install

# 型定義をインストール
npm install --save-dev @types/node @types/lodash
```

### TS2345: 型の不一致

```typescript
// 型を明示的に指定
const value: string = getValue() as string;

// 型ガードを使用
if (typeof value === 'string') {
  // 安全に使用
}
```

### TS2322: 型を割り当てられない

- インターフェースの定義を確認
- オプショナルプロパティ（`?`）の使用を検討
- 型アサーションを最小限に使用

### TS1005/TS1109: 構文エラー

```bash
# TypeScriptバージョンを確認
npx tsc --version

# ESLintで構文チェック
npx eslint src/ --ext .ts,.tsx
```

### TS6133: 未使用の変数

```json
// tsconfig.jsonで設定
{
  "compilerOptions": {
    "noUnusedLocals": false,
    "noUnusedParameters": false
  }
}
```

または変数名の先頭にアンダースコアを付ける：

```typescript
function handler(_event: Event) {
  // _event は使用しなくてもエラーにならない
}
```

## 型チェックのみ（ビルドなし）

```bash
# エラーチェックのみ
npx tsc --noEmit

# 監視モードでチェック
npx tsc --noEmit --watch
```

## CI/CD連携（GitHub Actions例）

```yaml
- name: Setup Node.js
  uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'

- name: Install dependencies
  run: npm ci

- name: Type check
  run: npx tsc --noEmit

- name: Lint
  run: npm run lint

- name: Build
  run: npm run build

- name: Check build artifacts
  run: ls -la dist/
```

## 診断・デバッグ

```bash
# ビルドパフォーマンスの計測
npx tsc --extendedDiagnostics

# トレース出力
npx tsc --traceResolution

# 生成されるファイルのプレビュー
npx tsc --listEmittedFiles
```
