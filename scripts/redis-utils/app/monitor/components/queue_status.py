"""
キューステータスコンポーネント

各キューの現在のメッセージ数を表示する。
"""

from typing import Optional

import streamlit as st

from ..services.session_scanner import SessionInfo, SessionScanner


def render_queue_status(
    scanner: SessionScanner,
    session: SessionInfo,
) -> None:
    """
    キューステータスを描画
    
    Args:
        scanner: セッションスキャナー
        session: セッション情報
    """
    st.subheader("📊 キュー状態")
    
    try:
        queue_lengths = scanner.get_queue_lengths(session)
    except Exception as e:
        st.error(f"❌ キュー情報取得エラー: {e}")
        return
    
    if not queue_lengths:
        st.info("キュー情報を取得できません")
        return
    
    # タスクキュー（moogle → chocobo）
    st.markdown("**📤 タスクキュー (moogle → chocobo)**")
    
    task_cols = st.columns(min(len(session.task_queues), 5))
    for i, queue in enumerate(session.task_queues):
        col_idx = i % len(task_cols)
        with task_cols[col_idx]:
            length = queue_lengths.get(queue, 0)
            # キュー名を短縮
            short_name = f"chocobo-{i+1}"
            
            # メトリクス表示
            if length > 0:
                st.metric(
                    label=short_name,
                    value=length,
                    delta=None,
                    help=f"キュー: {queue}",
                )
            else:
                st.metric(
                    label=short_name,
                    value="0",
                    delta=None,
                    help=f"キュー: {queue}",
                )
    
    st.markdown("---")
    
    # 報告キュー（chocobo → moogle）
    st.markdown("**📥 報告キュー (chocobo → moogle)**")
    
    report_length = queue_lengths.get(session.report_queue, 0)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.metric(
            label="reports",
            value=report_length,
            delta=None,
            help=f"キュー: {session.report_queue}",
        )


def render_queue_summary(
    scanner: SessionScanner,
    session: SessionInfo,
) -> dict[str, int]:
    """
    キュー状態のサマリーを取得
    
    Args:
        scanner: セッションスキャナー
        session: セッション情報
    
    Returns:
        サマリー情報の辞書
    """
    try:
        queue_lengths = scanner.get_queue_lengths(session)
    except Exception:
        return {"total_tasks": 0, "total_reports": 0, "active_queues": 0}
    
    total_tasks = sum(
        queue_lengths.get(q, 0)
        for q in session.task_queues
    )
    total_reports = queue_lengths.get(session.report_queue, 0)
    active_queues = sum(
        1 for q in session.task_queues
        if queue_lengths.get(q, 0) > 0
    )
    
    return {
        "total_tasks": total_tasks,
        "total_reports": total_reports,
        "active_queues": active_queues,
    }


def render_compact_queue_status(
    scanner: SessionScanner,
    session: SessionInfo,
) -> None:
    """
    コンパクトなキューステータスを描画（サイドバー用）
    
    Args:
        scanner: セッションスキャナー
        session: セッション情報
    """
    summary = render_queue_summary(scanner, session)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "📤 待機タスク",
            summary["total_tasks"],
        )
    
    with col2:
        st.metric(
            "📥 未読報告",
            summary["total_reports"],
        )
