# C# テストカバレッジコマンドリファレンス

## テスト実行コマンド

### dotnet test + Coverlet（推奨）

```bash
# 基本的なカバレッジ付きテスト実行
dotnet test /p:CollectCoverage=true

# コンソールにカバレッジ結果を表示
dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=cobertura

# JSON形式で出力
dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=json

# 複数形式で同時出力
dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=\"json,cobertura\"

# 閾値を設定（80%未満で失敗）
dotnet test /p:CollectCoverage=true /p:Threshold=80

# 特定のプロジェクトを除外
dotnet test /p:CollectCoverage=true /p:Exclude=\"[*.Tests]*\"
```

### dotnet-coverage ツール（.NET SDK組み込み）

```bash
# dotnet-coverageをインストール
dotnet tool install --global dotnet-coverage

# カバレッジ付きでテスト実行
dotnet-coverage collect dotnet test

# Cobertura形式で出力
dotnet-coverage collect -f cobertura dotnet test
```

### Visual Studio組み込みカバレッジ

```bash
# Visual Studio Enterprise のみ
dotnet test --collect:"Code Coverage"

# レポートを特定フォルダに出力
dotnet test --collect:"Code Coverage" --results-directory ./TestResults
```

## カバレッジレポートファイルのパス

| 形式 | 出力パス | 用途 |
|------|----------|------|
| JSON | `coverage.json` | プログラム解析 |
| Cobertura (XML) | `coverage.cobertura.xml` | CI/CD連携、ReportGenerator |
| OpenCover | `coverage.opencover.xml` | ReportGenerator連携 |
| LCOV | `coverage.info` | 汎用フォーマット |

## 主要なツール・フレームワーク

### テストフレームワーク

- **xUnit** - 最も広く使われているテストフレームワーク
- **NUnit** - 歴史あるテストフレームワーク
- **MSTest** - Microsoftの公式テストフレームワーク

### カバレッジツール

- **Coverlet** - クロスプラットフォームのOSSカバレッジツール（推奨）
- **dotnet-coverage** - .NET SDK組み込みツール
- **Visual Studio Code Coverage** - Enterprise版専用

### レポート生成

- **ReportGenerator** - HTMLレポート生成ツール

## 設定ファイル例

### Coverlet設定（.csproj）

```xml
<PropertyGroup>
  <CollectCoverage>true</CollectCoverage>
  <CoverletOutputFormat>cobertura</CoverletOutputFormat>
  <CoverletOutput>./coverage/</CoverletOutput>
  <Threshold>80</Threshold>
  <ThresholdType>line</ThresholdType>
  <ExcludeByFile>**/Migrations/**</ExcludeByFile>
</PropertyGroup>
```

### coverlet.runsettings

```xml
<?xml version="1.0" encoding="utf-8"?>
<RunSettings>
  <DataCollectionRunSettings>
    <DataCollectors>
      <DataCollector friendlyName="XPlat code coverage">
        <Configuration>
          <Format>cobertura</Format>
          <Exclude>[*]*.Migrations.*</Exclude>
          <ExcludeByAttribute>Obsolete,GeneratedCodeAttribute</ExcludeByAttribute>
        </Configuration>
      </DataCollector>
    </DataCollectors>
  </DataCollectionRunSettings>
</RunSettings>
```

使用方法：

```bash
dotnet test --settings coverlet.runsettings
```

## HTMLレポート生成

ReportGeneratorを使用してHTMLレポートを生成：

```bash
# ReportGeneratorをインストール
dotnet tool install --global dotnet-reportgenerator-globaltool

# HTMLレポート生成
reportgenerator -reports:coverage.cobertura.xml -targetdir:coveragereport -reporttypes:Html

# 複数のレポートをマージ
reportgenerator -reports:**/coverage.cobertura.xml -targetdir:coveragereport -reporttypes:Html
```

## CI/CD連携（GitHub Actions例）

```yaml
- name: Run tests with coverage
  run: |
    dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=cobertura

- name: Generate coverage report
  run: |
    dotnet tool install --global dotnet-reportgenerator-globaltool
    reportgenerator -reports:**/coverage.cobertura.xml -targetdir:coveragereport -reporttypes:Html

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    files: "**/coverage.cobertura.xml"
```

## カバレッジ閾値の設定

```bash
# 行カバレッジ80%未満で失敗
dotnet test /p:CollectCoverage=true /p:Threshold=80 /p:ThresholdType=line

# 分岐カバレッジも含める
dotnet test /p:CollectCoverage=true /p:Threshold=\"80,70\" /p:ThresholdType=\"line,branch\"
```
