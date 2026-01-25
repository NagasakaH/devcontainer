---
sidebar_position: 1769331678
date: 2026-01-25T09:01:18+00:00
---

# C# - デッドコード検出ツール

## 推奨ツール

| ツール | 検出対象 | インストール |
|--------|----------|--------------|
| Roslyn Analyzers | 未使用コード全般 | NuGetパッケージ |
| ReSharper | 未使用コード・依存関係 | JetBrains製品 |
| dotnet format | コードスタイル違反 | .NET SDK内蔵 |
| NDepend | 未使用コード・依存関係分析 | 商用ツール |

## コマンド例

### Roslyn Analyzers（推奨）

```bash
# ビルド時にアナライザーを有効化
dotnet build /p:EnforceCodeStyleInBuild=true

# 警告をエラーとして扱う
dotnet build -warnaserror

# 特定の警告のみチェック
dotnet build /p:TreatWarningsAsErrors=true /p:WarningsAsErrors=CS0219,CS0168
```

### dotnet format

```bash
# アナライザー診断を含めて検証
dotnet format --verify-no-changes --diagnostics IDE0051 IDE0052 IDE0059 IDE0060

# 自動修正
dotnet format --diagnostics IDE0051 IDE0052 IDE0059 IDE0060
```

### 未使用パッケージの検出

```bash
# 依存関係の一覧表示
dotnet list package

# 推移的依存関係を含めて表示
dotnet list package --include-transitive

# 未使用パッケージの特定（手動確認用）
dotnet list package --outdated
```

## 設定ファイル例

### .editorconfig（Roslyn Analyzers設定）

```ini
# 未使用のprivateメンバー
dotnet_diagnostic.IDE0051.severity = warning

# 未使用のprivateメンバー（読み取られない）
dotnet_diagnostic.IDE0052.severity = warning

# 未使用の値の代入
dotnet_diagnostic.IDE0059.severity = warning

# 未使用のパラメーター
dotnet_diagnostic.IDE0060.severity = warning

# 未使用のローカル変数
dotnet_diagnostic.CS0168.severity = warning
dotnet_diagnostic.CS0219.severity = warning
```

### Directory.Build.props（プロジェクト全体設定）

```xml
<Project>
  <PropertyGroup>
    <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <AnalysisLevel>latest</AnalysisLevel>
    <EnableNETAnalyzers>true</EnableNETAnalyzers>
  </PropertyGroup>

  <ItemGroup>
    <!-- Roslynアナライザーパッケージ -->
    <PackageReference Include="Microsoft.CodeAnalysis.NetAnalyzers" Version="8.0.0">
      <PrivateAssets>all</PrivateAssets>
      <IncludeAssets>runtime; build; native; contentfiles; analyzers</IncludeAssets>
    </PackageReference>
  </ItemGroup>
</Project>
```

### .csproj（プロジェクト単位設定）

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Microsoft.CodeAnalysis.NetAnalyzers" Version="8.0.0">
      <PrivateAssets>all</PrivateAssets>
    </PackageReference>
  </ItemGroup>
</Project>
```

## 診断コード一覧

| コード | 説明 |
|--------|------|
| IDE0051 | 未使用のprivateメンバー |
| IDE0052 | 読み取られないprivateメンバー |
| IDE0059 | 未使用の値の代入 |
| IDE0060 | 未使用のパラメーター |
| CS0168 | 宣言されたが使用されない変数 |
| CS0219 | 割り当てられたが使用されない変数 |
| CS0414 | 代入されたが読み取られないフィールド |

## CI/CD統合例

### GitHub Actions

```yaml
- name: Build with analyzers
  run: |
    dotnet build -warnaserror /p:EnforceCodeStyleInBuild=true

- name: Check code format
  run: |
    dotnet format --verify-no-changes --diagnostics IDE0051 IDE0052 IDE0059 IDE0060
```

### Azure DevOps

```yaml
- task: DotNetCoreCLI@2
  displayName: 'Build with analyzers'
  inputs:
    command: 'build'
    arguments: '-warnaserror /p:EnforceCodeStyleInBuild=true'
```

## 注意事項

- **リフレクション**: リフレクションで呼び出されるメンバーは誤検出される可能性あり
- **シリアライゼーション**: JSONシリアライズ用のプロパティは属性で明示
- **DIコンテナ**: 依存性注入で使用されるクラスは誤検出に注意
- **テストプロジェクト**: テストメソッドは `[Fact]` や `[Test]` 属性で認識される
