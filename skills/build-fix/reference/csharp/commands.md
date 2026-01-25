# C# ビルドコマンドリファレンス

## ビルドコマンド

### dotnet build（推奨）

```bash
# 基本的なビルド
dotnet build

# Releaseビルド
dotnet build -c Release

# 特定のプロジェクト
dotnet build MyProject.csproj

# 詳細なログ出力
dotnet build -v detailed

# 警告をエラーとして扱う
dotnet build /warnaserror

# 並列ビルド
dotnet build /m

# クリーンビルド
dotnet clean && dotnet build
```

### dotnet publish（配布用）

```bash
# 基本的なパブリッシュ
dotnet publish -c Release

# 自己完結型
dotnet publish -c Release --self-contained true -r win-x64

# 単一ファイル
dotnet publish -c Release -r win-x64 /p:PublishSingleFile=true

# トリミング（未使用コードを削除）
dotnet publish -c Release -r win-x64 /p:PublishTrimmed=true
```

### dotnet restore（依存関係復元）

```bash
# NuGetパッケージの復元
dotnet restore

# 特定のソース
dotnet restore --source https://api.nuget.org/v3/index.json
```

### MSBuild（高度な制御）

```bash
# MSBuildを直接使用
dotnet msbuild

# 特定のターゲット
dotnet msbuild /t:Build

# プロパティを指定
dotnet msbuild /p:Configuration=Release
```

## ビルド出力ディレクトリ

| 構成 | 出力パス |
|------|----------|
| Debug | `bin/Debug/{framework}/` |
| Release | `bin/Release/{framework}/` |
| Publish | `bin/Release/{framework}/publish/` |

例: `bin/Debug/net8.0/`

## 主要なビルドツール

- **dotnet CLI** - .NET SDK組み込みのビルドツール
- **MSBuild** - Microsoft Build Engine（dotnet CLIが内部で使用）
- **Visual Studio** - IDE統合ビルド
- **dotnet watch** - ファイル変更時の自動再ビルド

## 設定ファイル例

### .csproj（プロジェクトファイル）

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <WarningLevel>5</WarningLevel>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
  </ItemGroup>
</Project>
```

### Directory.Build.props（共通設定）

```xml
<Project>
  <PropertyGroup>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <Nullable>enable</Nullable>
    <LangVersion>latest</LangVersion>
  </PropertyGroup>
</Project>
```

### global.json（SDK バージョン固定）

```json
{
  "sdk": {
    "version": "8.0.100",
    "rollForward": "latestFeature"
  }
}
```

## 一般的なエラーと解決方法

### CS0246: 型または名前空間が見つからない

```bash
# NuGetパッケージを復元
dotnet restore

# パッケージを追加
dotnet add package PackageName
```

### CS0103: 名前がコンテキストに存在しない

- usingディレクティブの追加を確認
- 名前空間の確認

### CS8600-CS8603: Null許容警告

```csharp
// null許容参照型の対応
string? nullableString = GetValue();
if (nullableString != null)
{
    // 安全に使用
}
```

### MSB3027: ファイルをコピーできない

```bash
# プロセスがファイルを使用中の場合
# アプリケーションを停止してからビルド
dotnet clean
dotnet build
```

### NETSDK1045: SDKバージョンが必要

```bash
# .NET SDKのバージョンを確認
dotnet --list-sdks

# 必要なバージョンをインストール
# https://dotnet.microsoft.com/download
```

## リアルタイムビルド（ウォッチモード）

```bash
# ファイル変更時に自動再ビルド
dotnet watch build

# ビルドと実行
dotnet watch run

# テストを監視
dotnet watch test
```

## CI/CD連携（GitHub Actions例）

```yaml
- name: Setup .NET
  uses: actions/setup-dotnet@v3
  with:
    dotnet-version: '8.0.x'

- name: Restore dependencies
  run: dotnet restore

- name: Build
  run: dotnet build --no-restore -c Release /warnaserror

- name: Test
  run: dotnet test --no-build -c Release

- name: Publish
  run: dotnet publish -c Release -o ./publish
```

## 診断・デバッグ

```bash
# ビルドの詳細ログ
dotnet build -v diag > build.log

# バイナリログ（MSBuild Structured Log Viewer用）
dotnet build /bl

# 依存関係グラフを表示
dotnet list package --include-transitive
```
