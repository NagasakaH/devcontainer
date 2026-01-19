# DevContainer Setup

カスタムDevContainer featuresとvimcontainerスクリプトによる統合開発環境セットアップ。
GitHub Copilot CLI向けのカスタムエージェント・スキル環境も提供します。

## プロジェクト構成

```
devcontainer/
├── agents/                       # Copilot CLI カスタムエージェント
│   ├── call-opus-agent.agent.md # Opusサブエージェント呼び出し
│   ├── opus-parent-agent.md     # 親エージェント定義
│   └── opus-child-agent.md      # 子エージェント定義
├── agents-docs/                  # エージェント出力ドキュメント保存先
├── bin/
│   ├── vimcontainer             # DevContainer起動スクリプト
│   └── cplt                     # Copilot CLI wrapper
├── devcontainers/                # DevContainer設定テンプレート
│   ├── common/                   # 共通Features設定
│   ├── dotnet/                   # .NET開発環境
│   └── react/                    # React開発環境（準備中）
├── docusaurus/                   # agents-docsプレビュー用Docusaurus設定
├── dotfiles/
│   ├── .tmux.conf               # tmux設定
│   └── .config/lazygit/         # lazygit設定
├── features/                     # カスタムDevContainer features
│   ├── claude-code/             # Claude Code CLI
│   ├── copilot-cli/             # GitHub Copilot CLI
│   ├── easydotnet/              # .NET開発ツール統合
│   ├── lazygit/                 # lazygit CLIツール
│   ├── luarocks/                # Luaパッケージマネージャー
│   ├── tree-sitter/             # tree-sitter CLI
│   ├── vimcontainer-setup/      # Neovimデータディレクトリ設定
│   └── yazi/                    # ターミナルファイルマネージャ
├── scripts/                      # ユーティリティスクリプト
│   └── start-tmux.sh            # tmuxセッション初期化
├── skills/                       # Copilot CLI カスタムスキル
│   ├── get-docs-root/           # DOCS_ROOT環境変数取得
│   ├── mcp-builder/             # MCPサーバー構築ガイド
│   └── skill-creator/           # スキル作成ガイド
└── submodules/
    └── LazyVim/                 # Neovim設定 (submodule)
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
vimcontainer dotnet ~/path/to/your/project

# 初回またはリビルド時
vimcontainer -r dotnet ~/path/to/your/project

# 利用可能なイメージを確認
vimcontainer
```

**引数**:
- 第1引数: イメージ名（例: `dotnet`, `react`）
- 第2引数: プロジェクトのワークスペースパス（省略時: カレントディレクトリ）

**オプション**:
- `-r, --rebuild`: コンテナを再ビルド
- `-R, --restore`: バックアップからdevcontainer.jsonを復元
- `-n, --no-user-devcontainer`: ユーザーの.devcontainerを無視してテンプレートを使用

**利用可能なイメージ**:
- `dotnet`: .NET開発環境
- `react`: React開発環境（準備中）

## ユーザー.devcontainer自動編集機能

vimcontainerは、ワークスペースに既存の`.devcontainer`ディレクトリが存在する場合、自動的にその設定を利用してvimcontainerのfeaturesを追加します。

### 動作モード

| モード | 条件 | 動作 |
|--------|------|------|
| **Mode A** | ワークスペースに`.devcontainer`あり | ユーザーのdevcontainer.jsonにfeaturesを注入 |
| **Mode B** | ワークスペースに`.devcontainer`なし | テンプレートベースで新規作成 |

### Mode A: ユーザー設定編集モード

ワークスペースに`.devcontainer/devcontainer.json`が存在する場合：

1. **バックアップ作成**: 元のdevcontainer.jsonを`.vimcontainer-backup`として保存
2. **localFeaturesコピー**: tree-sitter、luarocks等を`.devcontainer/`にコピー
3. **Features注入**: vimcontainerのfeaturesをdevcontainer.jsonに追加
4. **既存設定保持**: ユーザーの既存featuresやpostCreateCommandは保持

