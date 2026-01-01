# DevContainer Setup

カスタムDevContainer featuresとvimcontainerスクリプトによる統合開発環境セットアップ

## プロジェクト構成

```
devcontainer/
├── bin/
│   └── vimcontainer              # DevContainer起動スクリプト
├── devcontainers/                # DevContainer設定テンプレート
│   └── dotnet/                   # .NET開発環境
│       └── .devcontainer/
│           ├── Dockerfile
│           └── devcontainer.json
├── features/                     # カスタムDevContainer features
│   ├── easydotnet/              # .NET開発ツール統合
│   └── tree-sitter/             # tree-sitter CLI
├── submodules/
│   └── LazyVim/                 # Neovim設定 (submodule)
└── dotfiles/
    └── .tmux.conf               # tmux設定
```

## クイックスタート

### 1. インストール

```bash
# リポジトリをクローン
git clone <repository-url>
cd devcontainer

# セットアップスクリプトを実行
./install.sh
```

`install.sh`は以下を自動で実行します:
- vimcontainerコマンドをPATHに追加
- LazyVimサブモジュールの初期化（vimcontainer実行時にも自動実行）

### 2. 使い方

```bash
# .NET開発環境を起動
vimcontainer ~/git/devcontainer/devcontainers/dotnet ~/path/to/your/project

# 初回またはリビルド時
vimcontainer -r ~/git/devcontainer/devcontainers/dotnet ~/path/to/your/project
```

**引数**:
- 第1引数: `.devcontainer`フォルダのパス（または親ディレクトリ）
- 第2引数: プロジェクトのワークスペースパス

**オプション**:
- `-r, --rebuild`: コンテナを再ビルド

## カスタムDevContainer Features

### tree-sitter

tree-sitter CLIをプリビルドバイナリからインストールします。

- **バージョン**: 0.24.5 (デフォルト)
- **対応アーキテクチャ**: amd64, arm64
- **インストール先**: `/usr/local/bin/tree-sitter`

### easydotnet

.NET開発環境を統合的にセットアップします。

**インストールされるツール**:
- `easydotnet` - .NET開発用CLIツール
- `dotnet-ef` (v8.0.11) - Entity Framework Core CLI
- `netcoredbg` (v3.1.0-1030) - .NETデバッガー (nvim-dap対応)

**インストール先**:
- `~/.dotnet/tools/dotnet-easydotnet`
- `~/.dotnet/tools/dotnet-ef`
- `/usr/local/bin/netcoredbg`

**自動設定**:
- vscodeユーザーにツールをインストール
- PATHを自動設定 (`/etc/profile.d/dotnet-tools.sh`)

## vimcontainerの仕組み

### コンテナの再利用

vimcontainerは同じワークスペースに対して同じコンテナを再利用します:

```bash
# ワークスペースパスのハッシュ値でコンテナを識別
WORKSPACE_HASH=$(echo -n "$WORKSPACE_PATH" | md5sum | cut -d' ' -f1 | cut -c1-8)
TEMP_WORKSPACE="/tmp/vimcontainer-${WORKSPACE_HASH}"
```

- `-r`オプションなし: 既存コンテナを再利用
- `-r`オプションあり: コンテナを再ビルド

### マウント構成

| ホスト | コンテナ | 説明 |
|--------|----------|------|
| `{WORKSPACE_PATH}` | `/workspaces/{basename}` | プロジェクトファイル |
| `submodules/LazyVim` | `/home/vscode/.config/nvim` | Neovim設定 (共有) |
| `dotfiles/.tmux.conf` | `/home/vscode/.tmux.conf` | tmux設定 |

**注**: nvimのdata/stateディレクトリ（`.local/share/nvim`, `.local/state/nvim`）はコンテナ内に保持され、コンテナごとに独立します。

### 自動追加されるfeatures

vimcontainerは以下のfeaturesを自動的に追加します:

- **プロジェクトカスタムfeatures**:
  - `./tree-sitter`
  - `./easydotnet`

- **公式features**:
  - `ghcr.io/duduribeiro/devcontainer-features/neovim:1`
  - `ghcr.io/jungaretti/features/ripgrep:1`
  - `ghcr.io/devcontainers-community/features/deno`
  - `ghcr.io/devcontainers/features/node:1`
  - `ghcr.io/devcontainers-extra/features/tmux-apt-get:1`

## .NET開発環境

### 設定済み機能

#### LSP (Language Server Protocol)
- **OmniSharp**: C#言語サーバー（自動起動）
- **easy-dotnet.nvim**: .NET開発プラグイン統合

#### DAP (Debug Adapter Protocol)
- **netcoredbg**: .NETデバッガー
- **nvim-dap**: デバッグクライアント
- **nvim-dap-ui**: デバッグUI

#### デバッグの使い方

nvim内で以下のコマンドを使用:

```vim
" ブレークポイント設定
:lua require('dap').toggle_breakpoint()

" デバッグ開始
:lua require('dap').continue()

" ステップ実行
:lua require('dap').step_over()   " F10相当
:lua require('dap').step_into()   " F11相当
:lua require('dap').step_out()    " Shift+F11相当
```

