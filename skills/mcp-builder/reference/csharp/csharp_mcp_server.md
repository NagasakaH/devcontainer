# C# MCP Server Implementation Guide

## Overview

This document provides C#/.NET-specific best practices and examples for implementing MCP servers using the official MCP SDK for C#. It covers project structure, server setup, tool registration patterns, input validation, error handling, and complete working examples.

---

## Quick Reference

### Key NuGet Packages

```xml
<PackageReference Include="ModelContextProtocol" Version="0.*" />
<PackageReference Include="Microsoft.Extensions.Hosting" Version="9.*" />
<PackageReference Include="Microsoft.Extensions.Logging.Console" Version="9.*" />
```

### Server Initialization

```csharp
using ModelContextProtocol.Server;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.DependencyInjection;

var builder = Host.CreateApplicationBuilder(args);
builder.Services.AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly();

var host = builder.Build();
await host.RunAsync();
```

### Tool Registration Pattern

```csharp
[McpServerToolType]
public static class MyTools
{
    [McpServerTool("tool_name"), Description("Tool description")]
    public static async Task<string> ToolName(
        [Description("Parameter description")] string param)
    {
        return $"Processed: {param}";
    }
}
```

---

## MCP C# SDK

The official MCP C# SDK provides:

- Native .NET integration with Microsoft.Extensions.Hosting
- Attribute-based tool registration with `[McpServerTool]`
- Dependency injection support for complex tools
- Async/await patterns for I/O operations

**For complete SDK documentation, visit:**
`https://github.com/modelcontextprotocol/csharp-sdk`

## Server Naming Convention

C# MCP servers should follow this naming pattern:

- **Format**: `{Service}McpServer` (PascalCase)
- **Examples**: `GitHubMcpServer`, `JiraMcpServer`, `StripeMcpServer`

The name should be:

- General (not tied to specific features)
- Descriptive of the service/API being integrated
- Easy to infer from the task description
- Without version numbers or dates

## Project Structure

Create the following structure for C# MCP servers:

```
{Service}McpServer/
├── {Service}McpServer.csproj
├── Program.cs                 # Main entry point
├── Tools/                     # Tool implementations
│   ├── SearchTools.cs
│   ├── CreateTools.cs
│   └── DeleteTools.cs
├── Services/                  # API clients and utilities
│   ├── ApiClient.cs
│   └── ErrorHandler.cs
├── Models/                    # Data models
│   └── ApiModels.cs
└── appsettings.json          # Configuration
```

## Tool Implementation

### Tool Naming

Use snake_case for tool names (e.g., `search_users`, `create_project`, `get_channel_info`) with clear, action-oriented names.

**Avoid Naming Conflicts**: Include the service context to prevent overlaps:

- Use `github_create_issue` instead of just `create_issue`
- Use `slack_send_message` instead of just `send_message`

### Tool Structure with Attributes

Tools are defined using the `[McpServerTool]` attribute:

