---
name: tdd
description: テスト駆動開発（TDD）のワークフローを実践するためのスキル。インターフェースの定義、テストファーストでの実装、最小限のコード記述、リファクタリングを通じて80%以上のカバレッジを確保する。「TDDで実装」「テストを先に書いて」「テスト駆動で開発」「RED-GREEN-REFACTOR」などのフレーズで起動。
---

# TDD（テスト駆動開発）スキル

テスト駆動開発の方法論を実践するためのガイド。

## TDDサイクル

```
RED → GREEN → REFACTOR → REPEAT

RED:      失敗するテストを書く
GREEN:    テストを通す最小限のコードを書く
REFACTOR: テストを維持しながらコードを改善
REPEAT:   次の機能/シナリオへ
```

## 実行手順

1. **インターフェース定義** - 入出力の型/インターフェースを定義
2. **テスト作成（RED）** - 失敗するテストを先に書く
3. **テスト実行・失敗確認** - 正しい理由で失敗することを確認
4. **最小実装（GREEN）** - テストを通す最小限のコードを書く
5. **テスト実行・成功確認** - すべてのテストが通ることを確認
6. **リファクタリング** - テストを維持しながらコードを改善
7. **カバレッジ確認** - 80%以上を確保、不足なら追加テスト

## 使用タイミング

- 新機能の実装
- 新しい関数/コンポーネントの追加
- バグ修正（まずバグを再現するテストを書く）
- 既存コードのリファクタリング
- 重要なビジネスロジックの構築

## TDDのベストプラクティス

### 推奨事項

- テストを実装より先に書く
- 実装前にテストが失敗することを確認
- テストを通す最小限のコードを書く
- テストがグリーンになってからリファクタリング
- エッジケースとエラーシナリオを追加
- 80%以上のカバレッジを目標（重要なコードは100%）

### 避けるべきこと

- テストより先に実装を書く
- 変更後のテスト実行をスキップ
- 一度に多くのコードを書く
- 失敗するテストを無視
- 実装の詳細をテストする（振る舞いをテストする）
- すべてをモックする（統合テストを優先）

## テストの種類

### ユニットテスト（関数レベル）

- 正常系シナリオ
- エッジケース（空、null、最大値）
- エラー条件
- 境界値

### 統合テスト（コンポーネントレベル）

- APIエンドポイント
- データベース操作
- 外部サービス呼び出し
- Reactコンポーネント（フック含む）

### E2Eテスト（システムレベル）

- 重要なユーザーフロー
- マルチステッププロセス
- フルスタック統合

## カバレッジ要件

- **80%以上**: すべてのコードの最低基準
- **100%必須**: 以下のコード
  - 金融計算
  - 認証ロジック
  - セキュリティ重要コード
  - コアビジネスロジック

## 実装例

### ステップ1: インターフェース定義（SCAFFOLD）

```typescript
// lib/liquidity.ts
export interface MarketData {
  totalVolume: number
  bidAskSpread: number
  activeTraders: number
  lastTradeTime: Date
}

export function calculateLiquidityScore(market: MarketData): number {
  // TODO: 実装
  throw new Error('未実装')
}
```

### ステップ2: 失敗するテストを書く（RED）

```typescript
// lib/liquidity.test.ts
import { calculateLiquidityScore } from './liquidity'

describe('calculateLiquidityScore', () => {
  it('流動性の高い市場では高スコアを返す', () => {
    const market = {
      totalVolume: 100000,
      bidAskSpread: 0.01,
      activeTraders: 500,
      lastTradeTime: new Date()
    }

    const score = calculateLiquidityScore(market)

    expect(score).toBeGreaterThan(80)
    expect(score).toBeLessThanOrEqual(100)
  })

  it('流動性の低い市場では低スコアを返す', () => {
    const market = {
      totalVolume: 100,
      bidAskSpread: 0.5,
      activeTraders: 2,
      lastTradeTime: new Date(Date.now() - 86400000) // 1日前
    }

    const score = calculateLiquidityScore(market)

    expect(score).toBeLessThan(30)
    expect(score).toBeGreaterThanOrEqual(0)
  })

  it('エッジケース: ボリュームゼロを処理', () => {
    const market = {
      totalVolume: 0,
      bidAskSpread: 0,
      activeTraders: 0,
      lastTradeTime: new Date()
    }

    const score = calculateLiquidityScore(market)

    expect(score).toBe(0)
  })
})
```

