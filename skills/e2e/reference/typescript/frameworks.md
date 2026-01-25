---
sidebar_position: 1769331671
date: 2026-01-25T09:01:11+00:00
---

# TypeScript E2Eテストフレームワーク

TypeScript/JavaScriptでエンドツーエンドテストを実践するためのフレームワークとツールガイド。

## テストフレームワーク

### Playwright（推奨）

Microsoftが開発したモダンなブラウザ自動化ツール。複数ブラウザをサポートし、自動待機、トレース、スクリーンショットなどの機能が充実。

```typescript
// tests/e2e/market-search.spec.ts
import { test, expect } from '@playwright/test'

test.describe('市場検索', () => {
  test('ユーザーは市場を検索してフィルタリングできる', async ({ page }) => {
    // 1. ホームページに移動
    await page.goto('/')
    
    // 2. 市場ページに移動
    await page.click('a[href="/markets"]')
    
    // 3. 検索を実行
    await page.fill('input[placeholder="検索"]', 'election')
    await page.waitForTimeout(600) // デバウンス待機
    
    // 4. 結果を検証
    const results = page.locator('[data-testid="market-card"]')
    await expect(results).toHaveCount(5, { timeout: 5000 })
  })

  test('ユーザーは市場の詳細を表示できる', async ({ page }) => {
    await page.goto('/markets')
    
    // 最初の市場カードをクリック
    await page.locator('[data-testid="market-card"]').first().click()
    
    // 詳細ページが表示されることを確認
    await expect(page.locator('h1')).toBeVisible()
    await expect(page.locator('[data-testid="market-chart"]')).toBeVisible()
  })
})
```

### Cypress

フロントエンド開発者に人気のE2Eテストフレームワーク。リアルタイムリロード、デバッグが容易。

```typescript
// cypress/e2e/market-search.cy.ts
describe('市場検索', () => {
  it('ユーザーは市場を検索してフィルタリングできる', () => {
    // 1. ホームページに移動
    cy.visit('/')
    
    // 2. 市場ページに移動
    cy.get('a[href="/markets"]').click()
    
    // 3. 検索を実行
    cy.get('input[placeholder="検索"]').type('election')
    cy.wait(600) // デバウンス待機
    
    // 4. 結果を検証
    cy.get('[data-testid="market-card"]').should('have.length', 5)
  })

  it('ユーザーは市場の詳細を表示できる', () => {
    cy.visit('/markets')
    
    // 最初の市場カードをクリック
    cy.get('[data-testid="market-card"]').first().click()
    
    // 詳細ページが表示されることを確認
    cy.get('h1').should('be.visible')
    cy.get('[data-testid="market-chart"]').should('be.visible')
  })
})
```

### Testing Library + Playwright

Testing Libraryの哲学（ユーザー視点でテスト）をPlaywrightと組み合わせ。

```typescript
// tests/e2e/market-search.spec.ts
import { test, expect } from '@playwright/test'

test.describe('市場検索', () => {
  test('ユーザーは市場を検索できる', async ({ page }) => {
    await page.goto('/markets')
    
    // ユーザー視点のセレクタ
    await page.getByRole('textbox', { name: '検索' }).fill('election')
    await page.getByRole('button', { name: 'フィルター' }).click()
    
    // 結果を検証
    const cards = page.getByTestId('market-card')
    await expect(cards).toHaveCount(5)
  })
})
```

## Page Object パターン

```typescript
// tests/pages/MarketsPage.ts
import { Page, Locator, expect } from '@playwright/test'

export class MarketsPage {
  readonly page: Page
  readonly searchInput: Locator
  readonly marketCards: Locator
  readonly filterButtons: Locator

  constructor(page: Page) {
    this.page = page
    this.searchInput = page.locator('input[placeholder="検索"]')
    this.marketCards = page.locator('[data-testid="market-card"]')
    this.filterButtons = page.locator('[data-testid="filter-button"]')
  }

  async goto() {
    await this.page.goto('/markets')
  }

  async search(keyword: string) {
    await this.searchInput.fill(keyword)
    await this.page.waitForTimeout(600) // デバウンス待機
  }

  async applyFilter(filterName: string) {
    await this.filterButtons.filter({ hasText: filterName }).click()
  }

  async getMarketCount(): Promise<number> {
    return await this.marketCards.count()
  }

  async clickFirstMarket() {
    await this.marketCards.first().click()
  }

  async expectMarketCount(count: number) {
    await expect(this.marketCards).toHaveCount(count)
  }
}

// 使用例
import { test } from '@playwright/test'
import { MarketsPage } from './pages/MarketsPage'

test('市場を検索する', async ({ page }) => {
  const marketsPage = new MarketsPage(page)
  await marketsPage.goto()
  await marketsPage.search('election')
  
  await marketsPage.expectMarketCount(5)
})
```

## アサーション