```csharp
using System.ComponentModel;
using ModelContextProtocol.Server;

[McpServerToolType]
public static class UserTools
{
    [McpServerTool("example_search_users")]
    [Description(@"Search for users in the Example system by name, email, or team.

This tool searches across all user profiles in the Example platform, 
supporting partial matches and various search filters.

Args:
    query (string): Search string to match against names/emails
    limit (int): Maximum results to return, between 1-100 (default: 20)
    offset (int): Number of results to skip for pagination (default: 0)

Returns:
    JSON-formatted string with search results containing:
    - total: Total matches found
    - count: Results in this response
    - users: Array of user objects

Examples:
    - Find marketing team: query='team:marketing'
    - Search by name: query='john'")]
    public static async Task<string> SearchUsers(
        [Description("Search query to match against names/emails (e.g., 'john', 'team:marketing')")] 
        string query,
        [Description("Maximum results to return (1-100, default: 20)")] 
        int limit = 20,
        [Description("Number of results to skip for pagination (default: 0)")] 
        int offset = 0,
        CancellationToken cancellationToken = default)
    {
        // Input validation
        if (string.IsNullOrWhiteSpace(query))
            return "Error: Query cannot be empty";
        
        if (limit < 1 || limit > 100)
            return "Error: Limit must be between 1 and 100";
        
        if (offset < 0)
            return "Error: Offset cannot be negative";

        try
        {
            var client = new HttpClient();
            var response = await client.GetAsync(
                $"{ApiBaseUrl}/users/search?q={Uri.EscapeDataString(query)}&limit={limit}&offset={offset}",
                cancellationToken);
            
            response.EnsureSuccessStatusCode();
            var data = await response.Content.ReadFromJsonAsync<SearchResult>(cancellationToken);
            
            if (data?.Users == null || data.Users.Count == 0)
                return $"No users found matching '{query}'";
            
            return JsonSerializer.Serialize(new
            {
                total = data.Total,
                count = data.Users.Count,
                offset,
                users = data.Users,
                has_more = data.Total > offset + data.Users.Count
            }, new JsonSerializerOptions { WriteIndented = true });
        }
        catch (HttpRequestException ex)
        {
            return HandleApiError(ex);
        }
    }

    private const string ApiBaseUrl = "https://api.example.com/v1";
}
```

### Tool with Dependency Injection

For tools requiring services, use dependency injection:

```csharp
[McpServerToolType]
public class DatabaseTools
{
    private readonly IDbContext _dbContext;
    private readonly ILogger<DatabaseTools> _logger;

    public DatabaseTools(IDbContext dbContext, ILogger<DatabaseTools> logger)
    {
        _dbContext = dbContext;
        _logger = logger;
    }

    [McpServerTool("db_query_users")]
    [Description("Query users from the database with optional filters")]
    public async Task<string> QueryUsers(
        [Description("Optional name filter")] string? nameFilter = null,
        [Description("Maximum results")] int limit = 50)
    {
        _logger.LogInformation("Querying users with filter: {Filter}", nameFilter);
        
        var query = _dbContext.Users.AsQueryable();
        
        if (!string.IsNullOrEmpty(nameFilter))
            query = query.Where(u => u.Name.Contains(nameFilter));
        
        var users = await query.Take(limit).ToListAsync();
        
        return JsonSerializer.Serialize(users);
    }
}
```

## Data Models

Define clear models for input/output:

```csharp
// Models/ApiModels.cs
using System.Text.Json.Serialization;

public record SearchResult
{
    [JsonPropertyName("total")]
    public int Total { get; init; }
    
    [JsonPropertyName("users")]
    public List<User> Users { get; init; } = new();
}

public record User
{
    [JsonPropertyName("id")]
    public string Id { get; init; } = "";
    
    [JsonPropertyName("name")]
    public string Name { get; init; } = "";
    
    [JsonPropertyName("email")]
    public string Email { get; init; } = "";
    
    [JsonPropertyName("team")]
    public string? Team { get; init; }
    
    [JsonPropertyName("active")]
    public bool Active { get; init; } = true;
}

// Input validation with Data Annotations
using System.ComponentModel.DataAnnotations;

public record CreateUserInput
{
    [Required(ErrorMessage = "Name is required")]
    [StringLength(100, MinimumLength = 1)]
    public string Name { get; init; } = "";
    
    [Required]
    [EmailAddress(ErrorMessage = "Invalid email format")]
    public string Email { get; init; } = "";
    
    [Range(0, 150, ErrorMessage = "Age must be between 0 and 150")]
    public int? Age { get; init; }
}
```

## Response Formats

Support multiple output formats:

```csharp
public enum ResponseFormat
{
    Markdown,
    Json
}

[McpServerTool("search_with_format")]
public static async Task<string> SearchWithFormat(
    string query,
    [Description("Output format: 'Markdown' or 'Json' (default: Markdown)")]
    ResponseFormat format = ResponseFormat.Markdown)
{
    var results = await SearchApi(query);
    
    return format switch
    {
        ResponseFormat.Markdown => FormatAsMarkdown(results),
        ResponseFormat.Json => JsonSerializer.Serialize(results, 
            new JsonSerializerOptions { WriteIndented = true }),
        _ => throw new ArgumentException("Invalid format")
    };
}

private static string FormatAsMarkdown(SearchResult results)
{
    var sb = new StringBuilder();
    sb.AppendLine($"# Search Results");
    sb.AppendLine();
    sb.AppendLine($"Found {results.Total} users");
    sb.AppendLine();
    
    foreach (var user in results.Users)
    {
        sb.AppendLine($"## {user.Name} ({user.Id})");
        sb.AppendLine($"- **Email**: {user.Email}");
        if (!string.IsNullOrEmpty(user.Team))
            sb.AppendLine($"- **Team**: {user.Team}");
        sb.AppendLine();
    }
    
    return sb.ToString();
}
```

## Pagination Implementation

```csharp
[McpServerTool("list_items")]
[Description("List items with pagination support")]
public static async Task<string> ListItems(
    [Description("Maximum results (1-100, default: 20)")] int limit = 20,
    [Description("Pagination offset (default: 0)")] int offset = 0)
{
    var data = await FetchItems(limit, offset);
    
    var response = new
    {
        total = data.Total,
        count = data.Items.Count,
        offset,
        items = data.Items,
        has_more = data.Total > offset + data.Items.Count,
        next_offset = data.Total > offset + data.Items.Count 
            ? offset + data.Items.Count 
            : (int?)null
    };
    
    return JsonSerializer.Serialize(response, new JsonSerializerOptions { WriteIndented = true });
}
```

## Error Handling

Provide clear, actionable error messages:

```csharp
// Services/ErrorHandler.cs
public static class ErrorHandler
{
    public static string HandleApiError(HttpRequestException ex)
    {
        return ex.StatusCode switch
        {
            HttpStatusCode.NotFound => 
                "Error: Resource not found. Please check the ID is correct.",
            HttpStatusCode.Forbidden => 
                "Error: Permission denied. You don't have access to this resource.",
            HttpStatusCode.TooManyRequests => 
                "Error: Rate limit exceeded. Please wait before making more requests.",
            HttpStatusCode.Unauthorized =>
                "Error: Authentication failed. Please check your credentials.",
            _ => $"Error: API request failed with status {ex.StatusCode}"
        };
    }

    public static string HandleGeneralError(Exception ex)
    {
        return ex switch
        {
            TaskCanceledException => "Error: Request timed out. Please try again.",
            JsonException => "Error: Invalid response format from API.",
            _ => $"Error: Unexpected error occurred: {ex.GetType().Name}"
        };
    }
}
```

## Shared Utilities

Extract common functionality:

```csharp
// Services/ApiClient.cs
public class ApiClient
{
    private readonly HttpClient _httpClient;
    private readonly string _baseUrl;
    private const int DefaultTimeout = 30;

    public ApiClient(string baseUrl, string? apiKey = null)
    {
        _baseUrl = baseUrl;
        _httpClient = new HttpClient
        {
            Timeout = TimeSpan.FromSeconds(DefaultTimeout)
        };
        
        if (!string.IsNullOrEmpty(apiKey))
        {
            _httpClient.DefaultRequestHeaders.Authorization = 
                new AuthenticationHeaderValue("Bearer", apiKey);
        }
    }

    public async Task<T> GetAsync<T>(string endpoint, CancellationToken ct = default)
    {
        var response = await _httpClient.GetAsync($"{_baseUrl}/{endpoint}", ct);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<T>(ct) 
            ?? throw new JsonException("Null response");
    }

    public async Task<T> PostAsync<T>(string endpoint, object data, CancellationToken ct = default)
    {
        var response = await _httpClient.PostAsJsonAsync($"{_baseUrl}/{endpoint}", data, ct);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<T>(ct) 
            ?? throw new JsonException("Null response");
    }
}
```

