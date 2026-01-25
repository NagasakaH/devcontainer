# C# メタデータファイル読み取りガイド

## 概要

C#/.NETプロジェクトのメタデータ（スクリプト、依存関係、設定）を読み取る方法を説明します。

---

## メタデータファイル一覧

| ファイル | 用途 | 優先度 |
|----------|------|--------|
| `*.csproj` | プロジェクト設定（MSBuild形式） | 高 |
| `*.sln` | ソリューションファイル | 高 |
| `Directory.Build.props` | 共通プロパティ設定 | 中 |
| `Directory.Build.targets` | 共通ターゲット設定 | 中 |
| `global.json` | SDKバージョン指定 | 中 |
| `nuget.config` | NuGet設定 | 低 |

---

## .csproj からの情報抽出

### 基本構造

```xml
<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <OutputType>Exe</OutputType>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <RootNamespace>MyProject</RootNamespace>
    <AssemblyName>my-project</AssemblyName>
    <Version>1.0.0</Version>
    <Description>プロジェクトの説明</Description>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" Version="9.0.0" />
    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
  </ItemGroup>

  <ItemGroup Condition="'$(Configuration)' == 'Debug'">
    <PackageReference Include="xunit" Version="2.6.2" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.5.4" />
  </ItemGroup>

</Project>
```

### XML解析による情報抽出

```csharp
using System.Xml.Linq;

public class CsprojParser
{
    public record ProjectMetadata(
        string? Name,
        string? Version,
        string? TargetFramework,
        List<PackageReference> Dependencies,
        Dictionary<string, string> Properties
    );

    public record PackageReference(string Name, string Version);

    public static ProjectMetadata Parse(string csprojPath)
    {
        var doc = XDocument.Load(csprojPath);
        var ns = doc.Root?.GetDefaultNamespace() ?? XNamespace.None;
        
        var properties = new Dictionary<string, string>();
        var dependencies = new List<PackageReference>();
        
        // PropertyGroup から情報抽出
        foreach (var propGroup in doc.Descendants("PropertyGroup"))
        {
            foreach (var prop in propGroup.Elements())
            {
                properties[prop.Name.LocalName] = prop.Value;
            }
        }
        
        // PackageReference から依存関係抽出
        foreach (var pkgRef in doc.Descendants("PackageReference"))
        {
            var include = pkgRef.Attribute("Include")?.Value;
            var version = pkgRef.Attribute("Version")?.Value 
                ?? pkgRef.Element("Version")?.Value;
            
            if (!string.IsNullOrEmpty(include))
            {
                dependencies.Add(new PackageReference(include, version ?? "*"));
            }
        }
        
        return new ProjectMetadata(
            Name: properties.GetValueOrDefault("AssemblyName") 
                ?? Path.GetFileNameWithoutExtension(csprojPath),
            Version: properties.GetValueOrDefault("Version"),
            TargetFramework: properties.GetValueOrDefault("TargetFramework"),
            Dependencies: dependencies,
            Properties: properties
        );
    }
}
```

### Bash/PowerShellでの抽出

```bash
# パッケージ参照の一覧を取得（bash）
grep -oP 'PackageReference Include="\K[^"]+' *.csproj

# バージョン付きで取得
grep -E 'PackageReference' *.csproj | sed 's/.*Include="\([^"]*\)".*Version="\([^"]*\)".*/\1 \2/'
```

```powershell
# PowerShellでの抽出
[xml]$csproj = Get-Content *.csproj
$csproj.Project.ItemGroup.PackageReference | 
    Select-Object Include, Version | 
    Format-Table
```

---

## 利用可能なコマンドの自動検出

### 標準 dotnet コマンド

```bash
# ビルド
dotnet build

# リリースビルド
dotnet build -c Release

# 実行
dotnet run

# テスト実行
dotnet test

# カバレッジ付きテスト
dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=cobertura

# パッケージ復元
dotnet restore

# クリーン
dotnet clean

# フォーマット
dotnet format

# パブリッシュ
dotnet publish -c Release -o ./publish
```

### カスタムターゲットの検出