```bash
# 例: ユーザーの.devcontainerがあるプロジェクト
vimcontainer dotnet ~/my-project

# 出力:
# Detected user .devcontainer at: /home/user/my-project/.devcontainer
# Using user's .devcontainer configuration (Mode A)
# Created backup: .../devcontainer.json.vimcontainer-backup
```

### バックアップからの復元

vimcontainerによる変更を元に戻すには`-R`オプションを使用：

```bash
# devcontainer.jsonを元の状態に復元
vimcontainer -R dotnet ~/my-project

# 出力:
# Restoring devcontainer.json from backup...
# Restored from backup: .../devcontainer.json
# Removed injected feature: tree-sitter
# Restore completed.
```

復元時に削除されるもの：
- 注入されたfeaturesの設定（devcontainer.jsonから）
- コピーされたlocalFeaturesディレクトリ（tree-sitter, luarocks等）

### テンプレートベースモードの強制

ユーザーの`.devcontainer`を無視してテンプレートを使用するには`-n`オプション：

```bash
# ユーザーの.devcontainerを無視してテンプレートを使用
vimcontainer -n dotnet ~/my-project

# 出力:
# Using template-based configuration (Mode B)
```

### 編集例

**編集前（ユーザーの既存設定）:**
```json
{
  "name": "My Project",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  "features": {
    "ghcr.io/devcontainers/features/git:1": {}
  },
  "postCreateCommand": "pip install -r requirements.txt"
}
```

**編集後（vimcontainer features注入後）:**
```json
{
  "name": "My Project",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  "features": {
    "ghcr.io/devcontainers/features/git:1": {},
    "./tree-sitter": {},
    "./luarocks": {},
    "./claude-code": {},
    "ghcr.io/duduribeiro/devcontainer-features/neovim:1": {"version": "stable"},
    "ghcr.io/jungaretti/features/ripgrep:1": {},
    "ghcr.io/devcontainers-extra/features/tmux-apt-get:1": {}
  },
  "postCreateCommand": "pip install -r requirements.txt && sudo chsh -s /bin/zsh vscode"
}
```

## カスタムDevContainer Features

### claude-code

Claude Code CLIをインストールし、AI支援開発を可能にします。

- **バージョン**: latest (デフォルト)
- **依存関係**: Node.js (ghcr.io/devcontainers/features/node)
- **用途**: AI支援によるコード生成、レビュー、リファクタリング

### copilot-cli

GitHub Copilot CLIをインストールします。

- **バージョン**: latest (デフォルト)
- **用途**: ターミナルでのAI支援、コマンド生成、コード補完

### tree-sitter

tree-sitter CLIをプリビルドバイナリからインストールします。

- **バージョン**: 0.25.10 (デフォルト)
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

### lazygit

lazygit（シンプルなGit用ターミナルUI）をインストールします。

- **バージョン**: 0.51.1 (デフォルト)
- **用途**: ターミナルでの直感的なGit操作
- **インストール先**: `/usr/local/bin/lazygit`

### yazi

Yazi（Rust製高速ターミナルファイルマネージャ）をインストールします。

- **バージョン**: 0.4.2 (デフォルト)
- **用途**: ターミナルでのファイル操作・プレビュー
- **インストール先**: `/usr/local/bin/yazi`

### luarocks

Luaパッケージマネージャーをインストールします。

- **用途**: Neovimプラグインで必要なLuaライブラリの管理
- **インストール先**: システムパッケージ経由

### vimcontainer-setup

Neovimデータディレクトリを設定します。

- **用途**: `/home/vscode/.local/share/nvim`ディレクトリの作成と権限設定
- **自動実行**: コンテナ起動時に所有権を自動設定

## Features設定システム

vimcontainerは`features.json`ファイルを使用してDevContainer featuresを管理します。

### 設定ファイルの階層

1. **Common Features** (`devcontainers/common/features.json`)
   - すべてのイメージで共通して使用するfeatures
   - ベースとなる開発環境ツール（neovim, ripgrep, tmux等）