## Async Best Practices

Always use async/await for I/O operations:

```csharp
// Good: Async HTTP request
public async Task<User> GetUserAsync(string userId, CancellationToken ct = default)
{
    var response = await _httpClient.GetAsync($"/users/{userId}", ct);
    response.EnsureSuccessStatusCode();
    return await response.Content.ReadFromJsonAsync<User>(ct)
        ?? throw new InvalidOperationException("User not found");
}

// Bad: Blocking call
public User GetUser(string userId)
{
    var response = _httpClient.GetAsync($"/users/{userId}").Result; // Blocks!
    return response.Content.ReadFromJsonAsync<User>().Result;
}
```

## Project Configuration

### .csproj

```xml
<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <RootNamespace>ExampleMcpServer</RootNamespace>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="ModelContextProtocol" Version="0.*" />
    <PackageReference Include="Microsoft.Extensions.Hosting" Version="9.*" />
    <PackageReference Include="Microsoft.Extensions.Logging.Console" Version="9.*" />
    <PackageReference Include="Microsoft.Extensions.Http" Version="9.*" />
  </ItemGroup>

</Project>
```

### Program.cs (Complete Example)

```csharp
using System.ComponentModel;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using ModelContextProtocol.Server;

// Build and configure the host
var builder = Host.CreateApplicationBuilder(args);

// Configure logging
builder.Logging.AddConsole();
builder.Logging.SetMinimumLevel(LogLevel.Warning);

// Add MCP server with stdio transport
builder.Services.AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly();

// Add custom services
builder.Services.AddHttpClient();

var host = builder.Build();
await host.RunAsync();

// Tool implementations
[McpServerToolType]
public static class ExampleTools
{
    private const string ApiBaseUrl = "https://api.example.com/v1";

    [McpServerTool("example_search_users")]
    [Description(@"Search for users in the Example system by name, email, or team.

This tool searches across all user profiles in the Example platform.

Args:
    query (string): Search string to match against names/emails
    limit (int): Maximum results (1-100, default: 20)
    offset (int): Pagination offset (default: 0)

Returns:
    JSON with total count, users array, and pagination info")]
    public static async Task<string> SearchUsers(
        [Description("Search query")] string query,
        [Description("Max results (1-100)")] int limit = 20,
        [Description("Pagination offset")] int offset = 0,
        CancellationToken ct = default)
    {
        if (string.IsNullOrWhiteSpace(query))
            return "Error: Query cannot be empty";
        
        limit = Math.Clamp(limit, 1, 100);
        offset = Math.Max(0, offset);

        try
        {
            using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(30) };
            var url = $"{ApiBaseUrl}/users/search?q={Uri.EscapeDataString(query)}&limit={limit}&offset={offset}";
            
            var response = await client.GetAsync(url, ct);
            response.EnsureSuccessStatusCode();
            
            var data = await response.Content.ReadFromJsonAsync<SearchResult>(ct);
            
            if (data?.Users == null || data.Users.Count == 0)
                return $"No users found matching '{query}'";

            return JsonSerializer.Serialize(new
            {
                total = data.Total,
                count = data.Users.Count,
                offset,
                users = data.Users.Select(u => new { u.Id, u.Name, u.Email, u.Team }),
                has_more = data.Total > offset + data.Users.Count,
                next_offset = data.Total > offset + data.Users.Count 
                    ? offset + data.Users.Count 
                    : (int?)null
            }, new JsonSerializerOptions { WriteIndented = true });
        }
        catch (HttpRequestException ex)
        {
            return HandleError(ex);
        }
        catch (Exception ex)
        {
            return $"Error: {ex.GetType().Name} - {ex.Message}";
        }
    }

    [McpServerTool("example_get_user")]
    [Description("Get detailed information about a specific user by ID")]
    public static async Task<string> GetUser(
        [Description("User ID (e.g., 'U123456789')")] string userId,
        CancellationToken ct = default)
    {
        if (string.IsNullOrWhiteSpace(userId))
            return "Error: User ID is required";

        try
        {
            using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(30) };
            var response = await client.GetAsync($"{ApiBaseUrl}/users/{Uri.EscapeDataString(userId)}", ct);
            response.EnsureSuccessStatusCode();
            
            var user = await response.Content.ReadFromJsonAsync<User>(ct);
            return JsonSerializer.Serialize(user, new JsonSerializerOptions { WriteIndented = true });
        }
        catch (HttpRequestException ex)
        {
            return HandleError(ex);
        }
    }

    private static string HandleError(HttpRequestException ex)
    {
        return ex.StatusCode switch
        {
            System.Net.HttpStatusCode.NotFound => "Error: Resource not found.",
            System.Net.HttpStatusCode.Forbidden => "Error: Permission denied.",
            System.Net.HttpStatusCode.TooManyRequests => "Error: Rate limit exceeded.",
            _ => $"Error: API request failed ({ex.StatusCode})"
        };
    }
}

// Data models
public record SearchResult
{
    [JsonPropertyName("total")]
    public int Total { get; init; }
    
    [JsonPropertyName("users")]
    public List<User> Users { get; init; } = new();
}

public record User
{
    [JsonPropertyName("id")]
    public string Id { get; init; } = "";
    
    [JsonPropertyName("name")]
    public string Name { get; init; } = "";
    
    [JsonPropertyName("email")]
    public string Email { get; init; } = "";
    
    [JsonPropertyName("team")]
    public string? Team { get; init; }
}
```

