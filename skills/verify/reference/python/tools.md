---
sidebar_position: 1769331678
date: 2026-01-25T09:01:18+00:00
---

# Python - 検証ツール

## 検証コマンド一覧

### ビルドチェック

```bash
# パッケージのビルド
python -m build

# Poetry使用時
poetry build

# 構文チェックのみ
python -m py_compile src/**/*.py
```

### 型チェック

```bash
# mypy（推奨）
mypy .

# 厳格モード
mypy --strict .

# pyright（高速）
pyright .

# pyright JSON出力
pyright --outputjson
```

### リントチェック

```bash
# ruff（推奨・高速）
ruff check .

# ruff 自動修正
ruff check . --fix

# pylint
pylint src/

# flake8
flake8 .
```

### テスト実行

```bash
# pytest（推奨）
pytest

# カバレッジ付き
pytest --cov --cov-report=term-missing

# 詳細出力
pytest -v

# 特定のテストのみ
pytest tests/test_specific.py
```

### デバッグ出力検索

```bash
# print文の検索
grep -rn "print(" --include="*.py" src/

# logging.debug の検索
grep -rn "logging.debug" --include="*.py" src/

# pdb/breakpoint の検索
grep -rn "pdb\|breakpoint()" --include="*.py" src/
```

## 設定ファイル例

### pyproject.toml（統合設定）

```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true

[tool.ruff]
line-length = 88
select = ["E", "F", "W", "I", "N", "UP", "B", "C4"]
ignore = []
exclude = ["venv", ".git", "__pycache__"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --cov=src --cov-report=term-missing"

[tool.coverage.run]
source = ["src"]
omit = ["tests/*", "*/__init__.py"]
```

### .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: []
```

## CI/CD統合例

### GitHub Actions

```yaml
name: Verify Python

on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      
      - name: Type check
        run: mypy .
      
      - name: Lint
        run: ruff check .
      
      - name: Test
        run: pytest --cov --cov-report=xml
      
      - name: Check for debug prints
        run: |
          if grep -rn "print(" --include="*.py" src/; then
            echo "Found print statements in source code"
            exit 1
          fi
```

## 検証結果の解釈

| チェック | 成功条件 |
|----------|----------|
| ビルド | エラーなしで完了 |
| 型チェック | mypy/pyright がエラー0件 |
| リント | ruff/pylint がエラー0件 |
| テスト | 全テストがパス |
| デバッグ出力 | print文がsrc/内にない |