2. **Image-specific Features** (`devcontainers/{image}/features.json`)
   - イメージ固有のfeatures
   - Common Featuresを上書き可能

### features.jsonの構造

```json
{
  "localFeatures": [
    {
      "name": "tree-sitter",
      "options": {}
    }
  ],
  "publicFeatures": {
    "ghcr.io/duduribeiro/devcontainer-features/neovim:1": {},
    "ghcr.io/jungaretti/features/ripgrep:1": {}
  },
  "postCreateCommand": "dotnet restore"
}
```

- **localFeatures**: `features/`ディレクトリ内のカスタムfeatures
- **publicFeatures**: GitHub Container Registryなどの公開features
- **postCreateCommand**: コンテナ作成後に実行するコマンド

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
| `dotfiles/.config/lazygit/` | `/home/vscode/.config/lazygit/` | lazygit設定 |
| `agents/` | `/home/vscode/.copilot/agents/` | Copilotカスタムエージェント |
| `skills/` | `/home/vscode/.copilot/skills/` | Copilotカスタムスキル |
| `bin/cplt` | `/usr/local/bin/cplt` | Copilot CLIラッパー |
| `agents-docs/{workspace}/` | `/docs` | エージェント出力ドキュメント |
| `~/.claude` | `/home/vscode/.claude` | Claude Code認証情報 |
| `~/.claude.json` | `/home/vscode/.claude.json` | Claude Code設定 |
| `~/.copilot/mcp-config.json` | `/home/vscode/.copilot/mcp-config.json` | Copilot MCP設定 |
| `~/.copilot/config.json` | `/home/vscode/.copilot/config.json` | Copilot設定 |

**注**: 
- nvimのdata/stateディレクトリ（`.local/share/nvim`）はDockerボリュームで永続化され、ワークスペースごとに独立
- DOCS_ROOT環境変数が自動的に`/docs`に設定される

### Features設定の読み込みプロセス

vimcontainerは起動時に以下の手順でfeaturesを読み込み、マージします:

1. **Common Featuresの読み込み** (`devcontainers/common/features.json`)
   - すべてのイメージで共通のlocalFeaturesとpublicFeaturesを読み込み

2. **Image-specific Featuresの読み込み** (`devcontainers/{image}/features.json`)
   - イメージ固有のfeaturesを読み込み

3. **マージ処理**
   - localFeatures: 配列を連結（common + image-specific）
   - publicFeatures: オブジェクトをマージ（image-specificがcommonを上書き）
   - postCreateCommand: image-specificのものを使用

4. **devcontainer.jsonへの統合**
   - マージされたfeaturesを一時ワークスペースの`devcontainer.json`に注入
   - postCreateCommandが未設定の場合は追加

この仕組みにより、共通設定を保ちながらイメージごとのカスタマイズが可能になります。

## Copilot CLI統合

vimcontainerはGitHub Copilot CLIのカスタムエージェント・スキル環境を自動的に設定します。

### cpltコマンド

`cplt`はCopilot CLIのラッパースクリプトです。

```bash
# Copilot CLIをcall-opus-agentで起動
cplt

# セッションを再開
cplt -r
```

**特徴**:
- tmux window名を自動で「copilot」に変更
- `call-opus-agent`エージェントをデフォルトで使用
- `-r`オプションで前回のセッションを再開
- `--allow-all`オプションが自動適用

### カスタムエージェント

`agents/`ディレクトリには、タスク管理のためのエージェント定義が含まれます。

| エージェント | 説明 |
|-------------|------|
| `call-opus-agent` | 環境情報収集とOpus親エージェント呼び出し |
| `opus-parent-agent` | タスク分割と並列実行管理 |
| `opus-child-agent` | 実際の作業実行とドキュメント出力 |

### カスタムスキル

`skills/`ディレクトリには、再利用可能なスキルが含まれます。

