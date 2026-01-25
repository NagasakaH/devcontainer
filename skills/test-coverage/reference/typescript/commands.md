# TypeScript テストカバレッジコマンドリファレンス

## テスト実行コマンド

### Jest（推奨）

```bash
# npm
npm test -- --coverage

# pnpm
pnpm test --coverage

# yarn
yarn test --coverage

# 直接実行
npx jest --coverage

# 特定のファイルのみ
npm test -- --coverage --collectCoverageFrom='src/**/*.ts'
```

### Vitest

```bash
# 基本的なカバレッジ付きテスト実行
npx vitest run --coverage

# watchモードでカバレッジ
npx vitest --coverage

# v8プロバイダー（高速）
npx vitest run --coverage --coverage.provider=v8

# istanbulプロバイダー（詳細）
npx vitest run --coverage --coverage.provider=istanbul
```

### c8（Node.js v8カバレッジ）

```bash
# mochaと組み合わせ
npx c8 mocha

# 任意のNode.jsスクリプト
npx c8 node script.js

# レポート形式指定
npx c8 --reporter=html --reporter=text mocha
```

### nyc（istanbul CLI）

```bash
# mochaと組み合わせ
npx nyc mocha

# レポート生成
npx nyc report --reporter=html
```

## カバレッジレポートファイルのパス

| 形式 | 出力パス | 用途 |
|------|----------|------|
| JSON Summary | `coverage/coverage-summary.json` | プログラム解析 |
| LCOV | `coverage/lcov.info` | CI/CD連携 |
| HTML | `coverage/lcov-report/index.html` | 詳細な可視化 |
| Clover | `coverage/clover.xml` | CI連携 |
| Cobertura | `coverage/cobertura-coverage.xml` | CI連携 |

## 主要なツール・フレームワーク

### テストフレームワーク

- **Jest** - 最も広く使われているテストフレームワーク
- **Vitest** - Vite対応の高速テストフレームワーク
- **Mocha** - 柔軟性の高いテストフレームワーク
- **AVA** - 並列実行に特化したテストフレームワーク

### カバレッジツール

- **istanbul/nyc** - デファクトスタンダードのカバレッジツール
- **c8** - Node.js v8組み込みカバレッジを使用（高速）
- **v8-to-istanbul** - v8カバレッジをistanbul形式に変換

## 設定ファイル例

### Jest（jest.config.js）

```javascript
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  collectCoverage: true,
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'json-summary'],
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.test.{ts,tsx}',
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
};
```

### Vitest（vitest.config.ts）

```typescript
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    coverage: {
      provider: 'v8', // or 'istanbul'
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.ts'],
      exclude: ['**/*.test.ts', '**/*.d.ts'],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
    },
  },
});
```

### nyc（.nycrc）

```json
{
  "extends": "@istanbuljs/nyc-config-typescript",
  "all": true,
  "include": ["src/**/*.ts"],
  "exclude": ["**/*.test.ts"],
  "reporter": ["text", "html", "lcov"],
  "check-coverage": true,
  "branches": 80,
  "lines": 80,
  "functions": 80,
  "statements": 80
}
```

## package.jsonスクリプト例

```json
{
  "scripts": {
    "test": "jest",
    "test:coverage": "jest --coverage",
    "test:ci": "jest --coverage --ci --reporters=default --reporters=jest-junit"
  }
}
```

## CI/CD連携（GitHub Actions例）

```yaml
- name: Run tests with coverage
  run: npm test -- --coverage --ci

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage/lcov.info

- name: Check coverage threshold
  run: |
    npm test -- --coverage --coverageThreshold='{"global":{"branches":80,"functions":80,"lines":80}}'
```

## カバレッジ閾値の設定

```bash
# Jestでの閾値チェック（CLIオプション）
npx jest --coverage --coverageThreshold='{"global":{"branches":80,"functions":80,"lines":80,"statements":80}}'

# Vitestでの閾値チェック
npx vitest run --coverage --coverage.thresholds.lines=80
```
