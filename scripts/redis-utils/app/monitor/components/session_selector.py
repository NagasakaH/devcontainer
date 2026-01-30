"""
セッションセレクターコンポーネント

Redisからアクティブなsummonerセッションを一覧表示し、
ユーザーが選択できるようにする。
"""

from typing import Optional

import streamlit as st

from ..services.session_scanner import SessionInfo, SessionScanner


def render_session_selector(scanner: SessionScanner) -> Optional[SessionInfo]:
    """
    セッションセレクターを描画
    
    Args:
        scanner: セッションスキャナー
    
    Returns:
        選択されたセッション情報（未選択の場合はNone）
    """
    st.subheader("📋 セッション選択")
    
    # 接続状態を確認
    if not scanner.is_connected():
        st.error("❌ Redisに接続できません")
        st.info("Redisサーバーが起動していることを確認してください")
        return None
    
    # セッションをスキャン
    try:
        sessions = scanner.scan_sessions()
    except ConnectionError as e:
        st.error(f"❌ セッションスキャンエラー: {e}")
        return None
    except RuntimeError as e:
        st.error(f"❌ エラー: {e}")
        return None
    
    if not sessions:
        st.warning("⚠️ アクティブなセッションが見つかりません")
        st.info("""
        summonerセッションを開始するには、以下のコマンドを実行してください:
        
        ```bash
        redis-orch --mode summoner --max-children 3
        ```
        """)
        
        # リフレッシュボタン
        if st.button("🔄 再スキャン", key="rescan_empty"):
            st.rerun()
        
        return None
    
    # セッション選択
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # セッション一覧を表示用にフォーマット
        session_options = {
            f"{s.session_id[:8]}... ({s.created_at})": s
            for s in sessions
        }
        
        selected_label = st.selectbox(
            "モニタリングするセッションを選択:",
            options=list(session_options.keys()),
            key="session_selector",
        )
    
    with col2:
        # リフレッシュボタン
        if st.button("🔄 更新", key="rescan_sessions"):
            st.rerun()
    
    if not selected_label:
        return None
    
    selected_session = session_options.get(selected_label)
    
    # 選択されたセッションの詳細を表示
    if selected_session:
        with st.expander("📝 セッション詳細", expanded=False):
            st.markdown(f"""
| 項目 | 値 |
|------|-----|
| **セッションID** | `{selected_session.session_id}` |
| **プレフィックス** | `{selected_session.prefix}` |
| **最大子エージェント数** | {selected_session.max_children} |
| **作成日時** | {selected_session.created_at} |
| **モード** | {selected_session.mode} |
| **モニターチャンネル** | `{selected_session.monitor_channel}` |
""")
            
            st.markdown("**タスクキュー:**")
            for i, queue in enumerate(selected_session.task_queues, 1):
                st.code(f"chocobo-{i}: {queue}")
            
            st.markdown("**報告キュー:**")
            st.code(selected_session.report_queue)
    
    return selected_session
