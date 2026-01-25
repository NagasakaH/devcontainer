---
sidebar_position: 1769331671
date: 2026-01-25T09:01:11+00:00
---

# TypeScript テストフレームワーク

TDD（テスト駆動開発）をTypeScript/JavaScriptで実践するためのフレームワークとツールガイド。

## テストフレームワーク

### Vitest（推奨）

Viteベースの高速テストフレームワーク。Jest互換のAPIでモダンなTypeScriptプロジェクトに最適。

```typescript
// lib/liquidity.test.ts
import { describe, it, expect } from 'vitest'
import { calculateLiquidityScore, MarketData } from './liquidity'

describe('calculateLiquidityScore', () => {
  it('流動性の高い市場では高スコアを返す', () => {
    const market: MarketData = {
      totalVolume: 100000,
      bidAskSpread: 0.01,
      activeTraders: 500,
      lastTradeTime: new Date()
    }

    const score = calculateLiquidityScore(market)

    expect(score).toBeGreaterThan(80)
    expect(score).toBeLessThanOrEqual(100)
  })

  it('ボリュームゼロではゼロを返す', () => {
    const market: MarketData = {
      totalVolume: 0,
      bidAskSpread: 0,
      activeTraders: 0,
      lastTradeTime: new Date()
    }

    const score = calculateLiquidityScore(market)

    expect(score).toBe(0)
  })

  it.each([
    { volume: 100, expectedMin: 0 },
    { volume: 1000, expectedMin: 20 },
    { volume: 10000, expectedMin: 50 },
    { volume: 100000, expectedMin: 80 },
  ])('volume=$volume のとき、スコアは $expectedMin 以上', ({ volume, expectedMin }) => {
    const market: MarketData = {
      totalVolume: volume,
      bidAskSpread: 0.01,
      activeTraders: 100,
      lastTradeTime: new Date()
    }

    const score = calculateLiquidityScore(market)

    expect(score).toBeGreaterThanOrEqual(expectedMin)
  })
})
```

### Jest

最も広く使用されているJavaScript/TypeScriptテストフレームワーク。

```typescript
// lib/liquidity.test.ts
import { calculateLiquidityScore, MarketData } from './liquidity'

describe('calculateLiquidityScore', () => {
  it('流動性の高い市場では高スコアを返す', () => {
    const market: MarketData = {
      totalVolume: 100000,
      bidAskSpread: 0.01,
      activeTraders: 500,
      lastTradeTime: new Date()
    }

    const score = calculateLiquidityScore(market)

    expect(score).toBeGreaterThan(80)
    expect(score).toBeLessThanOrEqual(100)
  })

  it('ボリュームゼロではゼロを返す', () => {
    const market: MarketData = {
      totalVolume: 0,
      bidAskSpread: 0,
      activeTraders: 0,
      lastTradeTime: new Date()
    }

    const score = calculateLiquidityScore(market)

    expect(score).toBe(0)
  })

  it.each`
    volume     | expectedMin
    ${100}     | ${0}
    ${1000}    | ${20}
    ${10000}   | ${50}
    ${100000}  | ${80}
  `('volume=$volume のとき、スコアは $expectedMin 以上', ({ volume, expectedMin }) => {
    const market: MarketData = {
      totalVolume: volume,
      bidAskSpread: 0.01,
      activeTraders: 100,
      lastTradeTime: new Date()
    }

    const score = calculateLiquidityScore(market)

    expect(score).toBeGreaterThanOrEqual(expectedMin)
  })
})
```

### Node.js Test Runner（標準ライブラリ）

Node.js 18+に組み込まれたテストランナー。外部依存なしで使用可能。

```typescript
// lib/liquidity.test.ts
import { describe, it } from 'node:test'
import assert from 'node:assert'
import { calculateLiquidityScore, MarketData } from './liquidity.js'

describe('calculateLiquidityScore', () => {
  it('流動性の高い市場では高スコアを返す', () => {
    const market: MarketData = {
      totalVolume: 100000,
      bidAskSpread: 0.01,
      activeTraders: 500,
      lastTradeTime: new Date()
    }

    const score = calculateLiquidityScore(market)

    assert.ok(score > 80)
    assert.ok(score <= 100)
  })

  it('ボリュームゼロではゼロを返す', () => {
    const market: MarketData = {
      totalVolume: 0,
      bidAskSpread: 0,
      activeTraders: 0,
      lastTradeTime: new Date()
    }

    const score = calculateLiquidityScore(market)

    assert.strictEqual(score, 0)
  })
})
```

## アサーションライブラリ

### expect（Vitest/Jest 組み込み）

```typescript
// 基本的なアサーション
expect(result).toBe(expected)           // 厳密等価
expect(result).toEqual(expected)        // 深い等価
expect(result).toBeGreaterThan(5)
expect(result).toBeLessThanOrEqual(100)
expect(result).toBeNull()
expect(result).toBeUndefined()
expect(result).toBeTruthy()
expect(result).toBeFalsy()

// 配列・オブジェクト
expect(array).toContain(item)
expect(array).toHaveLength(5)
expect(object).toHaveProperty('key', 'value')
expect(object).toMatchObject({ key: 'value' })

// 例外のテスト
expect(() => functionThatThrows()).toThrow('error message')
expect(() => functionThatThrows()).toThrow(CustomError)
await expect(asyncFn()).rejects.toThrow('error')

// 浮動小数点の近似比較
expect(result).toBeCloseTo(expected, 3)

// スナップショット
expect(result).toMatchSnapshot()
expect(result).toMatchInlineSnapshot(`"expected"`)
```

