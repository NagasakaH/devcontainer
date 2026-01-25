---
name: e2e
description: E2Eテストの生成・実行ガイド。テストジャーニーの作成、テスト実行、スクリーンショット/動画/トレースの取得、アーティファクトのアップロードをサポート。「E2Eテスト」「エンドツーエンドテスト」「Playwrightテスト」「ユーザージャーニーのテスト」などのフレーズで発動。
---

# E2Eテスト生成（E2E）

エンドツーエンドテストを生成・保守・実行するためのガイド。

## 対応言語

このスキルは以下の言語に対応しています。プロジェクトの言語を自動検出し、適切なテストフレームワークとコマンドを使用します。

| 言語 | E2Eフレームワーク | 詳細 |
|------|------------------|------|
| TypeScript/JavaScript | Playwright, Cypress | [reference/typescript/frameworks.md](reference/typescript/frameworks.md) |
| Python | Playwright for Python, Selenium | [reference/python/frameworks.md](reference/python/frameworks.md) |
| C# | Playwright for .NET, Selenium | [reference/csharp/frameworks.md](reference/csharp/frameworks.md) |

### 言語自動検出

プロジェクトの言語は以下のファイルの存在で判別します：

| ファイル | 判定される言語 |
|----------|----------------|
| `package.json` | TypeScript/JavaScript |
| `pyproject.toml`, `setup.py`, `requirements.txt` | Python |
| `*.csproj`, `*.sln` | C# |

`{{language}}` 変数が指定された場合は、その言語の設定を優先します。

## このスキルの目的

1. **テストジャーニーの生成** - ユーザーフローのPlaywrightテストを作成
2. **E2Eテストの実行** - 複数ブラウザでテストを実行
3. **アーティファクトの取得** - 失敗時のスクリーンショット、動画、トレースを保存
4. **結果のアップロード** - HTMLレポートとJUnit XMLを生成
5. **不安定なテストの検出** - 不安定なテストを特定・隔離

## 使用するタイミング

以下の場合に使用：
- 重要なユーザージャーニーのテスト（ログイン、決済、購入フロー等）
- 複数ステップのフローがエンドツーエンドで動作することの検証
- UIインタラクションとナビゲーションのテスト
- フロントエンドとバックエンドの統合検証
- 本番デプロイ前の品質確認

## ワークフロー

### ステップ1: ユーザーフローの分析

リクエストを分析し、テストシナリオを特定する。

- ユーザージャーニーの流れ
- テストで検証すべき項目
- 必要なテストケース数

### ステップ2: E2Eテストの生成

Page Object Modelパターンを使用してテストコードを生成する。

テストには以下を含める：
- ナビゲーション
- ユーザーアクション
- アサーション（検証）
- スクリーンショット取得

### ステップ3: テストの実行

複数ブラウザでテストを実行する。

対象ブラウザ：
- Chromium（デスクトップChrome）
- Firefox（デスクトップ）
- WebKit（デスクトップSafari）
- Mobile Chrome（オプション）

### ステップ4: 結果の報告

テスト結果とアーティファクトを報告する。

- 成功/失敗の状態
- 実行時間
- 生成されたアーティファクト
- 推奨事項（必要に応じて）

## 言語別テストコード例

以下に各言語でのE2Eテスト例を示します。詳細な情報は各言語のリファレンスを参照してください。

### TypeScript/JavaScript (Playwright)

```typescript
// tests/e2e/market-search.spec.ts
import { test, expect } from '@playwright/test'
import { MarketsPage } from '../pages/MarketsPage'

test.describe('市場検索', () => {
  test('ユーザーは市場を検索してフィルタリングできる', async ({ page }) => {
    // 1. ページへ移動
    const marketsPage = new MarketsPage(page)
    await marketsPage.goto()

    // 2. 検索を実行
    await marketsPage.search('election')

    // 3. 結果を検証
    await expect(marketsPage.marketCards).toHaveCount(5)
  })
})
```

**テスト実行:**

```bash
npx playwright test
npx playwright test --headed  # ブラウザ表示
npx playwright show-report    # レポート表示
```

### Python (Playwright for Python)

```python
# tests/e2e/test_market_search.py
from playwright.sync_api import Page, expect
from pages.markets_page import MarketsPage

class TestMarketSearch:
    def test_user_can_search_and_filter_markets(self, page: Page):
        # 1. ページへ移動
        markets_page = MarketsPage(page)
        markets_page.goto()

        # 2. 検索を実行
        markets_page.search('election')

        # 3. 結果を検証
        expect(markets_page.market_cards).to_have_count(5)
```

**テスト実行:**

```bash
pytest tests/e2e/
pytest tests/e2e/ --headed  # ブラウザ表示
```

### C# (Playwright for .NET)

```csharp
// Tests/E2E/MarketSearchTests.cs
using Microsoft.Playwright;
using Xunit;

public class MarketSearchTests : PlaywrightTest
{
    [Fact]
    public async Task UserCanSearchAndFilterMarkets()
    {
        // 1. ページへ移動
        var marketsPage = new MarketsPage(Page);
        await marketsPage.GotoAsync();

        // 2. 検索を実行
        await marketsPage.SearchAsync("election");

        // 3. 結果を検証
        await Expect(marketsPage.MarketCards).ToHaveCountAsync(5);
    }
}
```

**テスト実行:**

