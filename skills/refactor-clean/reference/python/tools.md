---
sidebar_position: 1769331678
date: 2026-01-25T09:01:18+00:00
---

# Python - デッドコード検出ツール

## 推奨ツール

| ツール | 検出対象 | インストール |
|--------|----------|--------------|
| vulture | 未使用のコード全般 | `pip install vulture` |
| autoflake | 未使用のインポート | `pip install autoflake` |
| pyflakes | 未使用の変数・インポート | `pip install pyflakes` |
| ruff | 未使用コード（高速） | `pip install ruff` |

## コマンド例

### vulture（推奨）

```bash
# プロジェクト全体をスキャン
vulture .

# 信頼度の閾値を指定（デフォルト60%）
vulture . --min-confidence 80

# ホワイトリストを使用
vulture . whitelist.py

# 特定のディレクトリを除外
vulture . --exclude venv,tests
```

### autoflake

```bash
# 未使用インポートのみ検出（ドライラン）
autoflake --remove-all-unused-imports -r --check .

# 未使用インポートを削除
autoflake --remove-all-unused-imports -r -i .

# 未使用変数も削除
autoflake --remove-all-unused-imports --remove-unused-variables -r -i .
```

### pyflakes

```bash
# プロジェクト全体をチェック
pyflakes .

# 特定のディレクトリのみ
pyflakes src/
```

### ruff（高速な代替）

```bash
# 未使用インポートをチェック（F401）
ruff check . --select F401

# 未使用変数をチェック（F841）
ruff check . --select F841

# 自動修正
ruff check . --select F401,F841 --fix
```

## 設定ファイル例

### pyproject.toml（vulture + ruff）

```toml
[tool.vulture]
exclude = ["venv/", "tests/", "migrations/"]
min_confidence = 80
sort_by_size = true

[tool.ruff]
select = ["F401", "F841"]  # 未使用インポート、未使用変数
ignore = []

[tool.ruff.per-file-ignores]
"__init__.py" = ["F401"]  # __init__.py での再エクスポートは許可
```

### setup.cfg（autoflake）

```ini
[autoflake]
remove-all-unused-imports = true
remove-unused-variables = true
recursive = true
exclude = venv,tests
```

## ホワイトリストの作成（vulture用）

特定のコードを意図的に未使用として許可する場合：

```python
# whitelist.py
from myproject import unused_but_needed  # noqa

# ダイナミックに使用されるメソッド
_.process_data  # 動的呼び出し用
_.handle_event  # イベントハンドラー
```

## CI/CD統合例

### GitHub Actions

```yaml
- name: Check for dead code
  run: |
    pip install vulture ruff
    vulture . --min-confidence 80
    ruff check . --select F401,F841
```

## 注意事項

- **動的インポート**: `importlib` や `__import__` を使用している場合、誤検出の可能性あり
- **フレームワーク固有**: Django/Flaskのビューやシグナルは動的に呼び出されるため注意
- **テストコード**: テストで使用されるフィクスチャやモックは除外を検討
