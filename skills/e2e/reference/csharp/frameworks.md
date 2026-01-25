---
sidebar_position: 1769331671
date: 2026-01-25T09:01:11+00:00
---

# C# E2Eテストフレームワーク

C#/.NETでエンドツーエンドテストを実践するためのフレームワークとツールガイド。

## テストフレームワーク

### Playwright for .NET（推奨）

Microsoftが開発したモダンなブラウザ自動化ツール。TypeScript版と同じAPIを提供。

```csharp
// Tests/E2E/MarketSearchTests.cs
using Microsoft.Playwright;
using Xunit;

public class MarketSearchTests : IAsyncLifetime
{
    private IPlaywright _playwright = null!;
    private IBrowser _browser = null!;
    private IPage _page = null!;

    public async Task InitializeAsync()
    {
        _playwright = await Playwright.CreateAsync();
        _browser = await _playwright.Chromium.LaunchAsync();
        _page = await _browser.NewPageAsync();
    }

    public async Task DisposeAsync()
    {
        await _browser.CloseAsync();
        _playwright.Dispose();
    }

    [Fact]
    public async Task UserCanSearchAndFilterMarkets()
    {
        // 1. ホームページに移動
        await _page.GotoAsync("http://localhost:3000/");
        
        // 2. 市場ページに移動
        await _page.ClickAsync("a[href='/markets']");
        
        // 3. 検索を実行
        await _page.FillAsync("input[placeholder='検索']", "election");
        await _page.WaitForTimeoutAsync(600); // デバウンス待機
        
        // 4. 結果を検証
        var results = _page.Locator("[data-testid='market-card']");
        await Expect(results).ToHaveCountAsync(5);
    }

    [Fact]
    public async Task UserCanViewMarketDetails()
    {
        await _page.GotoAsync("http://localhost:3000/markets");
        
        // 最初の市場カードをクリック
        await _page.Locator("[data-testid='market-card']").First.ClickAsync();
        
        // 詳細ページが表示されることを確認
        await Expect(_page.Locator("h1")).ToBeVisibleAsync();
        await Expect(_page.Locator("[data-testid='market-chart']")).ToBeVisibleAsync();
    }
}
```

### Selenium WebDriver

最も広く使用されているブラウザ自動化ツール。.NETで長い歴史を持つ。

```csharp
// Tests/E2E/MarketSearchTests.cs
using OpenQA.Selenium;
using OpenQA.Selenium.Chrome;
using OpenQA.Selenium.Support.UI;
using Xunit;

public class MarketSearchTests : IDisposable
{
    private readonly IWebDriver _driver;
    private readonly WebDriverWait _wait;

    public MarketSearchTests()
    {
        _driver = new ChromeDriver();
        _driver.Manage().Timeouts().ImplicitWait = TimeSpan.FromSeconds(10);
        _wait = new WebDriverWait(_driver, TimeSpan.FromSeconds(10));
    }

    public void Dispose()
    {
        _driver.Quit();
    }

    [Fact]
    public void UserCanSearchAndFilterMarkets()
    {
        // 1. ホームページに移動
        _driver.Navigate().GoToUrl("http://localhost:3000/");
        
        // 2. 市場ページに移動
        _driver.FindElement(By.CssSelector("a[href='/markets']")).Click();
        
        // 3. 検索を実行
        var searchInput = _driver.FindElement(By.CssSelector("input[placeholder='検索']"));
        searchInput.SendKeys("election");
        
        // 4. 結果を待機
        _wait.Until(d => d.FindElements(By.CssSelector("[data-testid='market-card']")).Count > 0);
        
        // 5. 結果を検証
        var results = _driver.FindElements(By.CssSelector("[data-testid='market-card']"));
        Assert.Equal(5, results.Count);
    }

    [Fact]
    public void UserCanViewMarketDetails()
    {
        _driver.Navigate().GoToUrl("http://localhost:3000/markets");
        
        // 最初の市場カードをクリック
        var cards = _driver.FindElements(By.CssSelector("[data-testid='market-card']"));
        cards[0].Click();
        
        // 詳細ページが表示されることを確認
        _wait.Until(d => d.FindElement(By.TagName("h1")).Displayed);
        Assert.True(_driver.FindElement(By.CssSelector("[data-testid='market-chart']")).Displayed);
    }
}
```

