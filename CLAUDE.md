# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a custom DevContainer environment setup that provides integrated development environments using the `vimcontainer` script. The project combines custom DevContainer features with a shared LazyVim configuration (from git submodule) to create consistent, reproducible development environments across different projects.

## Essential Commands

### Installation
```bash
# Initial setup - installs devcontainer CLI and adds bin/ to PATH
./install.sh

# After installation, source your shell config
source ~/.bashrc  # or ~/.zshrc
```

### Using vimcontainer
```bash
# Start a .NET development environment
vimcontainer ~/git/devcontainer/devcontainers/dotnet ~/path/to/your/project

# Rebuild container (required after changing devcontainer config)
vimcontainer -r ~/git/devcontainer/devcontainers/dotnet ~/path/to/your/project
```

**Arguments:**
- First: Path to `.devcontainer` folder or its parent directory
- Second: Project workspace path to mount in container

**Options:**
- `-r, --rebuild`: Force rebuild of the container

## Architecture

### vimcontainer Script (`bin/vimcontainer`)

The core script creates and manages DevContainer environments with these key behaviors:

1. **Container Reuse**: Containers are identified by workspace path hash (`md5sum | cut -c1-8`), ensuring the same workspace always reuses the same container
2. **Temporary Workspace**: Creates `/tmp/vimcontainer-{HASH}` for each unique workspace path
3. **Automatic Feature Injection**: Copies local features (`tree-sitter`, `easydotnet`, `luarocks`) from `features/` into temp `.devcontainer` and merges them into `devcontainer.json` using `jq`
4. **Auto-adds postCreateCommand**: If not present in original devcontainer.json, adds `dotnet restore` command for .NET projects
5. **Shared LazyVim Config**: Mounts `submodules/LazyVim` to `/home/vscode/.config/nvim` (shared across all containers)
6. **Additional Features**: Auto-injects public features (neovim, ripgrep, deno, node, tmux) via `--additional-features` flag

### Mount Structure

| Host | Container | Purpose |
|------|-----------|---------|
| `{WORKSPACE_PATH}` | `/workspaces/{basename}` | Project files |
| `submodules/LazyVim` | `/home/vscode/.config/nvim` | Shared Neovim config |
| `dotfiles/.tmux.conf` | `/home/vscode/.tmux.conf` | tmux config |

**Note**: nvim data/state directories (`.local/share/nvim`, `.local/state/nvim`) are container-specific and not shared.

### Custom DevContainer Features

Located in `features/` directory:

**tree-sitter** (`features/tree-sitter/`)
- Installs tree-sitter CLI from prebuilt binaries
- Default version: 0.25.10 (configurable)
- Supports amd64/arm64 architectures

**easydotnet** (`features/easydotnet/`)
- Installs .NET development toolchain:
  - `easydotnet` CLI tool
  - `dotnet-ef` (Entity Framework Core CLI v8.0.11)
  - `netcoredbg` (v3.1.0-1030) - .NET debugger for nvim-dap
- Auto-configures PATH via `/etc/profile.d/dotnet-tools.sh`

**luarocks** (`features/luarocks/`)
- Installs Lua package manager

### LazyVim Submodule

- **Location**: `submodules/LazyVim`
- **Source**: `git@github.com:NagasakaH/LazyVim.git`
- **Auto-initialization**: vimcontainer auto-runs `git submodule update --init` if not initialized
- **Plugin Customization**: Add user-specific plugins to `submodules/LazyVim/lua/plugins/` (not `~/.config/nvim/`)

### DevContainer Templates

**devcontainers/dotnet/**
- Base image: `mcr.microsoft.com/vscode/devcontainers/dotnet:8.0-bookworm`
- Platform: `linux/amd64` (for Apple Silicon compatibility)
- Includes: OmniSharp LSP, nvim-dap with netcoredbg
- Auto-runs: `dotnet restore` on container creation

**devcontainers/react/**
- Currently empty template (placeholder)

## Development Workflow

### .NET Development

When working on .NET projects in this repo:

1. The easydotnet feature provides integration with `easy-dotnet.nvim` plugin
2. LSP (OmniSharp) auto-starts for C# files
3. Debugging setup:
   - `netcoredbg` is pre-installed via easydotnet feature
   - nvim-dap and nvim-dap-ui are configured in LazyVim
   - Use standard nvim-dap commands (`:lua require('dap').toggle_breakpoint()`, etc.)
4. `postCreateCommand` automatically runs `dotnet restore` on first container creation

### Modifying Features

When editing feature installation scripts:
1. Make changes in `features/{feature-name}/install.sh`
2. Update `features/{feature-name}/devcontainer-feature.json` if needed
3. Rebuild container with `-r` flag to apply changes
4. vimcontainer copies features into temp workspace on rebuild

### Neovim Configuration

- Plugin configurations go in `submodules/LazyVim/lua/plugins/`
- The LazyVim submodule is shared across all containers
- Tree-sitter parsers install to container-specific `.local/share/nvim/` (not shared)
- For WSL2 clipboard integration, see README.md OSC 52 setup section

## Key Implementation Details

### Container Hash System
```bash
# From vimcontainer:65
WORKSPACE_HASH=$(echo -n "$WORKSPACE_PATH" | md5sum | cut -d' ' -f1 | cut -c1-8)
TEMP_WORKSPACE="/tmp/vimcontainer-${WORKSPACE_HASH}"
```
This ensures workspace → container mapping is deterministic.

### Feature Injection
```bash
# From vimcontainer:104-105
jq '.features += {"./tree-sitter": {}, "./easydotnet": {}, "./luarocks": {}}' "$ORIGINAL_JSON"
```
Features are merged into devcontainer.json at runtime, not stored in source control.

### postCreateCommand Auto-Addition
```bash
# From vimcontainer:108-113
POST_CREATE_CMD="bash -c 'for dir in /workspaces/*/; do if [ -f \"\$dir\"*.sln ] || [ -f \"\$dir\"*.csproj ]; then cd \"\$dir\" && dotnet restore && break; fi; done'"
```
Auto-detects .NET projects and runs restore.

## Important Notes

- **DO NOT** manually edit files in `/tmp/vimcontainer-*` - they are auto-generated
- **DO NOT** commit changes to the LazyVim submodule without understanding it's a shared config
- Container cleanup only happens on interrupt (Ctrl+C) or with `-r` flag, not on normal exit
- The same workspace path will always connect to the same container (unless rebuilt)
- Feature changes require container rebuild (`-r`) to take effect
