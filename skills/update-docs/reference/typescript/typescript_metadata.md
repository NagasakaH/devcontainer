# TypeScript/Node.js メタデータファイル読み取りガイド

## 概要

TypeScript/Node.jsプロジェクトのメタデータ（スクリプト、依存関係、設定）を読み取る方法を説明します。

---

## メタデータファイル一覧

| ファイル | 用途 | 優先度 |
|----------|------|--------|
| `package.json` | プロジェクト設定（必須） | 高 |
| `package-lock.json` | npm依存関係ロック | 高 |
| `pnpm-lock.yaml` | pnpm依存関係ロック | 高 |
| `yarn.lock` | yarn依存関係ロック | 高 |
| `tsconfig.json` | TypeScript設定 | 中 |
| `.nvmrc` / `.node-version` | Node.jsバージョン指定 | 中 |

---

## package.json からの情報抽出

### 基本構造

```json
{
  "name": "my-project",
  "version": "1.0.0",
  "description": "プロジェクトの説明",
  "main": "dist/index.js",
  "type": "module",
  "scripts": {
    "build": "tsc",
    "dev": "tsx watch src/index.ts",
    "test": "vitest",
    "test:coverage": "vitest --coverage",
    "lint": "eslint src --ext .ts",
    "format": "prettier --write src"
  },
  "dependencies": {
    "express": "^4.18.2",
    "zod": "^3.22.4"
  },
  "devDependencies": {
    "@types/express": "^4.17.21",
    "@types/node": "^20.10.0",
    "typescript": "^5.3.2",
    "vitest": "^1.0.0"
  },
  "engines": {
    "node": ">=18.0.0"
  }
}
```

### スクリプト一覧の取得

```typescript
import { readFileSync } from 'fs';

interface PackageJson {
  name: string;
  version: string;
  description?: string;
  scripts?: Record<string, string>;
  dependencies?: Record<string, string>;
  devDependencies?: Record<string, string>;
  engines?: { node?: string; npm?: string };
}

function getScripts(packageJsonPath: string = './package.json'): Record<string, string> {
  const content = readFileSync(packageJsonPath, 'utf-8');
  const pkg: PackageJson = JSON.parse(content);
  return pkg.scripts || {};
}

// 使用例
const scripts = getScripts();
console.log('利用可能なスクリプト:');
for (const [name, command] of Object.entries(scripts)) {
  console.log(`  npm run ${name}: ${command}`);
}
```

### 依存関係の取得

```typescript
function getDependencies(packageJsonPath: string = './package.json') {
  const content = readFileSync(packageJsonPath, 'utf-8');
  const pkg: PackageJson = JSON.parse(content);
  
  return {
    main: Object.entries(pkg.dependencies || {}).map(([name, version]) => ({
      name,
      version,
      type: 'production' as const
    })),
    dev: Object.entries(pkg.devDependencies || {}).map(([name, version]) => ({
      name,
      version,
      type: 'development' as const
    }))
  };
}
```

### パッケージマネージャーの検出

```typescript
import { existsSync } from 'fs';
import { join } from 'path';

type PackageManager = 'npm' | 'yarn' | 'pnpm' | 'bun';

function detectPackageManager(projectRoot: string = '.'): PackageManager {
  // ロックファイルで判定
  if (existsSync(join(projectRoot, 'pnpm-lock.yaml'))) return 'pnpm';
  if (existsSync(join(projectRoot, 'yarn.lock'))) return 'yarn';
  if (existsSync(join(projectRoot, 'bun.lockb'))) return 'bun';
  if (existsSync(join(projectRoot, 'package-lock.json'))) return 'npm';
  
  // package.json の packageManager フィールドを確認
  const pkgPath = join(projectRoot, 'package.json');
  if (existsSync(pkgPath)) {
    const pkg = JSON.parse(readFileSync(pkgPath, 'utf-8'));
    if (pkg.packageManager) {
      if (pkg.packageManager.startsWith('pnpm')) return 'pnpm';
      if (pkg.packageManager.startsWith('yarn')) return 'yarn';
      if (pkg.packageManager.startsWith('bun')) return 'bun';
    }
  }
  
  return 'npm'; // デフォルト
}
```

---

## tsconfig.json からの情報抽出

### 基本構造

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "Node16",
    "moduleResolution": "Node16",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "declaration": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

### パース方法

```typescript
import { readFileSync } from 'fs';

interface TsConfig {
  compilerOptions?: {
    target?: string;
    module?: string;
    outDir?: string;
    rootDir?: string;
    strict?: boolean;
    [key: string]: unknown;
  };
  include?: string[];
  exclude?: string[];
  extends?: string;
}

function parseTsConfig(path: string = './tsconfig.json'): TsConfig {
  const content = readFileSync(path, 'utf-8');
  // JSON5形式（コメント付き）の場合は json5 パッケージを使用
  // ここでは標準JSONとして処理
  return JSON.parse(content);
}
```

