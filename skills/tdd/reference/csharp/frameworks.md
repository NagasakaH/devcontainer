---
sidebar_position: 1769331671
date: 2026-01-25T09:01:11+00:00
---

# C# テストフレームワーク

TDD（テスト駆動開発）をC#/.NETで実践するためのフレームワークとツールガイド。

## テストフレームワーク

### xUnit（推奨）

.NETで最も広く使用されているテストフレームワーク。.NET Core/5+のデフォルト選択。

```csharp
// Tests/LiquidityTests.cs
using Xunit;

public class CalculateLiquidityScoreTests
{
    [Fact]
    public void HighLiquidity_ReturnsHighScore()
    {
        // Arrange
        var market = new MarketData(
            TotalVolume: 100000,
            BidAskSpread: 0.01,
            ActiveTraders: 500,
            LastTradeTime: DateTime.Now
        );
        
        // Act
        var score = LiquidityCalculator.CalculateLiquidityScore(market);
        
        // Assert
        Assert.True(score > 80);
        Assert.True(score <= 100);
    }
    
    [Fact]
    public void ZeroVolume_ReturnsZero()
    {
        var market = new MarketData(
            TotalVolume: 0,
            BidAskSpread: 0,
            ActiveTraders: 0,
            LastTradeTime: DateTime.Now
        );
        
        var score = LiquidityCalculator.CalculateLiquidityScore(market);
        
        Assert.Equal(0, score);
    }
    
    [Theory]
    [InlineData(100, 0)]
    [InlineData(1000, 20)]
    [InlineData(10000, 50)]
    [InlineData(100000, 80)]
    public void VolumeAffectsScore(double volume, double expectedMin)
    {
        var market = new MarketData(
            TotalVolume: volume,
            BidAskSpread: 0.01,
            ActiveTraders: 100,
            LastTradeTime: DateTime.Now
        );
        
        var score = LiquidityCalculator.CalculateLiquidityScore(market);
        
        Assert.True(score >= expectedMin);
    }
}
```

### NUnit

長い歴史を持つ成熟したフレームワーク。JUnitに似た構文。

```csharp
// Tests/LiquidityTests.cs
using NUnit.Framework;

[TestFixture]
public class CalculateLiquidityScoreTests
{
    [Test]
    public void HighLiquidity_ReturnsHighScore()
    {
        var market = new MarketData(
            TotalVolume: 100000,
            BidAskSpread: 0.01,
            ActiveTraders: 500,
            LastTradeTime: DateTime.Now
        );
        
        var score = LiquidityCalculator.CalculateLiquidityScore(market);
        
        Assert.That(score, Is.GreaterThan(80));
        Assert.That(score, Is.LessThanOrEqualTo(100));
    }
    
    [Test]
    public void ZeroVolume_ReturnsZero()
    {
        var market = new MarketData(
            TotalVolume: 0,
            BidAskSpread: 0,
            ActiveTraders: 0,
            LastTradeTime: DateTime.Now
        );
        
        var score = LiquidityCalculator.CalculateLiquidityScore(market);
        
        Assert.That(score, Is.EqualTo(0));
    }
    
    [TestCase(100, 0)]
    [TestCase(1000, 20)]
    [TestCase(10000, 50)]
    [TestCase(100000, 80)]
    public void VolumeAffectsScore(double volume, double expectedMin)
    {
        var market = new MarketData(
            TotalVolume: volume,
            BidAskSpread: 0.01,
            ActiveTraders: 100,
            LastTradeTime: DateTime.Now
        );
        
        var score = LiquidityCalculator.CalculateLiquidityScore(market);
        
        Assert.That(score, Is.GreaterThanOrEqualTo(expectedMin));
    }
}
```

### MSTest

Microsoftの公式テストフレームワーク。Visual Studioとの統合が優れている。

```csharp
// Tests/LiquidityTests.cs
using Microsoft.VisualStudio.TestTools.UnitTesting;

[TestClass]
public class CalculateLiquidityScoreTests
{
    [TestMethod]
    public void HighLiquidity_ReturnsHighScore()
    {
        var market = new MarketData(
            TotalVolume: 100000,
            BidAskSpread: 0.01,
            ActiveTraders: 500,
            LastTradeTime: DateTime.Now
        );
        
        var score = LiquidityCalculator.CalculateLiquidityScore(market);
        
        Assert.IsTrue(score > 80);
        Assert.IsTrue(score <= 100);
    }
    
    [TestMethod]
    public void ZeroVolume_ReturnsZero()
    {
        var market = new MarketData(
            TotalVolume: 0,
            BidAskSpread: 0,
            ActiveTraders: 0,
            LastTradeTime: DateTime.Now
        );
        
        var score = LiquidityCalculator.CalculateLiquidityScore(market);
        
        Assert.AreEqual(0, score);
    }
    
    [DataTestMethod]
    [DataRow(100, 0)]
    [DataRow(1000, 20)]
    [DataRow(10000, 50)]
    [DataRow(100000, 80)]
    public void VolumeAffectsScore(double volume, double expectedMin)
    {
        var market = new MarketData(
            TotalVolume: volume,
            BidAskSpread: 0.01,
            ActiveTraders: 100,
            LastTradeTime: DateTime.Now
        );
        
        var score = LiquidityCalculator.CalculateLiquidityScore(market);
        
        Assert.IsTrue(score >= expectedMin);
    }
}
```

## アサーションライブラリ

### FluentAssertions（推奨）

自然言語に近い構文で可読性の高いアサーション。