### postCreateCommand

.NET開発環境では、コンテナ作成時に自動的に`dotnet restore`が実行されます。

設定: `devcontainers/dotnet/.devcontainer/devcontainer.json`
```json
{
  "postCreateCommand": "dotnet restore"
}
```

## Neovim設定

### LazyVimサブモジュール

プロジェクトのLazyVimサブモジュールがすべてのコンテナで共有されます:

- **パス**: `submodules/LazyVim`
- **自動初期化**: vimcontainer実行時に未初期化の場合は自動で`git submodule update --init`
- **マウント先**: `/home/vscode/.config/nvim`

### プラグイン設定の場所

ユーザー固有のプラグイン設定は`~/.config/nvim/`ではなく、`submodules/LazyVim/lua/plugins/`に配置してください。

**例**: C#開発プラグイン設定
- 場所: `~/.config/nvim/lua/plugins/easy-dotnet.lua`
- 内容: easy-dotnet.nvim、nvim-dap、nvim-dap-uiの設定

## Neovim クリップボード共有 (WSL2)

WSL2 + DevContainer環境でNeovimのクリップボードをホストOSと共有する設定です。

### セットアップ手順

#### 1. Windows Terminal設定

Windows Terminalの設定でOSC 52を有効にします。

1. Windows Terminalを起動
2. `Ctrl + ,` で設定を開く
3. 左下の「JSONファイルを開く」をクリック
4. 以下を追加:

```json
{
  "profiles": {
    "defaults": {
      "compatibility.allowOsc52": true
    }
  }
}
```

5. 設定を保存して再起動

#### 2. Neovim設定

`~/.config/nvim/lua/config/options.lua` に以下を追加:

```lua
-- OSC 52 clipboard support for DevContainer/WSL2
local function paste()
  return {
    vim.fn.split(vim.fn.getreg(""), "\n"),
    vim.fn.getregtype(""),
  }
end

vim.g.clipboard = {
  name = "OSC 52",
  copy = {
    ["+"] = require("vim.ui.clipboard.osc52").copy("+"),
    ["*"] = require("vim.ui.clipboard.osc52").copy("*"),
  },
  paste = {
    ["+"] = paste,
    ["*"] = paste,
  },
}

vim.opt.termguicolors = true
vim.opt.clipboard = "unnamedplus"
```

#### 3. 使い方

Neovimを再起動後、通常のヤンク/ペースト操作でホストOSのクリップボードと連携します:

- **コピー**: ビジュアルモードで選択して `y`
- **ペースト**: ノーマルモードで `p`

### トラブルシューティング

#### "waiting for OSC 52 response from the terminal" でタイムアウトする

**原因**: Windows TerminalでOSC 52が有効になっていない、または設定が反映されていない

**解決策**:
1. Windows Terminalの設定を再確認
2. Windows Terminalを完全に再起動
3. 以下のコマンドでOSC 52が動作するかテスト:

```bash
printf "\033]52;c;$(printf "test" | base64)\a"
```

上記を実行後、`Ctrl+V` でクリップボードに "test" が貼り付けられれば成功です。

#### 代替案: win32yank使用

OSC 52が動作しない場合、win32yankを使用する方法もあります:

```bash
# win32yankインストール
curl -sLo /tmp/win32yank.zip https://github.com/equalsraf/win32yank/releases/download/v0.1.1/win32yank-x64.zip
unzip -p /tmp/win32yank.zip win32yank.exe > /tmp/win32yank.exe
chmod +x /tmp/win32yank.exe
sudo mv /tmp/win32yank.exe /usr/local/bin/win32yank.exe
```

Neovim設定を以下に変更:

```lua
vim.g.clipboard = {
  name = 'win32yank',
  copy = {
    ['+'] = 'win32yank.exe -i --crlf',
    ['*'] = 'win32yank.exe -i --crlf',
  },
  paste = {
    ['+'] = 'win32yank.exe -o --lf',
    ['*'] = 'win32yank.exe -o --lf',
  },
  cache_enabled = 0,
}
```

## よくある質問

### Q: コンテナが毎回新しく作成されてしまう
A: vimcontainerは同じワークスペースパスに対して同じコンテナを再利用します。`-r`オプションを付けずに実行してください。

### Q: nvim-treesitterのパーサーがインストールできない
A: パーサーはコンテナ内の`/home/vscode/.local/share/nvim/`にインストールされます。ホストとは共有されないため、コンテナごとにインストールが必要です。

### Q: C# LSPが動作しない
A: `dotnet restore`が実行されているか確認してください。初回起動時は`postCreateCommand`で自動実行されますが、手動で実行する場合は:
```bash
dotnet restore
```

### Q: デバッガーが起動しない
A: netcoredbgがインストールされているか確認:
```bash
which netcoredbg
# /usr/local/bin/netcoredbg
```

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。
