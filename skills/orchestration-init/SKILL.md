---
name: orchestration-init
description: エージェントオーケストレーション用のRedisリスト/ストリームを初期化するスキル。親エージェントと子エージェント間の通信基盤をセットアップし、複数のオーケストレーションが重複しないようユニークな名前空間を生成する。「オーケストレーション初期化」「リスト初期化」「エージェント通信セットアップ」「Redis初期化」「並列エージェント準備」などのフレーズで発動。
---

# Orchestration Init

エージェントオーケストレーション用のRedisリスト/ストリームを初期化する。

## 通信方式

Blocked List（BLPOP/RPUSH）方式を採用：

| 方向 | 送信側操作 | 受信側操作 | 説明 |
|------|-----------|-----------|------|
| 親→子 | `RPUSH {prefix}:p2c:{N}` | `BLPOP {prefix}:p2c:{N}` | タスク割り当て |
| 子→親 | `RPUSH {prefix}:c2p:{N}` | `BLPOP {prefix}:c2p:{N}` | 結果報告 |

- **送信側**: `RPUSH` でリストの末尾にメッセージを追加
- **受信側**: `BLPOP` でリストの先頭からブロッキング取得（メッセージが来るまで待機）

## 前提条件

- Redisが起動済み（compose.ymlで `redis` サービスが定義されていること）
- Python 3.x がインストール済み

## Quick Start

```bash
# デフォルト設定で初期化（最大9子、自動プレフィックス）
python scripts/init_orchestration.py

# JSON形式で出力（他のスクリプトで使用する場合）
python scripts/init_orchestration.py --json
```

## 命名規則

リスト/ストリーム名は以下の規則で生成される：

```
{PROJECT_NAME}-{HOST_NAME}-{連番}:{リソースタイプ}:{番号}
```

例: `devcontainer-4c606c3024b0-001:p2c:1`

| 要素 | 説明 | 例 |
|------|------|-----|
| PROJECT_NAME | 環境変数 `$PROJECT_NAME` | `devcontainer` |
| HOST_NAME | 環境変数 `$HOSTNAME`（12文字まで） | `4c606c3024b0` |
| 連番 | 重複回避用の3桁連番（自動検索） | `001`, `002` |

## 初期化されるリソース

| リソース | 用途 | 名前パターン | 操作 |
|---------|------|-------------|------|
| 親→子リスト | タスク割り当て | `{prefix}:p2c:{1-9}` | RPUSH/BLPOP |
| 子→親リスト | 結果報告 | `{prefix}:c2p:{1-9}` | RPUSH/BLPOP |
| 状態ストリーム | イベント記録 | `{prefix}:status` | XADD/XREAD |
| 結果ストリーム | 結果集約 | `{prefix}:results` | XADD/XREAD |
| 制御リスト | 停止/キャンセル | `{prefix}:control` | RPUSH/BLPOP |
| 設定キー | セッション情報 | `{prefix}:config` | GET/SET |

## 使用方法

### 初期化スクリプト

```bash
python scripts/init_orchestration.py [options]
```

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--host` | `redis` | Redisホスト |
| `--port` | `6379` | Redisポート |
| `--prefix` | 自動生成 | カスタムプレフィックス |
| `--max-children` | `9` | 最大子エージェント数 |
| `--sequence` | 自動検索 | シーケンス番号を指定 |
| `--ttl` | `3600` | 設定のTTL秒数 |
| `--json` | - | JSON形式で出力 |

### 設定取得

```bash
# セッション設定を表示
python scripts/get_config.py devcontainer-4c606c3024b0-001

# JSON形式で取得
python scripts/get_config.py devcontainer-4c606c3024b0-001 --json
```

### クリーンアップ

```bash
# 全セッションをリスト
python scripts/cleanup.py --list-all

# 特定セッションを削除
python scripts/cleanup.py devcontainer-4c606c3024b0-001

# 全セッションを削除（危険）
python scripts/cleanup.py --cleanup-all
```

## 使用例: オーケストレーション開始フロー

1. **初期化**
   ```bash
   python scripts/init_orchestration.py --json > /tmp/orch_config.json
   export ORCH_SESSION=$(jq -r .prefix /tmp/orch_config.json)
   ```

2. **子エージェントにセッション情報を渡す**
   ```
   セッション: devcontainer-4c606c3024b0-001
   
   子エージェント1:
     - タスク受信: BLPOP devcontainer-4c606c3024b0-001:p2c:1 0
     - 結果送信: RPUSH devcontainer-4c606c3024b0-001:c2p:1 "<結果JSON>"
   
   子エージェント2:
     - タスク受信: BLPOP devcontainer-4c606c3024b0-001:p2c:2 0
     - 結果送信: RPUSH devcontainer-4c606c3024b0-001:c2p:2 "<結果JSON>"
   ```

3. **親エージェントのタスク送信**
   ```bash
   # 子エージェント1にタスクを送信
   redis-cli RPUSH devcontainer-4c606c3024b0-001:p2c:1 '{"task": "...", "id": "task-1"}'
   
   # 子エージェント1からの結果を待機
   redis-cli BLPOP devcontainer-4c606c3024b0-001:c2p:1 300
   ```

4. **タスク完了後のクリーンアップ**
   ```bash
   python scripts/cleanup.py $ORCH_SESSION
   ```

## 重複回避の仕組み

- 初期化時に `{prefix}:config` キーの存在を確認
- 既存のシーケンス番号は自動的にスキップ
- 同一マシン上で複数のオーケストレーションを同時実行可能

## スクリプト

- `scripts/init_orchestration.py` - オーケストレーション初期化
- `scripts/get_config.py` - 設定取得
- `scripts/cleanup.py` - セッションクリーンアップ