```csharp
using FluentAssertions;

// 基本的なアサーション
result.Should().Be(expected);
result.Should().BeGreaterThan(threshold);
result.Should().BeInRange(min, max);
result.Should().BeNull();
result.Should().BeOfType<SomeClass>();

// コレクション
list.Should().HaveCount(5);
list.Should().Contain(item);
list.Should().BeInAscendingOrder();

// 例外のテスト
action.Should().Throw<InvalidOperationException>()
    .WithMessage("*invalid*");

// 浮動小数点の近似比較
result.Should().BeApproximately(expected, precision: 0.001);

// オブジェクト比較
actual.Should().BeEquivalentTo(expected);
```

### xUnit 組み込み

```csharp
// 基本的なアサーション
Assert.Equal(expected, actual);
Assert.True(condition);
Assert.False(condition);
Assert.Null(value);
Assert.NotNull(value);
Assert.IsType<SomeClass>(value);

// 例外のテスト
Assert.Throws<InvalidOperationException>(() => MethodThatThrows());
await Assert.ThrowsAsync<InvalidOperationException>(() => AsyncMethodThatThrows());

// コレクション
Assert.Contains(item, collection);
Assert.Empty(collection);
Assert.Single(collection);
```

## モックライブラリ

### Moq（推奨）

```csharp
using Moq;

// 基本的なモック
var mockService = new Mock<IDataService>();
mockService.Setup(s => s.GetData(It.IsAny<int>()))
    .Returns(new Data { Value = "test" });

var result = sut.ProcessData(mockService.Object);

mockService.Verify(s => s.GetData(42), Times.Once);

// 非同期メソッドのモック
mockService.Setup(s => s.GetDataAsync(It.IsAny<int>()))
    .ReturnsAsync(new Data { Value = "test" });

// 例外を投げる
mockService.Setup(s => s.GetData(It.Is<int>(i => i < 0)))
    .Throws<ArgumentException>();

// コールバック
mockService.Setup(s => s.SaveData(It.IsAny<Data>()))
    .Callback<Data>(d => savedData.Add(d));
```

### NSubstitute

```csharp
using NSubstitute;

// 基本的なモック
var mockService = Substitute.For<IDataService>();
mockService.GetData(Arg.Any<int>()).Returns(new Data { Value = "test" });

var result = sut.ProcessData(mockService);

mockService.Received(1).GetData(42);

// 非同期メソッドのモック
mockService.GetDataAsync(Arg.Any<int>()).Returns(Task.FromResult(new Data()));

// 例外を投げる
mockService.GetData(Arg.Is<int>(i => i < 0)).Returns(x => throw new ArgumentException());
```

## 実行コマンド

```bash
# dotnet test でテスト実行
dotnet test

# 特定のプロジェクト
dotnet test tests/MyProject.Tests

# 特定のテスト
dotnet test --filter "FullyQualifiedName~CalculateLiquidityScore"

# 詳細出力
dotnet test -v detailed

# カバレッジ付き（coverlet）
dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=cobertura

# 並列実行
dotnet test --parallel

# 失敗時のログ出力
dotnet test --logger "console;verbosity=detailed"
```

## カバレッジ

### Coverlet（推奨）

```bash
# パッケージ追加
dotnet add package coverlet.collector

# カバレッジ付きでテスト実行
dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=cobertura

# HTMLレポート生成（ReportGenerator使用）
dotnet tool install -g dotnet-reportgenerator-globaltool
reportgenerator -reports:coverage.cobertura.xml -targetdir:coveragereport

# 最小カバレッジを強制
dotnet test /p:CollectCoverage=true /p:Threshold=80
```

**カバレッジレポートパス**: `coverage.cobertura.xml` または `coveragereport/index.html`

## プロジェクト構成例

```
Solution/
├── Solution.sln
├── src/
│   └── MyProject/
│       ├── MyProject.csproj
│       └── Services/
│           └── LiquidityCalculator.cs
├── tests/
│   └── MyProject.Tests/
│       ├── MyProject.Tests.csproj
│       ├── Services/
│       │   └── LiquidityCalculatorTests.cs
│       └── Fixtures/
│           └── MarketDataFixture.cs
└── Directory.Build.props
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
    <PackageReference Include="xunit" Version="2.*" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.*" />
    <PackageReference Include="FluentAssertions" Version="6.*" />
    <PackageReference Include="Moq" Version="4.*" />
    <PackageReference Include="coverlet.collector" Version="6.*" />
  </ItemGroup>

  <ItemGroup>
    <ProjectReference Include="..\..\src\MyProject\MyProject.csproj" />
  </ItemGroup>
</Project>
```

## ベストプラクティス

### 推奨事項

- `xUnit` + `FluentAssertions` + `Moq` の組み合わせ
- テストメソッド名は `{メソッド名}_{シナリオ}_{期待結果}` 形式
- `Theory` / `TestCase` でパラメータ化テストを活用
- `IClassFixture` で高コストなセットアップを共有
- async/await を適切に使用
- `record` 型でテストデータを定義

### 避けるべきこと

- テスト間で状態を共有（各テストは独立すべき）
- コンストラクタでのテストセットアップ（フィクスチャを使用）
- 静的状態への依存
- 実装の詳細をテスト（振る舞いをテスト）
- `Thread.Sleep` の使用（適切な待機を使用）

## 関連ツール

| ツール | 用途 |
|--------|------|
| `xUnit` / `NUnit` / `MSTest` | テストフレームワーク |
| `FluentAssertions` | アサーションライブラリ |
| `Moq` / `NSubstitute` | モックライブラリ |
| `Coverlet` | カバレッジ計測 |
| `ReportGenerator` | カバレッジレポート生成 |
| `AutoFixture` | テストデータ自動生成 |
| `Bogus` | フェイクデータ生成 |
| `Verify` | スナップショットテスト |
