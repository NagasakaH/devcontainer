---
sidebar_position: 1769331678
date: 2026-01-25T09:01:18+00:00
---

# C# - 検証ツール

## 検証コマンド一覧

### ビルドチェック

```bash
# 通常ビルド
dotnet build

# Releaseビルド
dotnet build -c Release

# 警告をエラーとして扱う
dotnet build -warnaserror

# クリーンビルド
dotnet clean && dotnet build
```

### 型チェック

C#はコンパイル言語のため、ビルド時に型チェックが実行されます。

```bash
# 型チェック（ビルドと同時）
dotnet build -warnaserror

# アナライザーを有効化
dotnet build /p:EnforceCodeStyleInBuild=true

# Nullable参照型の警告を厳格に
dotnet build /p:Nullable=enable /p:TreatWarningsAsErrors=true
```

### リントチェック

```bash
# dotnet format（コードスタイル検証）
dotnet format --verify-no-changes

# 特定の診断のみチェック
dotnet format --verify-no-changes --diagnostics IDE0051 IDE0052

# 自動修正
dotnet format

# アナライザー診断を含める
dotnet format analyzers --verify-no-changes
```

### テスト実行

```bash
# テスト実行
dotnet test

# カバレッジ付き（Coverlet使用）
dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=cobertura

# 詳細出力
dotnet test -v normal

# 特定のテストのみ
dotnet test --filter "FullyQualifiedName~MyTest"
```

### デバッグ出力検索

```bash
# Console.WriteLine の検索
grep -rn "Console.WriteLine" --include="*.cs" src/

# Debug.WriteLine の検索
grep -rn "Debug.WriteLine" --include="*.cs" src/

# Trace の検索
grep -rn "Trace\." --include="*.cs" src/
```

## 設定ファイル例

### .editorconfig

```ini
root = true

[*.cs]
# インデント
indent_style = space
indent_size = 4

# コードスタイル
csharp_style_var_for_built_in_types = true:suggestion
csharp_style_var_when_type_is_apparent = true:suggestion

# 未使用コード警告
dotnet_diagnostic.IDE0051.severity = error
dotnet_diagnostic.IDE0052.severity = error
dotnet_diagnostic.IDE0059.severity = warning
dotnet_diagnostic.CS0168.severity = error
dotnet_diagnostic.CS0219.severity = error
```

### Directory.Build.props

```xml
<Project>
  <PropertyGroup>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
    <AnalysisLevel>latest</AnalysisLevel>
    <EnableNETAnalyzers>true</EnableNETAnalyzers>
    <Nullable>enable</Nullable>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Microsoft.CodeAnalysis.NetAnalyzers" Version="8.0.0">
      <PrivateAssets>all</PrivateAssets>
    </PackageReference>
    <PackageReference Include="coverlet.collector" Version="6.0.0">
      <PrivateAssets>all</PrivateAssets>
    </PackageReference>
  </ItemGroup>
</Project>
```

### テストプロジェクト設定（.csproj）

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <IsPackable>false</IsPackable>
    <IsTestProject>true</IsTestProject>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.8.0" />
    <PackageReference Include="xunit" Version="2.6.4" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.5.6" />
    <PackageReference Include="coverlet.collector" Version="6.0.0" />
  </ItemGroup>
</Project>
```

## CI/CD統合例

### GitHub Actions

```yaml
name: Verify .NET

on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.0.x'
      
      - name: Restore
        run: dotnet restore
      
      - name: Build
        run: dotnet build -warnaserror /p:EnforceCodeStyleInBuild=true
      
      - name: Format check
        run: dotnet format --verify-no-changes
      
      - name: Test
        run: dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=cobertura
      
      - name: Check for debug output
        run: |
          if grep -rn "Console.WriteLine" --include="*.cs" src/; then
            echo "Found Console.WriteLine in source code"
            exit 1
          fi
```

### Azure DevOps

```yaml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

steps:
  - task: UseDotNet@2
    inputs:
      packageType: 'sdk'
      version: '8.0.x'

  - script: dotnet build -warnaserror
    displayName: 'Build'

  - script: dotnet format --verify-no-changes
    displayName: 'Format check'

  - script: dotnet test /p:CollectCoverage=true
    displayName: 'Test'
```

## 検証結果の解釈

| チェック | 成功条件 |
|----------|----------|
| ビルド | エラーなしで完了、警告0件（-warnaserror時） |
| 型チェック | コンパイルエラーなし |
| リント | dotnet format が変更を検出しない |
| テスト | 全テストがパス |
| デバッグ出力 | Console.WriteLineがsrc/内にない |
