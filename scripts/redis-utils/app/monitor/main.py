#!/usr/bin/env python3
"""
Redis Agent Monitor - メインアプリケーション

summoner/moogle/chocoboエージェント間のRedisメッセージを
リアルタイムでモニタリングするStreamlitアプリ。

Usage:
    cd /workspaces/devcontainer/scripts/redis-utils
    streamlit run app/monitor/main.py
"""

import time
from typing import Optional

import streamlit as st

from ..config import RedisConfig, get_default_config
from .services.session_scanner import SessionInfo, SessionScanner
from .services.pubsub_listener import MonitorMessage, PubSubListener
from .components.session_selector import render_session_selector
from .components.chat_view import (
    render_chat_view,
    render_chat_controls,
    render_message_type_legend,
)
from .components.queue_status import render_queue_status, render_compact_queue_status


# ページ設定
st.set_page_config(
    page_title="Redis Agent Monitor",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state() -> None:
    """セッション状態を初期化"""
    if "messages" not in st.session_state:
        st.session_state.messages: list[MonitorMessage] = []
    
    if "listener" not in st.session_state:
        st.session_state.listener: Optional[PubSubListener] = None
    
    if "selected_session_id" not in st.session_state:
        st.session_state.selected_session_id: Optional[str] = None
    
    if "last_update" not in st.session_state:
        st.session_state.last_update: float = 0


def get_scanner() -> SessionScanner:
    """セッションスキャナーを取得（キャッシュ）"""
    if "scanner" not in st.session_state:
        config = get_default_config()
        st.session_state.scanner = SessionScanner(config)
    return st.session_state.scanner


def start_listener(session: SessionInfo) -> bool:
    """
    Pub/Subリスナーを開始
    
    Args:
        session: セッション情報
    
    Returns:
        開始成功時True
    """
    # 既存のリスナーを停止
    stop_listener()
    
    try:
        config = get_default_config()
        listener = PubSubListener(
            channel=session.monitor_channel,
            config=config,
        )
        
        if listener.start():
            st.session_state.listener = listener
            st.session_state.selected_session_id = session.session_id
            st.session_state.messages = []
            return True
        
        return False
    
    except Exception as e:
        st.error(f"❌ リスナー開始エラー: {e}")
        return False


def stop_listener() -> None:
    """Pub/Subリスナーを停止"""
    if st.session_state.listener:
        st.session_state.listener.stop()
        st.session_state.listener = None
        st.session_state.selected_session_id = None


def update_messages() -> None:
    """メッセージを更新"""
    listener = st.session_state.listener
    if listener and listener.is_running:
        new_messages = listener.get_messages()
        if new_messages:
            st.session_state.messages.extend(new_messages)
            # 最大保持数を制限
            max_messages = 500
            if len(st.session_state.messages) > max_messages:
                st.session_state.messages = st.session_state.messages[-max_messages:]


def render_sidebar(scanner: SessionScanner) -> Optional[SessionInfo]:
    """
    サイドバーを描画
    
    Returns:
        選択されたセッション情報
    """
    with st.sidebar:
        st.title("📡 Redis Agent Monitor")
        st.markdown("---")
        
        # セッション選択
        selected_session = render_session_selector(scanner)
        
        if selected_session:
            st.markdown("---")
            
            # リスナー状態
            listener = st.session_state.listener
            current_session_id = st.session_state.selected_session_id
            
            if listener and listener.is_running and current_session_id == selected_session.session_id:
                st.success("🟢 モニタリング中")
                
                # キューステータス（コンパクト）
                render_compact_queue_status(scanner, selected_session)
                
                if st.button("⏹️ 停止", key="stop_listener"):
                    stop_listener()
                    st.rerun()
            else:
                st.info("🔴 停止中")
                
                if st.button("▶️ モニタリング開始", key="start_listener"):
                    if start_listener(selected_session):
                        st.rerun()
        
        st.markdown("---")
        
        # 凡例
        render_message_type_legend()
        
        # アプリ情報
        st.markdown("---")
        st.caption("Redis Agent Monitor v1.0.0")
        st.caption("🔧 [redis-utils]")
    
    return selected_session


def render_main_content(
    scanner: SessionScanner,
    session: Optional[SessionInfo],
) -> None:
    """メインコンテンツを描画"""
    st.title("🔍 Agent Communication Monitor")
    
    if not session:
        st.info("""
        👈 サイドバーからセッションを選択してください。
        
        ### 使い方
        
        1. summonerセッションを開始します
           ```bash
           redis-orch --mode summoner --max-children 3
           ```
        
        2. サイドバーでセッションを選択
        
        3. 「モニタリング開始」ボタンをクリック
        
        4. moogle/chocobo間のメッセージがリアルタイムで表示されます
        """)
        return
    
    listener = st.session_state.listener
    
    if not listener or not listener.is_running:
        st.warning("⚠️ サイドバーの「モニタリング開始」をクリックしてください")
        
        # キューステータスだけは表示
        with st.expander("📊 現在のキュー状態", expanded=True):
            render_queue_status(scanner, session)
        return
    
    # コントロール
    controls = render_chat_controls()
    
    # メッセージをクリア
    if controls.get("clear"):
        st.session_state.messages = []
        st.rerun()
    
    # 自動更新
    if controls.get("auto_scroll"):
        update_messages()
        # 自動リフレッシュ用のプレースホルダー
        refresh_interval = 1  # 秒
        time.sleep(0.1)  # 短い待機
    
    # メイン表示エリア
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # チャットビュー
        render_chat_view(
            messages=st.session_state.messages,
            show_raw=controls.get("show_raw", False),
        )
    
    with col2:
        # キューステータス
        render_queue_status(scanner, session)
    
    # 自動更新（ページ下部）
    if controls.get("auto_scroll"):
        st.empty()
        time.sleep(refresh_interval)
        st.rerun()


def main() -> None:
    """メインエントリーポイント"""
    # セッション状態を初期化
    init_session_state()
    
    # スキャナーを取得
    scanner = get_scanner()
    
    # サイドバー
    selected_session = render_sidebar(scanner)
    
    # メインコンテンツ
    render_main_content(scanner, selected_session)


if __name__ == "__main__":
    main()
