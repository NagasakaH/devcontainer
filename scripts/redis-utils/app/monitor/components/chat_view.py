"""
チャットビューコンポーネント

メッセージを送信者ごとに色分けして表示する。
タイムスタンプ付きで時系列表示。
"""

import json
from typing import Optional

import streamlit as st

from ..services.pubsub_listener import MonitorMessage


# 送信者ごとの色設定
SENDER_COLORS = {
    "summoner": "#9B59B6",    # 紫
    "moogle": "#3498DB",       # 青
    "chocobo": "#27AE60",      # 緑
    "chocobo-1": "#27AE60",    # 緑
    "chocobo-2": "#2ECC71",    # ライトグリーン
    "chocobo-3": "#1ABC9C",    # ターコイズ
    "chocobo-4": "#16A085",    # ダークターコイズ
    "chocobo-5": "#F39C12",    # オレンジ
    "chocobo-6": "#E67E22",    # ダークオレンジ
    "chocobo-7": "#E74C3C",    # 赤
    "chocobo-8": "#C0392B",    # ダーク赤
    "chocobo-9": "#8E44AD",    # ダーク紫
    "unknown": "#7F8C8D",      # グレー
}

# 送信者ごとの絵文字
SENDER_EMOJI = {
    "summoner": "🌟",
    "moogle": "🐾",
    "chocobo": "🐤",
    "unknown": "❓",
}


def get_sender_color(sender: str) -> str:
    """送信者の色を取得"""
    if sender in SENDER_COLORS:
        return SENDER_COLORS[sender]
    if sender.startswith("chocobo-"):
        return SENDER_COLORS.get("chocobo", "#27AE60")
    return SENDER_COLORS["unknown"]


def get_sender_emoji(sender: str) -> str:
    """送信者の絵文字を取得"""
    if sender in SENDER_EMOJI:
        return SENDER_EMOJI[sender]
    if sender.startswith("chocobo"):
        return "🐤"
    return SENDER_EMOJI["unknown"]


def render_message(msg: MonitorMessage, show_raw: bool = False) -> None:
    """
    メッセージを1件描画
    
    Args:
        msg: モニターメッセージ
        show_raw: 生データも表示するか
    """
    color = get_sender_color(msg.sender)
    emoji = get_sender_emoji(msg.sender)
    
    # タイムスタンプ
    timestamp_str = msg.timestamp.strftime("%H:%M:%S.%f")[:-3]
    
    # メッセージスタイル
    st.markdown(
        f"""
        <div style="
            border-left: 4px solid {color};
            padding: 8px 12px;
            margin: 4px 0;
            background-color: rgba(0,0,0,0.05);
            border-radius: 0 8px 8px 0;
        ">
            <div style="
                font-size: 0.8em;
                color: {color};
                font-weight: bold;
                margin-bottom: 4px;
            ">
                {emoji} {msg.sender} <span style="color: #888; font-weight: normal;">[{timestamp_str}]</span>
            </div>
            <div style="font-size: 0.95em;">
                {msg.get_display_content()}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # 生データを展開可能な形式で表示
    if show_raw and msg.parsed_data:
        with st.expander("📋 詳細 (JSON)", expanded=False):
            st.json(msg.parsed_data)


def render_chat_view(
    messages: list[MonitorMessage],
    show_raw: bool = False,
    max_messages: int = 100,
) -> None:
    """
    チャットビューを描画
    
    Args:
        messages: メッセージのリスト
        show_raw: 生データも表示するか
        max_messages: 表示する最大メッセージ数
    """
    st.subheader("💬 メッセージストリーム")
    
    if not messages:
        st.info("📭 まだメッセージがありません。セッションの活動を待機中...")
        return
    
    # メッセージ数の表示
    total_count = len(messages)
    display_count = min(total_count, max_messages)
    
    st.caption(f"表示: {display_count} / {total_count} メッセージ")
    
    # 最新のメッセージを表示（逆順で表示：新しいものが上）
    displayed = messages[-max_messages:] if len(messages) > max_messages else messages
    
    # チャットコンテナ
    with st.container():
        for msg in reversed(displayed):
            render_message(msg, show_raw=show_raw)


def render_chat_controls() -> dict:
    """
    チャットビューのコントロールを描画
    
    Returns:
        コントロール設定の辞書
    """
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        auto_scroll = st.checkbox("🔄 自動更新", value=True, key="auto_scroll")
    
    with col2:
        show_raw = st.checkbox("📋 詳細表示", value=False, key="show_raw")
    
    with col3:
        if st.button("🗑️ クリア", key="clear_messages"):
            return {"clear": True, "auto_scroll": auto_scroll, "show_raw": show_raw}
    
    return {"clear": False, "auto_scroll": auto_scroll, "show_raw": show_raw}


def render_message_type_legend() -> None:
    """メッセージタイプの凡例を描画"""
    with st.expander("📖 凡例", expanded=False):
        st.markdown("""
| アイコン | 送信者 | 説明 |
|---------|--------|------|
| 🌟 | **summoner** | オーケストレーション制御 |
| 🐾 | **moogle** | 親エージェント（タスク配信） |
| 🐤 | **chocobo-N** | 子エージェント（タスク実行） |

| メッセージタイプ | 説明 |
|-----------------|------|
| `task` | moogle → chocobo へのタスク指示 |
| `report` | chocobo → moogle への作業報告 |
| `shutdown` | 終了指示 |
| `initialized` | セッション初期化 |
| `cleanup` | セッションクリーンアップ |
""")
