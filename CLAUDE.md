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
- `-R, --restore`: Restore original devcontainer.json from backup (Mode A only)
- `-n, --no-user-devcontainer`: Ignore user's .devcontainer, use template

## Architecture

### vimcontainer Script (`bin/vimcontainer`)

The core script creates and manages DevContainer environments with these key behaviors:

1. **Container Reuse**: Containers are identified by workspace path hash (`md5sum | cut -c1-8`), ensuring the same workspace always reuses the same container
2. **Temporary Workspace**: Creates `/tmp/vimcontainer-{HASH}` for each unique workspace path
3. **Automatic Feature Injection**: Copies local features (`tree-sitter`, `easydotnet`, `luarocks`) from `features/` into temp `.devcontainer` and merges them into `devcontainer.json` using `jq`
4. **Auto-adds postCreateCommand**: If not present in original devcontainer.json, adds `dotnet restore` command for .NET projects
5. **Shared LazyVim Config**: Mounts `submodules/LazyVim` to `/home/vscode/.config/nvim` (shared across all containers)
6. **Additional Features**: Auto-injects public features (neovim, ripgrep, deno, node, tmux) via `--additional-features` flag
7. **User .devcontainer Detection**: Automatically detects and edits user's existing .devcontainer configuration

### Mode A: User .devcontainer Edit Mode

When the workspace contains an existing `.devcontainer/devcontainer.json`:

1. **Backup Creation**: Creates `.vimcontainer-backup` of original devcontainer.json
2. **Feature Injection**: Injects vimcontainer features (local + public) into existing config
3. **Existing Config Preservation**: Preserves user's existing features and postCreateCommand
4. **Direct Workspace Usage**: Uses workspace path directly without temp directory

Key functions:

- `detect_user_devcontainer()`: Checks for valid .devcontainer in workspace
- `backup_devcontainer_json()`: Creates backup before editing
- `restore_devcontainer_json()`: Restores from backup and cleans up injected features
- `copy_local_features_to_user_devcontainer()`: Copies feature directories
- `inject_vimcontainer_features()`: Merges features into devcontainer.json

### Mode B: Template-Based Mode

When no .devcontainer exists in workspace (original behavior):

1. Creates temporary workspace at `/tmp/vimcontainer-{HASH}`
2. Copies template from `devcontainers/{image}/.devcontainer`
3. Injects features via `--additional-features` flag

### Mount Structure

| Host                                  | Container                                 | Purpose                         |
| ------------------------------------- | ----------------------------------------- | ------------------------------- |
| `{WORKSPACE_PATH}`                    | `/workspaces/{basename}`                  | Project files                   |
| `submodules/LazyVim`                  | `/home/vscode/.config/nvim`               | Shared Neovim config            |
| `dotfiles/.tmux.conf`                 | `/home/vscode/.tmux.conf`                 | tmux config                     |
| `dotfiles/.config/lazygit/config.yml` | `/home/vscode/.config/lazygit/config.yml` | lazygit config                  |
| `agents/`                             | `/home/vscode/.copilot/agents`            | Copilot agents                  |
| `skills/`                             | `/home/vscode/.copilot/skills`            | Copilot skills                  |
| `bin/cplt`                            | `/usr/local/bin/cplt`                     | Copilot CLI wrapper             |
| `agents-docs/{name}-{hash}`           | `/docs`                                   | Document output directory       |
| `~/.copilot/mcp-config.json`          | `/home/vscode/.copilot/mcp-config.json`   | MCP config (if exists)          |
| `~/.copilot/config.json`              | `/home/vscode/.copilot/config.json`       | Copilot config (if exists)      |
| `~/.claude`                           | `/home/vscode/.claude`                    | Claude Code auth (if exists)    |
| `~/.claude.json`                      | `/home/vscode/.claude.json`               | Claude Code config (if exists)  |
| `vimcontainer-setup-{hash}` (volume)  | `/home/vscode/.local/share/nvim`          | Neovim data (persistent volume) |

**Note**: nvim data is now persisted via named volumes per workspace, enabling state retention across container rebuilds.

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

**claude-code** (`features/claude-code/`)

- Installs Claude Code CLI for AI-powered development
- Requires Node.js (installsAfter node feature)
- Version: configurable (default: latest)

**copilot-cli** (`features/copilot-cli/`)

- Installs GitHub Copilot CLI for AI-powered terminal assistance
- Version: configurable (default: latest)

**lazygit** (`features/lazygit/`)

- Installs lazygit - a simple terminal UI for git commands
- Default version: 0.51.1 (configurable)

**yazi** (`features/yazi/`)

- Installs Yazi, a blazing fast terminal file manager written in Rust
- Default version: 0.4.2 (configurable)

**vimcontainer-setup** (`features/vimcontainer-setup/`)

- Creates and configures `/home/vscode/.local/share/nvim` directory for Neovim data persistence
- Sets proper ownership for vscode user

### LazyVim Submodule

- **Location**: `submodules/LazyVim`
- **Source**: `git@github.com:NagasakaH/LazyVim.git`
- **Auto-initialization**: vimcontainer auto-runs `git submodule update --init` if not initialized
- **Plugin Customization**: Add user-specific plugins to `submodules/LazyVim/lua/plugins/` (not `~/.config/nvim/`)

### Copilot CLI Integration

**Commands** (`bin/`)

- `cplt` - Copilot CLI wrapper that:
  - Renames tmux window to "copilot" during execution
  - Supports `-r` flag for `--resume`
  - Automatically uses `call-opus-agent` agent
  - Usage: `cplt [-r] [args]`

**Agents** (`agents/`)

Custom agents for orchestrating AI-powered workflows:

- `call-opus-agent.agent.md` - Entry point agent that:
  - Collects environment information (DOCS_ROOT, working directory)
  - Delegates to opus-parent-agent with context

- `opus-parent-agent.md` - Task orchestration agent that:
  - Splits tasks and creates work plans
  - Manages parallel/serial execution of sub-agents
  - Records task execution history
  - Uses Claude Opus 4.5 model

- `opus-child-agent.md` - Task execution agent that:
  - Executes delegated tasks
  - Outputs work reports to designated directories
  - Uses Claude Opus 4.5 model

**Skills** (`skills/`)

Modular packages that extend AI capabilities:

- `get-docs-root/` - Retrieves DOCS_ROOT environment variable
  - Script: `scripts/get_docs_root.py`
  - Returns the documentation root directory path

- `mcp-builder/` - Guide for creating MCP (Model Context Protocol) servers
  - Covers TypeScript and Python implementations
  - Includes best practices and evaluation guides
  - References in `reference/` directory

- `skill-creator/` - Guide for creating effective skills
  - Documents skill anatomy (SKILL.md, scripts, references, assets)
  - Includes init and package scripts
  - Progressive disclosure design patterns

### Environment Variables (set in container)

- `DOCS_ROOT=/docs` - Documentation output directory
- `PROJECT_NAME={workspace_name}` - Current workspace name

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
- Neovim data is persisted in named Docker volumes (one per workspace hash)
- DOCS_ROOT environment variable is automatically set to `/docs` in containers
- Agents and skills are mounted from host and available in `/home/vscode/.copilot/`