---

## 利用可能なコマンドの自動検出

### npm scripts の整理

```typescript
interface ScriptInfo {
  name: string;
  command: string;
  description: string;
  category: 'build' | 'test' | 'dev' | 'lint' | 'deploy' | 'other';
}

function categorizeScripts(scripts: Record<string, string>): ScriptInfo[] {
  const result: ScriptInfo[] = [];
  
  for (const [name, command] of Object.entries(scripts)) {
    let category: ScriptInfo['category'] = 'other';
    let description = command;
    
    // カテゴリ判定
    if (name.includes('build') || name.includes('compile')) {
      category = 'build';
      description = 'プロジェクトをビルド';
    } else if (name.includes('test') || name.includes('spec')) {
      category = 'test';
      description = 'テストを実行';
    } else if (name.includes('dev') || name.includes('start') || name.includes('watch')) {
      category = 'dev';
      description = '開発サーバーを起動';
    } else if (name.includes('lint') || name.includes('format') || name.includes('check')) {
      category = 'lint';
      description = 'コード品質チェック';
    } else if (name.includes('deploy') || name.includes('publish') || name.includes('release')) {
      category = 'deploy';
      description = 'デプロイ/公開';
    }
    
    result.push({ name, command, description, category });
  }
  
  return result;
}
```

### 一般的なスクリプトパターン

```typescript
const commonScriptDescriptions: Record<string, string> = {
  // ビルド系
  'build': 'プロジェクトをビルド',
  'build:prod': '本番用ビルド',
  'build:dev': '開発用ビルド',
  'compile': 'TypeScriptをコンパイル',
  'clean': 'ビルド成果物を削除',
  
  // 開発系
  'dev': '開発サーバーを起動（ホットリロード付き）',
  'start': 'アプリケーションを起動',
  'watch': 'ファイル変更を監視して自動再ビルド',
  
  // テスト系
  'test': 'テストを実行',
  'test:watch': 'テストを監視モードで実行',
  'test:coverage': 'カバレッジレポート付きでテスト',
  'test:e2e': 'E2Eテストを実行',
  
  // リント系
  'lint': 'リントを実行',
  'lint:fix': 'リントエラーを自動修正',
  'format': 'コードをフォーマット',
  'typecheck': '型チェックを実行',
  
  // その他
  'prepare': 'パッケージインストール後の準備',
  'precommit': 'コミット前フック',
  'prepush': 'プッシュ前フック',
};
```

---

## Node.js バージョンの検出

```typescript
function detectNodeVersion(projectRoot: string = '.'): string | null {
  // .nvmrc
  const nvmrcPath = join(projectRoot, '.nvmrc');
  if (existsSync(nvmrcPath)) {
    return readFileSync(nvmrcPath, 'utf-8').trim();
  }
  
  // .node-version
  const nodeVersionPath = join(projectRoot, '.node-version');
  if (existsSync(nodeVersionPath)) {
    return readFileSync(nodeVersionPath, 'utf-8').trim();
  }
  
  // package.json engines
  const pkgPath = join(projectRoot, 'package.json');
  if (existsSync(pkgPath)) {
    const pkg = JSON.parse(readFileSync(pkgPath, 'utf-8'));
    if (pkg.engines?.node) {
      return pkg.engines.node;
    }
  }
  
  return null;
}
```

---

## ドキュメント生成テンプレート

### 利用可能なスクリプト

```markdown
## 利用可能なスクリプト

### 開発

| コマンド | 説明 |
|----------|------|
| `npm run dev` | 開発サーバーを起動（ホットリロード付き） |
| `npm start` | アプリケーションを起動 |

### ビルド

| コマンド | 説明 |
|----------|------|
| `npm run build` | TypeScriptをコンパイルしてビルド |
| `npm run clean` | ビルド成果物を削除 |

### テスト

| コマンド | 説明 |
|----------|------|
| `npm test` | テストを実行 |
| `npm run test:coverage` | カバレッジレポート付きでテスト |
| `npm run test:watch` | 監視モードでテスト |

### コード品質

| コマンド | 説明 |
|----------|------|
| `npm run lint` | ESLintでコードをチェック |
| `npm run format` | Prettierでコードをフォーマット |
| `npm run typecheck` | TypeScript型チェック |
```

### 依存関係

```markdown
## 依存関係

### 本番依存関係

| パッケージ | バージョン | 用途 |
|------------|------------|------|
| express | ^4.18.2 | Webフレームワーク |
| zod | ^3.22.4 | スキーマバリデーション |

### 開発依存関係

| パッケージ | バージョン | 用途 |
|------------|------------|------|
| typescript | ^5.3.2 | TypeScriptコンパイラ |
| vitest | ^1.0.0 | テストフレームワーク |
| eslint | ^8.55.0 | リンター |
| prettier | ^3.1.0 | コードフォーマッター |
```