```xml
<!-- .csprojのカスタムターゲット例 -->
<Target Name="GenerateVersion" BeforeTargets="Build">
  <Exec Command="git describe --tags" ConsoleToMSBuild="true">
    <Output TaskParameter="ConsoleOutput" PropertyName="GitVersion" />
  </Exec>
</Target>

<Target Name="RunMigrations" AfterTargets="Build">
  <Exec Command="dotnet ef database update" />
</Target>
```

```bash
# カスタムターゲットの実行
dotnet msbuild -t:GenerateVersion
dotnet msbuild -t:RunMigrations
```

### ターゲット一覧の取得

```bash
# 利用可能なターゲット一覧
dotnet msbuild -targets

# または
dotnet msbuild -pp > preprocessed.xml
grep -oP 'Target Name="\K[^"]+' preprocessed.xml | sort -u
```

---

## ソリューションファイル (.sln) の解析

### 基本構造

```sln
Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 17
Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "MyProject", "src\MyProject\MyProject.csproj", "{GUID}"
EndProject
Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "MyProject.Tests", "tests\MyProject.Tests\MyProject.Tests.csproj", "{GUID}"
EndProject
```

### プロジェクト一覧の取得

```bash
# slnファイルからプロジェクトパスを抽出
grep -oP '= "[^"]+", "\K[^"]+\.csproj' *.sln
```

```csharp
public static List<string> GetProjectsFromSolution(string slnPath)
{
    var projects = new List<string>();
    var lines = File.ReadAllLines(slnPath);
    
    foreach (var line in lines)
    {
        var match = Regex.Match(line, @"= ""[^""]+"", ""([^""]+\.csproj)""");
        if (match.Success)
        {
            var projectPath = match.Groups[1].Value.Replace("\\", "/");
            projects.Add(projectPath);
        }
    }
    
    return projects;
}
```

---

## global.json の解析

### 基本構造

```json
{
  "sdk": {
    "version": "8.0.100",
    "rollForward": "latestMinor"
  },
  "msbuild-sdks": {
    "Microsoft.Build.Traversal": "4.1.0"
  }
}
```

### パース方法

```csharp
public record GlobalJson(
    SdkConfig? Sdk,
    Dictionary<string, string>? MsbuildSdks
);

public record SdkConfig(
    string? Version,
    string? RollForward
);

public static GlobalJson? ParseGlobalJson(string path)
{
    if (!File.Exists(path)) return null;
    
    var json = File.ReadAllText(path);
    return JsonSerializer.Deserialize<GlobalJson>(json, new JsonSerializerOptions
    {
        PropertyNameCaseInsensitive = true,
        PropertyNamingPolicy = JsonNamingPolicy.KebabCaseLower
    });
}
```

---

## Directory.Build.props の解析

### 基本構造

```xml
<Project>
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <LangVersion>latest</LangVersion>
  </PropertyGroup>
  
  <ItemGroup>
    <!-- 全プロジェクト共通の依存関係 -->
    <PackageReference Include="Microsoft.Extensions.Logging.Abstractions" Version="9.0.0" />
  </ItemGroup>
</Project>
```

---

## ドキュメント生成テンプレート

### 利用可能なコマンド

```markdown
## 利用可能なコマンド

### ビルドとテスト

| コマンド | 説明 |
|----------|------|
| `dotnet build` | プロジェクトをビルド |
| `dotnet build -c Release` | リリースビルド |
| `dotnet test` | テストを実行 |
| `dotnet test --collect:"XPlat Code Coverage"` | カバレッジ付きテスト |

### 開発

| コマンド | 説明 |
|----------|------|
| `dotnet run` | アプリケーションを実行 |
| `dotnet watch run` | ホットリロード付きで実行 |
| `dotnet format` | コードフォーマット |
| `dotnet restore` | 依存関係を復元 |

### パブリッシュ

| コマンド | 説明 |
|----------|------|
| `dotnet publish -c Release` | リリース用にパブリッシュ |
| `dotnet publish -c Release --self-contained` | 自己完結型パブリッシュ |
```

### 依存関係

```markdown
## 依存関係

### 本番依存関係

| パッケージ | バージョン | 用途 |
|------------|------------|------|
| Microsoft.Extensions.Hosting | 9.0.0 | 汎用ホスト |
| Newtonsoft.Json | 13.0.3 | JSON処理 |

### 開発依存関係

| パッケージ | バージョン | 用途 |
|------------|------------|------|
| xunit | 2.6.2 | テストフレームワーク |
| Moq | 4.20.70 | モックライブラリ |
| coverlet.collector | 6.0.0 | カバレッジ収集 |
```