| スキル | 説明 |
|--------|------|
| `get-docs-root` | DOCS_ROOT環境変数の値を取得 |
| `mcp-builder` | MCPサーバー構築ガイド（TypeScript/Python対応） |
| `skill-creator` | 新しいスキル作成のガイドライン |

### 環境変数

vimcontainerが自動設定する環境変数:

| 変数名 | 値 | 説明 |
|--------|-----|------|
| `DOCS_ROOT` | `/docs` | エージェント出力ドキュメントのルート |
| `PROJECT_NAME` | ワークスペース名 | プロジェクト識別子 |

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

設定: `devcontainers/dotnet/features.json`
```json
{
  "postCreateCommand": "dotnet restore"
}
```

この設定はvimcontainerによって自動的に`.devcontainer/devcontainer.json`にマージされます。

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

## agents-docs ドキュメント管理

### 概要
vimcontainerでエージェントが出力するドキュメントを管理する仕組みです。

### 仕組み
- `agents-docs/` ディレクトリ配下に各環境固有のディレクトリが作成されます
- ディレクトリ名は `{workspace-name}-{hash}` 形式（例: `myproject-a1b2c3d4`）
- コンテナ内の `/docs` にマウントされ、エージェントはそこにドキュメントを出力します
- `DOCS_ROOT`環境変数が自動で`/docs`に設定されます

### ディレクトリ構造

```
agents-docs/
├── .gitkeep
└── {workspace-name}-{hash}/  # 各環境固有（例: myproject-a1b2c3d4/）
    └── {task-folder}/        # タスクごとのディレクトリ
        ├── タスク実行履歴.md  # タスク実行履歴
        ├── 001/               # 直列タスク1
        │   └── child-*.md
        ├── 002-1/             # 並列タスク（親番号002、サブ番号1）
        │   └── child-*.md
        └── 002-2/             # 並列タスク（親番号002、サブ番号2）
            └── child-*.md
```

### ドキュメントの出力ルール
- マークダウン形式で出力
- 図には可能な限りmermaidを使用
- Docusaurus互換のMDXルールに従う（山括弧はインラインコードで囲む）
- parent-agentがタスクフォルダと連番ディレクトリを事前に作成
- child-agentが`child-<タスク名>.md`を出力

### プレビュー方法
Docusaurusを使用してagents-docsのドキュメントをブラウザでプレビューできます：

```bash
cd docusaurus
npm install
npm run start
```

ブラウザで http://localhost:3000 にアクセスしてください。

### 設定ファイル

| ファイル | 説明 |
|---------|------|
| `agents/opus-parent-agent.md` | 親エージェントのタスク管理・ドキュメント出力ルール |
| `agents/opus-child-agent.md` | 子エージェントの作業実行・ドキュメント出力ルール |
| `agents/call-opus-agent.agent.md` | 環境情報収集・Opusエージェント呼び出し |
| `bin/vimcontainer` | agents-docsのマウント設定 |
| `skills/get-docs-root/` | DOCS_ROOT環境変数取得スキル |

## よくある質問

### Q: コンテナが毎回新しく作成されてしまう
A: vimcontainerは同じワークスペースパスに対して同じコンテナを再利用します。`-r`オプションを付けずに実行してください。

### Q: nvim-treesitterのパーサーがインストールできない
A: パーサーはDockerボリューム内（`vimcontainer-setup-{hash}`）に保存されます。ワークスペースごとに独立しており、初回は自動インストールされます。

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

### Q: Copilot CLIが動作しない
A: 以下を確認してください:
1. `copilot-cli` featureがインストールされているか
2. GitHub認証が完了しているか（`copilot auth login`を実行）
3. `cplt`コマンドを使用しているか

### Q: DOCS_ROOTが取得できない
A: `get-docs-root`スキルを使用してください:
```bash
python3 ~/.copilot/skills/get-docs-root/scripts/get_docs_root.py
```
空行が返る場合は環境変数が設定されていません。

### Q: lazygitの設定が反映されない
A: `dotfiles/.config/lazygit/config.yml`がマウントされています。設定を変更した場合はコンテナを再起動してください。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。