### SpecFlow（BDDスタイル）

Cucumber/Gherkin構文を使用したBDDフレームワーク。

```gherkin
# Features/MarketSearch.feature
Feature: 市場検索
  ユーザーとして
  市場を検索してフィルタリングしたい
  投資対象を見つけるために

  Scenario: 市場を検索する
    Given ホームページにアクセスする
    When 市場ページに移動する
    And 検索フィールドに "election" と入力する
    Then 5件の市場カードが表示される
```

```csharp
// Steps/MarketSearchSteps.cs
using TechTalk.SpecFlow;
using Microsoft.Playwright;

[Binding]
public class MarketSearchSteps
{
    private readonly IPage _page;

    public MarketSearchSteps(IPage page)
    {
        _page = page;
    }

    [Given(@"ホームページにアクセスする")]
    public async Task GivenGoToHome()
    {
        await _page.GotoAsync("http://localhost:3000/");
    }

    [When(@"市場ページに移動する")]
    public async Task WhenGoToMarkets()
    {
        await _page.ClickAsync("a[href='/markets']");
    }

    [When(@"検索フィールドに ""(.*)"" と入力する")]
    public async Task WhenSearchKeyword(string keyword)
    {
        await _page.FillAsync("input[placeholder='検索']", keyword);
        await _page.WaitForTimeoutAsync(600);
    }

    [Then(@"(\d+)件の市場カードが表示される")]
    public async Task ThenVerifyResults(int count)
    {
        var results = _page.Locator("[data-testid='market-card']");
        await Expect(results).ToHaveCountAsync(count);
    }
}
```

## Page Object パターン

```csharp
// Pages/MarketsPage.cs
using Microsoft.Playwright;

public class MarketsPage
{
    private readonly IPage _page;
    
    public ILocator SearchInput => _page.Locator("input[placeholder='検索']");
    public ILocator MarketCards => _page.Locator("[data-testid='market-card']");
    public ILocator FilterButtons => _page.Locator("[data-testid='filter-button']");

    public MarketsPage(IPage page)
    {
        _page = page;
    }

    public async Task GotoAsync()
    {
        await _page.GotoAsync("http://localhost:3000/markets");
    }

    public async Task SearchAsync(string keyword)
    {
        await SearchInput.FillAsync(keyword);
        await _page.WaitForTimeoutAsync(600); // デバウンス待機
    }

    public async Task ApplyFilterAsync(string filterName)
    {
        await FilterButtons.Filter(new() { HasText = filterName }).ClickAsync();
    }

    public async Task<int> GetMarketCountAsync()
    {
        return await MarketCards.CountAsync();
    }

    public async Task ClickFirstMarketAsync()
    {
        await MarketCards.First.ClickAsync();
    }
}

// 使用例
[Fact]
public async Task SearchMarkets()
{
    var marketsPage = new MarketsPage(_page);
    await marketsPage.GotoAsync();
    await marketsPage.SearchAsync("election");
    
    Assert.Equal(5, await marketsPage.GetMarketCountAsync());
}
```

## アサーション

### Playwright Expect

```csharp
using static Microsoft.Playwright.Assertions;

// 要素の可視性
await Expect(_page.Locator("h1")).ToBeVisibleAsync();
await Expect(_page.Locator(".modal")).ToBeHiddenAsync();

// テキスト
await Expect(_page.Locator("h1")).ToHaveTextAsync("市場一覧");
await Expect(_page.Locator("h1")).ToContainTextAsync("市場");

// 属性
await Expect(_page.Locator("input")).ToHaveValueAsync("election");
await Expect(_page.Locator("button")).ToBeEnabledAsync();
await Expect(_page.Locator("input")).ToBeDisabledAsync();

// 数
await Expect(_page.Locator(".item")).ToHaveCountAsync(5);

// URL
await Expect(_page).ToHaveURLAsync("/markets");
await Expect(_page).ToHaveTitleAsync("市場 | MyApp");
```

### Selenium + FluentAssertions