```bash
dotnet test
dotnet test --filter "Category=E2E"
```

## テストコードテンプレート（TypeScript）

```typescript
// tests/e2e/{機能名}/{テスト名}.spec.ts
import { test, expect } from '@playwright/test'
import { {ページ名}Page } from '../../pages/{ページ名}Page'

test.describe('{テストスイート名}', () => {
  test('{テストケース名}', async ({ page }) => {
    // 1. ページへ移動
    const targetPage = new {ページ名}Page(page)
    await targetPage.goto()

    // 2. ページ読み込みを検証
    await expect(page).toHaveTitle(/{期待するタイトル}/)
    await expect(page.locator('h1')).toContainText('{期待するテキスト}')

    // 3. ユーザーアクションを実行
    await targetPage.{アクションメソッド}('{入力値}')

    // 4. APIレスポンスを待機
    await page.waitForResponse(resp =>
      resp.url().includes('{APIエンドポイント}') && resp.status() === 200
    )

    // 5. 結果を検証
    await expect(page.locator('{セレクタ}')).toBeVisible()

    // 6. スクリーンショットを取得
    await page.screenshot({ path: 'artifacts/{スクリーンショット名}.png' })
  })
})
```

## Page Objectテンプレート

```typescript
// tests/pages/{ページ名}Page.ts
import { Page, Locator } from '@playwright/test'

export class {ページ名}Page {
  readonly page: Page
  readonly {要素名}: Locator

  constructor(page: Page) {
    this.page = page
    this.{要素名} = page.locator('[data-testid="{テストID}"]')
  }

  async goto() {
    await this.page.goto('{URL}')
  }

  async {アクションメソッド}(input: string) {
    await this.{要素名}.fill(input)
    await this.{要素名}.press('Enter')
  }
}
```

## テストアーティファクト

テスト実行時に以下のアーティファクトを取得：

**全テストで取得：**
- HTMLレポート（タイムラインと結果）
- JUnit XML（CI統合用）

**失敗時のみ取得：**
- 失敗状態のスクリーンショット
- テストの動画記録
- デバッグ用トレースファイル（ステップバイステップ再生）
- ネットワークログ
- コンソールログ

## クイックコマンド

### TypeScript/JavaScript (Playwright)

```bash
# 全E2Eテストを実行
npx playwright test

# 特定のテストファイルを実行
npx playwright test tests/e2e/market-search.spec.ts

# ヘッドモードで実行（ブラウザを表示）
npx playwright test --headed

# デバッグモードで実行
npx playwright test --debug

# テストコードを生成
npx playwright codegen http://localhost:3000

# レポートを表示
npx playwright show-report

# トレースファイルを表示
npx playwright show-trace artifacts/trace.zip
```

### Python (Playwright for Python)

```bash
# 全E2Eテストを実行
pytest tests/e2e/

# ヘッドモードで実行
pytest tests/e2e/ --headed

# 特定のブラウザで実行
pytest tests/e2e/ --browser chromium

# トレース記録
pytest tests/e2e/ --tracing on
```

### C# (Playwright for .NET)

```bash
# 全E2Eテストを実行
dotnet test --filter "Category=E2E"

# 詳細出力
dotnet test -v detailed

# Playwrightブラウザインストール
pwsh bin/Debug/net8.0/playwright.ps1 install
```

## 不安定なテストの検出

テストが断続的に失敗する場合：

1. **原因の特定**
   - タイムアウト問題
   - レース条件
   - アニメーションによる要素の非表示

2. **推奨される修正**
   - 明示的な待機を追加: `await page.waitForSelector('{セレクタ}')`
   - タイムアウトを増加: `{ timeout: 10000 }`
   - コンポーネント内のレース条件を確認
   - アニメーションによる要素非表示を検証

3. **隔離の推奨**
   - 修正まで `test.fixme()` でマーク

## ベストプラクティス

**推奨事項：**
- Page Object Modelを使用して保守性を向上
- セレクタには `data-testid` 属性を使用
- 任意の待ち時間ではなくAPIレスポンスを待機
- 重要なユーザージャーニーをエンドツーエンドでテスト
- mainへのマージ前にテストを実行
- 失敗時はアーティファクトを確認

**避けるべきこと：**
- 脆いセレクタの使用（CSSクラスは変更される可能性がある）
- 実装の詳細をテスト
- 本番環境でテストを実行
- 不安定なテストを無視
- 失敗時のアーティファクト確認をスキップ
- 全てのエッジケースをE2Eでテスト（ユニットテストを使用）

## CI/CD統合

```yaml
# .github/workflows/e2e.yml
- name: Install Playwright
  run: npx playwright install --with-deps

- name: Run E2E tests
  run: npx playwright test

- name: Upload artifacts
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: playwright-report/
```

## 重要な注意事項

**本番環境での注意点：**
- 金銭が関わるE2Eテストはテストネット/ステージング環境のみで実行
- 本番環境で決済・取引テストを実行しない
- 金融関連テストには `test.skip(process.env.NODE_ENV === 'production')` を設定
- テスト用のウォレット/アカウントのみを使用

## 他のスキルとの連携

- **plan**: テストすべき重要なジャーニーを特定
- **tdd**: ユニットテスト用（より高速で詳細）
- **e2e**: 統合テストとユーザージャーニーテスト用
- **code-review**: テスト品質の検証