### Playwright expect

```typescript
import { expect } from '@playwright/test'

// 要素の可視性
await expect(page.locator('h1')).toBeVisible()
await expect(page.locator('.modal')).toBeHidden()

// テキスト
await expect(page.locator('h1')).toHaveText('市場一覧')
await expect(page.locator('h1')).toContainText('市場')

// 属性
await expect(page.locator('input')).toHaveValue('election')
await expect(page.locator('button')).toBeEnabled()
await expect(page.locator('input')).toBeDisabled()

// 数
await expect(page.locator('.item')).toHaveCount(5)

// URL
await expect(page).toHaveURL('/markets')
await expect(page).toHaveTitle('市場 | MyApp')

// スクリーンショット比較
await expect(page).toHaveScreenshot('markets.png')
```

### Cypress assertions

```typescript
// 基本的なアサーション
cy.get('h1').should('be.visible')
cy.get('h1').should('have.text', '市場一覧')
cy.get('h1').should('contain', '市場')
cy.get('input').should('have.value', 'election')
cy.get('.item').should('have.length', 5)

// URL
cy.url().should('include', '/markets')
cy.title().should('eq', '市場 | MyApp')
```

## 実行コマンド

```bash
# Playwright
npx playwright test                      # 全E2Eテスト実行
npx playwright test --headed             # ブラウザ表示
npx playwright test --project=chromium   # 特定ブラウザ
npx playwright test --debug              # デバッグモード
npx playwright test --ui                 # UIモード
npx playwright codegen http://localhost:3000  # テストコード生成

# Cypress
npx cypress run                          # ヘッドレス実行
npx cypress open                         # インタラクティブモード
npx cypress run --browser chrome         # 特定ブラウザ
npx cypress run --spec "cypress/e2e/market*.cy.ts"  # 特定ファイル

# レポート表示
npx playwright show-report
npx playwright show-trace artifacts/trace.zip
```

## テストアーティファクト

### Playwright トレース

```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  use: {
    trace: 'retain-on-failure', // 失敗時のみ保存
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
})
```

```bash
# トレース表示
npx playwright show-trace test-results/trace.zip
```

### スクリーンショット

```typescript
// 手動取得
await page.screenshot({ path: 'artifacts/screenshot.png' })
await page.screenshot({ path: 'artifacts/full-page.png', fullPage: true })

// 要素のスクリーンショット
await page.locator('.chart').screenshot({ path: 'artifacts/chart.png' })

// 比較用スクリーンショット（ビジュアルリグレッション）
await expect(page).toHaveScreenshot('markets-page.png')
```

## CI/CD統合

### GitHub Actions

```yaml
# .github/workflows/e2e.yml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
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
      
      - name: Install Playwright browsers
        run: npx playwright install --with-deps
      
      - name: Run E2E tests
        run: npx playwright test
      
      - name: Upload artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: playwright-report/
```

## 設定ファイル

### playwright.config.ts

```typescript
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
})
```

### cypress.config.ts

```typescript
import { defineConfig } from 'cypress'

export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:3000',
    supportFile: 'cypress/support/e2e.ts',
    specPattern: 'cypress/e2e/**/*.cy.ts',
    viewportWidth: 1280,
    viewportHeight: 720,
    video: false,
    screenshotOnRunFailure: true,
  },
})
```

## プロジェクト構成例

```
project/
├── package.json
├── playwright.config.ts
├── tests/
│   └── e2e/
│       ├── pages/
│       │   ├── MarketsPage.ts
│       │   └── HomePage.ts
│       ├── fixtures/
│       │   └── test-data.ts
│       └── specs/
│           ├── market-search.spec.ts
│           └── user-flow.spec.ts
└── playwright-report/        # 自動生成
```

## ベストプラクティス

### 推奨事項

- `Playwright` を使用（自動待機、複数ブラウザ、トレース機能）
- Page Object パターンで保守性を向上
- `data-testid` 属性をセレクタに使用
- `getByRole`, `getByText` でアクセシビリティを考慮
- 重要なユーザーフローのみをE2Eでテスト
- トレースとスクリーンショットを活用
- CIでは複数ブラウザでテスト

### 避けるべきこと

- 脆いセレクタ（CSS クラス、nth-child）
- 任意の `waitForTimeout` 待機（APIレスポンス待機を使用）
- 本番環境でのテスト実行
- 全てのエッジケースをE2Eでテスト（ユニットテストを使用）
- テスト間でのデータ依存

## 関連ツール

| ツール | 用途 |
|--------|------|
| `@playwright/test` | E2Eテストフレームワーク（推奨） |
| `cypress` | E2Eテストフレームワーク（代替） |
| `@testing-library/playwright` | Testing Library統合 |
| `msw` | APIモック |
| `@faker-js/faker` | テストデータ生成 |
| `allure-playwright` | 高度なレポート生成 |
