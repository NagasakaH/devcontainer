# Python ビルドコマンドリファレンス

## ビルド・パッケージングコマンド

### build（推奨）

```bash
# パッケージのビルド（sdist + wheel）
python -m build

# ソース配布物のみ
python -m build --sdist

# wheelのみ
python -m build --wheel

# 出力先を指定
python -m build --outdir dist/
```

### poetry

```bash
# パッケージのビルド
poetry build

# wheelのみ
poetry build --format wheel

# ソース配布物のみ
poetry build --format sdist
```

### setuptools（従来方式）

```bash
# sdist + wheel
python setup.py sdist bdist_wheel

# 開発モードでインストール
pip install -e .
```

### Flit

```bash
# ビルド
flit build

# ソース配布物のみ
flit build --format sdist
```

### Hatch

```bash
# ビルド
hatch build

# wheelのみ
hatch build -t wheel
```

## 型チェック（TypeScript相当）

### mypy

```bash
# 基本的な型チェック
mypy src/

# 厳格モード
mypy --strict src/

# 設定ファイルを指定
mypy --config-file mypy.ini src/

# エラーの詳細を表示
mypy --show-error-codes src/
```

### pyright

```bash
# 基本的な型チェック
pyright

# 特定のファイル
pyright src/

# 監視モード
pyright --watch
```

## リントチェック

### ruff（推奨）

```bash
# リントチェック
ruff check src/

# 自動修正
ruff check --fix src/

# フォーマット
ruff format src/
```

### flake8

```bash
# リントチェック
flake8 src/
```

### pylint

```bash
# リントチェック
pylint src/
```

## ビルド出力ディレクトリ

| ツール | 出力パス |
|--------|----------|
| build | `dist/` |
| poetry | `dist/` |
| setuptools | `dist/` |
| mypy | なし（チェックのみ） |

## 主要なビルドツール

- **build** - PEP 517準拠のビルドフロントエンド（推奨）
- **poetry** - 依存関係管理とビルドの統合ツール
- **setuptools** - 従来からの標準ビルドツール
- **flit** - シンプルなビルドツール
- **hatch** - 現代的なビルドツール

## 設定ファイル例

### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "my-package"
version = "1.0.0"
requires-python = ">=3.9"

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_ignores = true

[tool.ruff]
line-length = 88
select = ["E", "F", "I", "UP"]
```

### setup.cfg

```ini
[mypy]
python_version = 3.11
strict = True

[flake8]
max-line-length = 88
exclude = .git,__pycache__,dist
```

## 一般的なエラーと解決方法

### ImportError / ModuleNotFoundError

```bash
# 依存関係をインストール
pip install -r requirements.txt

# 開発モードでインストール
pip install -e .
```

### 型エラー（mypy）

```bash
# 型スタブをインストール
pip install types-requests types-PyYAML

# 特定のエラーを無視（一時的）
mypy --ignore-missing-imports src/
```

### SyntaxError

```bash
# Pythonバージョンを確認
python --version

# 構文チェック
python -m py_compile src/main.py
```

## CI/CD連携（GitHub Actions例）

```yaml
- name: Install dependencies
  run: |
    pip install build mypy ruff

- name: Type check
  run: mypy src/

- name: Lint
  run: ruff check src/

- name: Build
  run: python -m build

- name: Check build artifacts
  run: ls -la dist/
```