---

## 統合パース関数

```typescript
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

interface ProjectMetadata {
  name: string;
  version: string;
  description?: string;
  packageManager: 'npm' | 'yarn' | 'pnpm' | 'bun';
  nodeVersion?: string;
  scripts: Record<string, string>;
  dependencies: {
    main: Array<{ name: string; version: string }>;
    dev: Array<{ name: string; version: string }>;
  };
  typescript?: {
    target?: string;
    module?: string;
    strict?: boolean;
  };
}

export function extractProjectMetadata(projectRoot: string = '.'): ProjectMetadata {
  const pkgPath = join(projectRoot, 'package.json');
  
  if (!existsSync(pkgPath)) {
    throw new Error('package.json not found');
  }
  
  const pkg = JSON.parse(readFileSync(pkgPath, 'utf-8'));
  
  // パッケージマネージャー検出
  let packageManager: ProjectMetadata['packageManager'] = 'npm';
  if (existsSync(join(projectRoot, 'pnpm-lock.yaml'))) packageManager = 'pnpm';
  else if (existsSync(join(projectRoot, 'yarn.lock'))) packageManager = 'yarn';
  else if (existsSync(join(projectRoot, 'bun.lockb'))) packageManager = 'bun';
  
  // Node.jsバージョン検出
  let nodeVersion: string | undefined;
  if (existsSync(join(projectRoot, '.nvmrc'))) {
    nodeVersion = readFileSync(join(projectRoot, '.nvmrc'), 'utf-8').trim();
  } else if (pkg.engines?.node) {
    nodeVersion = pkg.engines.node;
  }
  
  // TypeScript設定
  let typescript: ProjectMetadata['typescript'];
  const tsconfigPath = join(projectRoot, 'tsconfig.json');
  if (existsSync(tsconfigPath)) {
    try {
      const tsconfig = JSON.parse(readFileSync(tsconfigPath, 'utf-8'));
      typescript = {
        target: tsconfig.compilerOptions?.target,
        module: tsconfig.compilerOptions?.module,
        strict: tsconfig.compilerOptions?.strict,
      };
    } catch {
      // JSON5などの場合は無視
    }
  }
  
  return {
    name: pkg.name,
    version: pkg.version,
    description: pkg.description,
    packageManager,
    nodeVersion,
    scripts: pkg.scripts || {},
    dependencies: {
      main: Object.entries(pkg.dependencies || {}).map(([name, version]) => ({
        name,
        version: version as string
      })),
      dev: Object.entries(pkg.devDependencies || {}).map(([name, version]) => ({
        name,
        version: version as string
      }))
    },
    typescript
  };
}

// Markdown生成
export function generateDocumentation(metadata: ProjectMetadata): string {
  const lines: string[] = [];
  
  lines.push(`# ${metadata.name}`);
  lines.push('');
  if (metadata.description) {
    lines.push(metadata.description);
    lines.push('');
  }
  
  // 環境情報
  lines.push('## 環境');
  lines.push('');
  lines.push(`- **パッケージマネージャー**: ${metadata.packageManager}`);
  if (metadata.nodeVersion) {
    lines.push(`- **Node.js**: ${metadata.nodeVersion}`);
  }
  if (metadata.typescript) {
    lines.push(`- **TypeScript**: target=${metadata.typescript.target}, strict=${metadata.typescript.strict}`);
  }
  lines.push('');
  
  // スクリプト
  if (Object.keys(metadata.scripts).length > 0) {
    lines.push('## 利用可能なスクリプト');
    lines.push('');
    lines.push('| コマンド | 説明 |');
    lines.push('|----------|------|');
    for (const [name, command] of Object.entries(metadata.scripts)) {
      const runCmd = `${metadata.packageManager} run ${name}`;
      lines.push(`| \`${runCmd}\` | \`${command}\` |`);
    }
    lines.push('');
  }
  
  // 依存関係
  if (metadata.dependencies.main.length > 0) {
    lines.push('## 依存関係');
    lines.push('');
    lines.push('### 本番');
    lines.push('');
    lines.push('| パッケージ | バージョン |');
    lines.push('|------------|------------|');
    for (const dep of metadata.dependencies.main) {
      lines.push(`| ${dep.name} | ${dep.version} |`);
    }
    lines.push('');
  }
  
  if (metadata.dependencies.dev.length > 0) {
    lines.push('### 開発');
    lines.push('');
    lines.push('| パッケージ | バージョン |');
    lines.push('|------------|------------|');
    for (const dep of metadata.dependencies.dev) {
      lines.push(`| ${dep.name} | ${dep.version} |`);
    }
    lines.push('');
  }
  
  return lines.join('\n');
}
```