---

## 統合パース関数

```csharp
using System.Text.Json;
using System.Xml.Linq;

public class DotNetProjectMetadata
{
    public string? Name { get; set; }
    public string? Version { get; set; }
    public string? TargetFramework { get; set; }
    public string? SdkVersion { get; set; }
    public List<PackageInfo> Dependencies { get; set; } = new();
    public List<string> Projects { get; set; } = new();
    public Dictionary<string, string> Scripts { get; set; } = new();
}

public record PackageInfo(string Name, string Version, bool IsDev);

public static class DotNetMetadataExtractor
{
    public static DotNetProjectMetadata Extract(string projectRoot)
    {
        var metadata = new DotNetProjectMetadata();
        
        // global.json から SDK バージョンを取得
        var globalJsonPath = Path.Combine(projectRoot, "global.json");
        if (File.Exists(globalJsonPath))
        {
            var json = JsonDocument.Parse(File.ReadAllText(globalJsonPath));
            if (json.RootElement.TryGetProperty("sdk", out var sdk))
            {
                if (sdk.TryGetProperty("version", out var version))
                {
                    metadata.SdkVersion = version.GetString();
                }
            }
        }
        
        // .sln から全プロジェクトを取得
        var slnFiles = Directory.GetFiles(projectRoot, "*.sln");
        if (slnFiles.Length > 0)
        {
            metadata.Projects = GetProjectsFromSolution(slnFiles[0]);
        }
        
        // .csproj から詳細を取得
        var csprojFiles = Directory.GetFiles(projectRoot, "*.csproj", SearchOption.AllDirectories);
        foreach (var csproj in csprojFiles)
        {
            var project = ParseCsproj(csproj);
            
            if (metadata.Name == null && !csproj.Contains(".Tests"))
            {
                metadata.Name = project.Name;
                metadata.Version = project.Version;
                metadata.TargetFramework = project.TargetFramework;
            }
            
            foreach (var dep in project.Dependencies)
            {
                var isDev = csproj.Contains(".Tests") || 
                            dep.Name.Contains("xunit") || 
                            dep.Name.Contains("Moq");
                
                if (!metadata.Dependencies.Any(d => d.Name == dep.Name))
                {
                    metadata.Dependencies.Add(new PackageInfo(dep.Name, dep.Version, isDev));
                }
            }
        }
        
        // 標準スクリプトを追加
        metadata.Scripts = new Dictionary<string, string>
        {
            ["build"] = "dotnet build",
            ["test"] = "dotnet test",
            ["run"] = "dotnet run",
            ["publish"] = "dotnet publish -c Release",
            ["format"] = "dotnet format",
            ["restore"] = "dotnet restore"
        };
        
        return metadata;
    }

    private static (string? Name, string? Version, string? TargetFramework, List<(string Name, string Version)> Dependencies) 
        ParseCsproj(string path)
    {
        var doc = XDocument.Load(path);
        var props = new Dictionary<string, string>();
        var deps = new List<(string, string)>();
        
        foreach (var prop in doc.Descendants().Where(e => e.Parent?.Name.LocalName == "PropertyGroup"))
        {
            props[prop.Name.LocalName] = prop.Value;
        }
        
        foreach (var pkgRef in doc.Descendants("PackageReference"))
        {
            var include = pkgRef.Attribute("Include")?.Value;
            var version = pkgRef.Attribute("Version")?.Value ?? "*";
            if (include != null)
            {
                deps.Add((include, version));
            }
        }
        
        return (
            props.GetValueOrDefault("AssemblyName") ?? Path.GetFileNameWithoutExtension(path),
            props.GetValueOrDefault("Version"),
            props.GetValueOrDefault("TargetFramework"),
            deps
        );
    }

    private static List<string> GetProjectsFromSolution(string slnPath)
    {
        var projects = new List<string>();
        foreach (var line in File.ReadLines(slnPath))
        {
            var match = Regex.Match(line, @"= ""[^""]+"", ""([^""]+\.csproj)""");
            if (match.Success)
            {
                projects.Add(match.Groups[1].Value.Replace("\\", "/"));
            }
        }
        return projects;
    }
}
```