### ステップ3: テスト実行 - 失敗を確認

```bash
npm test lib/liquidity.test.ts

FAIL lib/liquidity.test.ts
  ✕ 流動性の高い市場では高スコアを返す (2 ms)
    Error: 未実装

1 test failed, 0 passed
```

テストが期待通り失敗。実装準備完了。

### ステップ4: 最小実装（GREEN）

```typescript
// lib/liquidity.ts
export function calculateLiquidityScore(market: MarketData): number {
  if (market.totalVolume === 0) {
    return 0
  }

  const volumeScore = Math.min(market.totalVolume / 1000, 100)
  const spreadScore = Math.max(100 - (market.bidAskSpread * 1000), 0)
  const traderScore = Math.min(market.activeTraders / 10, 100)

  const hoursSinceLastTrade = (Date.now() - market.lastTradeTime.getTime()) / (1000 * 60 * 60)
  const recencyScore = Math.max(100 - (hoursSinceLastTrade * 10), 0)

  const score = (
    volumeScore * 0.4 +
    spreadScore * 0.3 +
    traderScore * 0.2 +
    recencyScore * 0.1
  )

  return Math.min(Math.max(score, 0), 100)
}
```

### ステップ5: テスト実行 - 成功を確認

```bash
npm test lib/liquidity.test.ts

PASS lib/liquidity.test.ts
  ✓ 流動性の高い市場では高スコアを返す (3 ms)
  ✓ 流動性の低い市場では低スコアを返す (2 ms)
  ✓ エッジケース: ボリュームゼロを処理 (1 ms)

3 tests passed
```

### ステップ6: リファクタリング（IMPROVE）

```typescript
// lib/liquidity.ts - 定数と可読性を改善
const WEIGHTS = {
  VOLUME: 0.4,
  SPREAD: 0.3,
  TRADERS: 0.2,
  RECENCY: 0.1,
} as const

const SCALE_FACTORS = {
  VOLUME: 1000,
  SPREAD: 1000,
  TRADERS: 10,
  RECENCY_PENALTY: 10,
} as const

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

export function calculateLiquidityScore(market: MarketData): number {
  if (market.totalVolume === 0) return 0

  const volumeScore = Math.min(market.totalVolume / SCALE_FACTORS.VOLUME, 100)
  const spreadScore = clamp(100 - (market.bidAskSpread * SCALE_FACTORS.SPREAD), 0, 100)
  const traderScore = Math.min(market.activeTraders / SCALE_FACTORS.TRADERS, 100)

  const hoursSinceLastTrade = (Date.now() - market.lastTradeTime.getTime()) / (1000 * 60 * 60)
  const recencyScore = clamp(100 - (hoursSinceLastTrade * SCALE_FACTORS.RECENCY_PENALTY), 0, 100)

  const weightedScore =
    volumeScore * WEIGHTS.VOLUME +
    spreadScore * WEIGHTS.SPREAD +
    traderScore * WEIGHTS.TRADERS +
    recencyScore * WEIGHTS.RECENCY

  return clamp(weightedScore, 0, 100)
}
```

### ステップ7: テストが通ることを再確認

```bash
npm test lib/liquidity.test.ts

PASS lib/liquidity.test.ts
  ✓ 流動性の高い市場では高スコアを返す (3 ms)
  ✓ 流動性の低い市場では低スコアを返す (2 ms)
  ✓ エッジケース: ボリュームゼロを処理 (1 ms)

3 tests passed
```

### ステップ8: カバレッジ確認

```bash
npm test -- --coverage lib/liquidity.test.ts

File           | % Stmts | % Branch | % Funcs | % Lines
---------------|---------|----------|---------|--------
liquidity.ts   |   100   |   100    |   100   |   100

Coverage: 100% ✅ (Target: 80%)
```

## 重要事項

**必須**: テストは実装より先に書く。TDDサイクルは：

1. **RED** - 失敗するテストを書く
2. **GREEN** - テストを通す実装
3. **REFACTOR** - コード改善

REDフェーズを絶対にスキップしない。テストより先にコードを書かない。
