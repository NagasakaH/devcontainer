# code-review スキル作成報告

## 実施内容

`/workspaces/devcontainer/submodules/everything-claude-code/commands/code-review.md` を参考に、code-review スキルを作成しました。

## 作成したファイル

```
/workspaces/devcontainer/skills/code-review/
├── SKILL.md        # スキル定義（日本語化済み）
├── README.md       # 使い方ガイド（日本語化済み）
└── scripts/
    └── review.sh   # 簡易レビュースクリプト
```

## 各ファイルの内容

### SKILL.md
- Claude が読み込むスキル定義ファイル
- フロントマターに `name` と `description` を設定
- チェック項目を3つのカテゴリに分類:
  - セキュリティ問題（CRITICAL）
  - コード品質（HIGH）
  - ベストプラクティス（MEDIUM）
- レポート形式の説明
- コミットブロック条件の明記

### README.md
- 人間向けの使い方ガイド
- スキルの概要説明
- チェック項目の詳細
- ファイル構成の説明

### scripts/review.sh
- 基本的なコードレビューを自動実行するシェルスクリプト
- 以下のチェックを実行:
  - ハードコードされた認証情報の検出
  - `console.log` の検出（JavaScript/TypeScript）
  - TODO/FIXME コメントの検出
- 重大度別のカウントとサマリー出力
- CRITICAL問題検出時は終了コード1を返す

## 変更点（元ファイルからの差異）

1. **日本語化**: すべての説明文を日本語に翻訳
2. **Docusaurus互換**: 変数表記はインラインコードで囲む形式に統一
3. **スクリプト追加**: 簡易レビュー用のシェルスクリプトを追加
4. **構造化**: get-docs-root スキルと同じフォルダ構成に整理

## 動作確認

`review.sh` スクリプトの動作確認を実施し、正常に機能することを確認しました。

## 備考

DOCS_ROOTが未設定のため、ドキュメント出力先へのファイル出力はスキップしました。