### Chai

```typescript
import { expect } from 'chai'

// 基本的なアサーション
expect(result).to.equal(expected)
expect(result).to.deep.equal(expected)
expect(result).to.be.greaterThan(5)
expect(result).to.be.null
expect(result).to.be.an('array')
expect(result).to.have.property('key', 'value')
expect(result).to.include(item)

// 例外のテスト
expect(() => fn()).to.throw(Error)
```

## モックライブラリ

### Vitest モック

```typescript
import { vi, describe, it, expect, beforeEach } from 'vitest'

// 関数のモック
const mockFn = vi.fn()
mockFn.mockReturnValue('mocked')
mockFn.mockResolvedValue('async mocked')

// モジュールのモック
vi.mock('./database', () => ({
  getUser: vi.fn().mockResolvedValue({ id: 1, name: 'Test' })
}))

// スパイ
const spy = vi.spyOn(object, 'method')
spy.mockImplementation(() => 'mocked')

// タイマーのモック
vi.useFakeTimers()
vi.advanceTimersByTime(1000)
vi.useRealTimers()

// 呼び出し検証
expect(mockFn).toHaveBeenCalled()
expect(mockFn).toHaveBeenCalledWith(arg1, arg2)
expect(mockFn).toHaveBeenCalledTimes(3)
```

### Jest モック

```typescript
// 関数のモック
const mockFn = jest.fn()
mockFn.mockReturnValue('mocked')
mockFn.mockResolvedValue('async mocked')

// モジュールのモック
jest.mock('./database', () => ({
  getUser: jest.fn().mockResolvedValue({ id: 1, name: 'Test' })
}))

// スパイ
const spy = jest.spyOn(object, 'method')
spy.mockImplementation(() => 'mocked')

// タイマーのモック
jest.useFakeTimers()
jest.advanceTimersByTime(1000)
jest.useRealTimers()
```

## 実行コマンド

```bash
# Vitest
npx vitest                  # watch モード
npx vitest run              # 一度だけ実行
npx vitest run --coverage   # カバレッジ付き
npx vitest --ui             # UI モード

# Jest
npm test                    # package.json の test スクリプト
npx jest                    # 直接実行
npx jest --watch            # watch モード
npx jest --coverage         # カバレッジ付き

# Node.js Test Runner
node --test                 # テスト実行
node --test --watch         # watch モード

# 共通オプション
npx vitest run tests/liquidity.test.ts    # 特定ファイル
npx jest --testNamePattern="高スコア"       # 名前でフィルタ
npx vitest run --reporter=verbose          # 詳細出力
```

## カバレッジ

### Vitest カバレッジ

```bash
# インストール
npm install -D @vitest/coverage-v8

# カバレッジ付きでテスト実行
npx vitest run --coverage

# 閾値設定（vitest.config.ts）
```

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      exclude: ['node_modules', 'test'],
      thresholds: {
        global: {
          branches: 80,
          functions: 80,
          lines: 80,
          statements: 80
        }
      }
    }
  }
})
```

### Jest カバレッジ

```bash
# カバレッジ付きでテスト実行
npx jest --coverage

# 閾値設定（jest.config.js）
```

```javascript
// jest.config.js
module.exports = {
  collectCoverageFrom: ['src/**/*.{ts,tsx}'],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  }
}
```

**カバレッジレポートパス**: `coverage/lcov-report/index.html`

## プロジェクト構成例

```
project/
├── package.json
├── tsconfig.json
├── vitest.config.ts      # Vitest設定
├── src/
│   └── lib/
│       ├── liquidity.ts
│       └── liquidity.test.ts   # co-location
└── tests/                      # または別ディレクトリ
    └── integration/
        └── api.test.ts
```

### package.json

```json
{
  "scripts": {
    "test": "vitest",
    "test:run": "vitest run",
    "test:coverage": "vitest run --coverage",
    "test:ui": "vitest --ui"
  },
  "devDependencies": {
    "vitest": "^1.0.0",
    "@vitest/coverage-v8": "^1.0.0",
    "@vitest/ui": "^1.0.0"
  }
}
```

## ベストプラクティス

### 推奨事項

- `Vitest` を使用（高速、TypeScriptネイティブサポート）
- テストファイルは `.test.ts` または `.spec.ts` 拡張子
- ソースファイルと同じディレクトリにテストを配置（co-location）
- `it.each` / `test.each` でデータ駆動テストを実装
- `beforeEach` / `afterEach` でテストのセットアップ・クリーンアップ
- 型安全なモックを使用

### 避けるべきこと

- テスト間で状態を共有（各テストは独立すべき）
- `any` 型の多用（型安全性を維持）
- `setTimeout` での任意の待機（適切な待機を使用）
- 実装の詳細をテスト（振る舞いをテスト）
- スナップショットの過度な使用

## 関連ツール

| ツール | 用途 |
|--------|------|
| `Vitest` / `Jest` | テストフレームワーク |
| `@vitest/coverage-v8` | カバレッジ計測 |
| `@vitest/ui` | テストUI |
| `msw` | APIモック（Mock Service Worker） |
| `@testing-library/react` | Reactコンポーネントテスト |
| `@faker-js/faker` | フェイクデータ生成 |
| `supertest` | HTTP APIテスト |