```csharp
using FluentAssertions;

// 基本的なアサーション
_driver.Title.Should().Be("市場 | MyApp");
_driver.FindElement(By.TagName("h1")).Text.Should().Contain("市場");
_driver.FindElement(By.CssSelector(".modal")).Displayed.Should().BeTrue();

// コレクション
var cards = _driver.FindElements(By.CssSelector("[data-testid='market-card']"));
cards.Should().HaveCount(5);
```

## 実行コマンド

```bash
# dotnet test
dotnet test                                     # 全テスト実行
dotnet test --filter "Category=E2E"             # E2Eテストのみ
dotnet test --filter "FullyQualifiedName~MarketSearch"  # 名前でフィルタ

# Playwright CLI
playwright install                              # ブラウザインストール
playwright codegen http://localhost:3000        # テストコード生成

# 詳細出力
dotnet test -v detailed

# 並列実行
dotnet test --parallel
```

## テストアーティファクト

### Playwright トレース

```csharp
// トレース記録を開始
await _context.Tracing.StartAsync(new()
{
    Screenshots = true,
    Snapshots = true,
    Sources = true
});

// テスト実行後
await _context.Tracing.StopAsync(new()
{
    Path = "artifacts/trace.zip"
});

// トレース表示
// playwright show-trace artifacts/trace.zip
```

### スクリーンショット

```csharp
// 手動取得
await _page.ScreenshotAsync(new() { Path = "artifacts/screenshot.png" });
await _page.ScreenshotAsync(new() { Path = "artifacts/full-page.png", FullPage = true });

// 失敗時に自動取得
public async Task DisposeAsync()
{
    if (TestContext.CurrentContext.Result.Outcome == ResultState.Failure)
    {
        await _page.ScreenshotAsync(new()
        {
            Path = $"artifacts/failure-{TestContext.CurrentContext.Test.Name}.png"
        });
    }
    await _browser.CloseAsync();
}
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
      
      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.0.x'
      
      - name: Install dependencies
        run: dotnet restore
      
      - name: Build
        run: dotnet build --no-restore
      
      - name: Install Playwright browsers
        run: pwsh bin/Debug/net8.0/playwright.ps1 install --with-deps
      
      - name: Run E2E tests
        run: dotnet test --filter "Category=E2E" --logger "trx;LogFileName=results.trx"
      
      - name: Upload artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: |
            **/artifacts/
            **/*.trx
```

## プロジェクト構成例

```
Solution/
├── Solution.sln
├── src/
│   └── MyApp/
│       └── MyApp.csproj
├── tests/
│   ├── MyApp.UnitTests/
│   │   └── MyApp.UnitTests.csproj
│   └── MyApp.E2ETests/
│       ├── MyApp.E2ETests.csproj
│       ├── Pages/
│       │   ├── MarketsPage.cs
│       │   └── HomePage.cs
│       ├── Tests/
│       │   └── MarketSearchTests.cs
│       └── Fixtures/
│           └── PlaywrightFixture.cs
```

### テストプロジェクトファイル（.csproj）

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <IsPackable>false</IsPackable>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.*" />
    <PackageReference Include="Microsoft.Playwright" Version="1.*" />
    <PackageReference Include="xunit" Version="2.*" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.*" />
    <PackageReference Include="FluentAssertions" Version="6.*" />
  </ItemGroup>
</Project>
```

## ベストプラクティス

### 推奨事項

- `Playwright for .NET` を使用（モダン、高速、TypeScript版と同じAPI）
- Page Object パターンで保守性を向上
- `data-testid` 属性をセレクタに使用
- `IAsyncLifetime` でセットアップ・クリーンアップを管理
- テストカテゴリでE2Eテストを分離
- トレースとスクリーンショットを活用

### 避けるべきこと

- 脆いセレクタ（CSS クラス、XPath の深いパス）
- `Thread.Sleep()` での任意の待機
- 本番環境でのテスト実行
- 全てのエッジケースをE2Eでテスト
- テスト間でのデータ依存

## 関連ツール

| ツール | 用途 |
|--------|------|
| `Microsoft.Playwright` | ブラウザ自動化（推奨） |
| `Selenium.WebDriver` | ブラウザ自動化（レガシー） |
| `SpecFlow` | BDDスタイルテスト |
| `FluentAssertions` | 可読性の高いアサーション |
| `Bogus` | テストデータ生成 |
| `WireMock.Net` | APIモック |
