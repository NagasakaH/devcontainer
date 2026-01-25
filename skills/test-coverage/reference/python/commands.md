# Python テストカバレッジコマンドリファレンス

## テスト実行コマンド

### pytest + coverage.py（推奨）

```bash
# 基本的なカバレッジ付きテスト実行
pytest --cov --cov-report=term-missing

# HTMLレポート生成
pytest --cov --cov-report=html

# JSON形式でレポート生成
pytest --cov --cov-report=json

# XML形式（CI連携向け）
pytest --cov --cov-report=xml

# 特定のパッケージのカバレッジを取得
pytest --cov=src --cov-report=term-missing
```

### unittest + coverage.py

```bash
# coverage.pyを使ってunittestを実行
coverage run -m unittest discover
coverage report
coverage html
```

### poetry環境

```bash
# poetryプロジェクトでのテスト実行
poetry run pytest --cov --cov-report=term-missing

# coverage.pyを直接使用
poetry run coverage run -m pytest
poetry run coverage report
```

## カバレッジレポートファイルのパス

| 形式 | 出力パス | 用途 |
|------|----------|------|
| ターミナル | - | 即時確認 |
| HTML | `htmlcov/index.html` | 詳細な可視化 |
| JSON | `coverage.json` | プログラム解析 |
| XML | `coverage.xml` | CI/CD連携 |

## 主要なツール・フレームワーク

### テストフレームワーク

- **pytest** - 最も広く使われているテストフレームワーク
- **unittest** - 標準ライブラリのテストフレームワーク
- **nose2** - unittestの拡張

### カバレッジツール

- **coverage.py** - デファクトスタンダードのカバレッジツール
- **pytest-cov** - pytestとcoverage.pyの連携プラグイン

## 設定ファイル例

### pyproject.toml

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=src --cov-report=term-missing"

[tool.coverage.run]
source = ["src"]
omit = ["*/__init__.py", "*/tests/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
fail_under = 80
```

### setup.cfg

```ini
[tool:pytest]
testpaths = tests
addopts = --cov=src --cov-report=term-missing

[coverage:run]
source = src
omit = */__init__.py, */tests/*

[coverage:report]
fail_under = 80
```

## カバレッジ閾値の設定

```bash
# 80%未満で失敗させる
pytest --cov --cov-fail-under=80
```

## CI/CD連携（GitHub Actions例）

```yaml
- name: Run tests with coverage
  run: |
    pytest --cov --cov-report=xml
    
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```
