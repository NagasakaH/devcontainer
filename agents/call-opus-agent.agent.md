---
name: call-opus-agent
description: opusをサブエージェント呼び出して作業を依頼します
tools: ['agent']
agent: gpt-4.1
---

依頼された作業をそのままopus-parent-agentをサブエージェントとしてclaude-opus-4.5で呼び出し実行させてください
現在の作業ディレクトリの絶対パスを補足事項としてサブエージェントに確実に伝えてください