---

## Transport Options

### stdio (Default - Local Integration)

```csharp
builder.Services.AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly();
```

### SSE (Server-Sent Events - Remote)

```csharp
// In Program.cs for ASP.NET Core
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddMcpServer()
    .WithHttpTransport()
    .WithToolsFromAssembly();

var app = builder.Build();
app.MapMcp("/mcp");
app.Run();
```

**Transport selection:**

- **stdio**: Command-line tools, local development, subprocess integration
- **SSE/HTTP**: Web services, remote access, multiple clients

---

## Code Best Practices

### Code Composability and Reusability

1. **Extract Common Functionality**:
   - Create reusable services for API calls
   - Centralize error handling
   - Use extension methods for common operations

2. **Avoid Duplication**:
   - NEVER copy-paste similar code between tools
   - Common operations should be in shared services
   - Use generic methods where appropriate

### C#-Specific Best Practices

1. **Use Nullable Reference Types**: Enable `<Nullable>enable</Nullable>`
2. **Use Records**: For immutable data transfer objects
3. **Use Pattern Matching**: For error handling and type checking
4. **Use CancellationToken**: For all async operations
5. **Use IAsyncEnumerable**: For streaming large datasets
6. **Use Source Generators**: When available for performance

## Quality Checklist

### Strategic Design

- [ ] Tools enable complete workflows
- [ ] Tool names follow `service_action_target` pattern
- [ ] Response formats optimize for agent comprehension
- [ ] Error messages guide agents toward correct usage

### Implementation Quality

- [ ] All tools have `[McpServerTool]` attribute with name
- [ ] All tools have `[Description]` attribute with comprehensive documentation
- [ ] All parameters have `[Description]` attributes with examples
- [ ] Input validation is implemented for all parameters
- [ ] Async operations use `CancellationToken`

### Code Quality

- [ ] Nullable reference types enabled
- [ ] No `#nullable disable`
- [ ] Records used for DTOs
- [ ] HttpClient properly managed (IHttpClientFactory or using)
- [ ] JSON serialization options consistent

### Project Configuration

- [ ] Target framework is .NET 8.0+
- [ ] ImplicitUsings enabled
- [ ] Nullable enabled
- [ ] MCP SDK referenced

### Testing

- [ ] `dotnet build` completes without errors
- [ ] `dotnet run` starts server successfully
- [ ] Tools respond correctly via MCP Inspector
