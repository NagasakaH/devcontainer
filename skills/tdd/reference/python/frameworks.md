---
sidebar_position: 1769331671
date: 2026-01-25T09:01:11+00:00
---

# Python テストフレームワーク

TDD（テスト駆動開発）をPythonで実践するためのフレームワークとツールガイド。

## テストフレームワーク

### pytest（推奨）

Pythonで最も広く使用されているテストフレームワーク。シンプルな構文と豊富なプラグインエコシステムが特徴。

```python
# tests/test_liquidity.py
import pytest
from lib.liquidity import calculate_liquidity_score, MarketData

class TestCalculateLiquidityScore:
    def test_high_liquidity_returns_high_score(self):
        market = MarketData(
            total_volume=100000,
            bid_ask_spread=0.01,
            active_traders=500,
            last_trade_time=datetime.now()
        )
        
        score = calculate_liquidity_score(market)
        
        assert score > 80
        assert score <= 100
    
    def test_zero_volume_returns_zero(self):
        market = MarketData(
            total_volume=0,
            bid_ask_spread=0,
            active_traders=0,
            last_trade_time=datetime.now()
        )
        
        score = calculate_liquidity_score(market)
        
        assert score == 0
    
    @pytest.mark.parametrize("volume,expected_min", [
        (100, 0),
        (1000, 20),
        (10000, 50),
        (100000, 80),
    ])
    def test_volume_affects_score(self, volume, expected_min):
        market = MarketData(
            total_volume=volume,
            bid_ask_spread=0.01,
            active_traders=100,
            last_trade_time=datetime.now()
        )
        
        score = calculate_liquidity_score(market)
        
        assert score >= expected_min
```

### unittest（標準ライブラリ）

Python標準ライブラリに含まれるテストフレームワーク。外部依存なしで使用可能。

```python
# tests/test_liquidity.py
import unittest
from lib.liquidity import calculate_liquidity_score, MarketData

class TestCalculateLiquidityScore(unittest.TestCase):
    def test_high_liquidity_returns_high_score(self):
        market = MarketData(
            total_volume=100000,
            bid_ask_spread=0.01,
            active_traders=500,
            last_trade_time=datetime.now()
        )
        
        score = calculate_liquidity_score(market)
        
        self.assertGreater(score, 80)
        self.assertLessEqual(score, 100)
    
    def test_zero_volume_returns_zero(self):
        market = MarketData(
            total_volume=0,
            bid_ask_spread=0,
            active_traders=0,
            last_trade_time=datetime.now()
        )
        
        score = calculate_liquidity_score(market)
        
        self.assertEqual(score, 0)

if __name__ == '__main__':
    unittest.main()
```

## アサーションライブラリ

### pytest（組み込み assert）

```python
# 基本的なアサーション
assert result == expected
assert result > threshold
assert result in collection
assert result is None
assert isinstance(result, SomeClass)

# 例外のテスト
with pytest.raises(ValueError, match="invalid value"):
    function_that_raises()

# 浮動小数点の近似比較
assert result == pytest.approx(expected, rel=1e-3)
```

### unittest（組み込み）

```python
# 基本的なアサーション
self.assertEqual(result, expected)
self.assertGreater(result, threshold)
self.assertIn(result, collection)
self.assertIsNone(result)
self.assertIsInstance(result, SomeClass)

# 例外のテスト
with self.assertRaises(ValueError):
    function_that_raises()

# 浮動小数点の近似比較
self.assertAlmostEqual(result, expected, places=3)
```

## モックライブラリ

### unittest.mock（標準ライブラリ）

```python
from unittest.mock import Mock, patch, MagicMock

# 基本的なモック
mock_service = Mock()
mock_service.get_data.return_value = {"key": "value"}

# パッチデコレータ
@patch('module.external_service')
def test_with_mock(mock_external):
    mock_external.fetch.return_value = {"data": "test"}
    result = function_under_test()
    mock_external.fetch.assert_called_once()

# コンテキストマネージャ
with patch('module.database') as mock_db:
    mock_db.query.return_value = [{"id": 1}]
    result = service.get_items()
    assert len(result) == 1
```

### pytest-mock

```python
# fixtures経由でのモック（pytest-mock）
def test_with_mocker(mocker):
    mock_service = mocker.patch('module.service')
    mock_service.return_value = "mocked"
    
    result = function_under_test()
    
    mock_service.assert_called_once()
```

## 実行コマンド

```bash
# pytest でテスト実行
pytest

# 特定のテストファイル
pytest tests/test_liquidity.py

# 特定のテスト関数
pytest tests/test_liquidity.py::test_high_liquidity

# 特定のテストクラス
pytest tests/test_liquidity.py::TestCalculateLiquidityScore

# 詳細出力
pytest -v

# 失敗時に即停止
pytest -x

# 最後に失敗したテストのみ再実行
pytest --lf

# カバレッジ付き
pytest --cov=lib --cov-report=html

# マーカーでフィルタ
pytest -m "not slow"
```

```bash
# unittest でテスト実行
python -m unittest discover

# 特定のテストモジュール
python -m unittest tests.test_liquidity

# 詳細出力
python -m unittest -v tests.test_liquidity
```

## カバレッジ

### pytest-cov

```bash
# インストール
pip install pytest-cov

# カバレッジ付きでテスト実行
pytest --cov=src --cov-report=html --cov-report=term-missing

# 最小カバレッジを強制
pytest --cov=src --cov-fail-under=80
```

### coverage.py

```bash
# インストール
pip install coverage

# テスト実行
coverage run -m pytest

# レポート表示
coverage report

# HTMLレポート生成
coverage html
```

**カバレッジレポートパス**: `htmlcov/index.html` または `coverage.json`

## プロジェクト構成例

```
project/
├── pyproject.toml      # プロジェクト設定
├── src/
│   └── lib/
│       ├── __init__.py
│       └── liquidity.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py     # pytest共通fixtures
│   └── test_liquidity.py
└── .coveragerc         # カバレッジ設定
```

### pyproject.toml

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --cov=src --cov-report=term-missing"
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
]

[tool.coverage.run]
source = ["src"]
branch = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "raise NotImplementedError",
]
```

## ベストプラクティス

### 推奨事項

- `pytest` を使用（シンプルで強力）
- テストファイルは `test_` プレフィックスを付ける
- フィクスチャを活用してセットアップコードを共有
- `@pytest.mark.parametrize` でデータ駆動テストを実装
- 型ヒントを使用してコードの可読性を向上
- `dataclass` または `TypedDict` でテストデータを構造化

### 避けるべきこと

- テスト間で状態を共有（各テストは独立すべき）
- 外部サービスへの実際の呼び出し（モックを使用）
- 実装の詳細をテスト（振る舞いをテスト）
- 過度に複雑なフィクスチャ
- ハードコードされたファイルパスやURL

## 関連ツール

| ツール | 用途 |
|--------|------|
| `pytest` | テストフレームワーク |
| `pytest-cov` | カバレッジ計測 |
| `pytest-mock` | モック支援 |
| `pytest-xdist` | 並列実行 |
| `hypothesis` | プロパティベーステスト |
| `factory_boy` | テストデータ生成 |
| `faker` | フェイクデータ生成 |
