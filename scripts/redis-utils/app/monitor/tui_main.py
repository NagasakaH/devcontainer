"""
Redis Agent Monitor - Textual TUI版（自動監視モード）

Textualベースのターミナルユーザーインターフェース。
すべてのアクティブセッションを自動監視し、メッセージをリアルタイムで表示。
"""

import json
from datetime import datetime
from typing import Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
    RichLog,
    Static,
)
from rich.text import Text

from .services.session_scanner import SessionInfo, SessionScanner
from .services.pubsub_listener import MonitorMessage, PubSubListener
from .services.log_storage import LogStorage, LogEntry
from .services.error_logger import log_error
from ..config import get_default_config


# メッセージタイプごとの色設定（Rich用）
TYPE_COLORS = {
    "task": "cyan",
    "report": "green",
}
DEFAULT_COLOR = "grey50"


def get_type_color(msg_type: str) -> str:
    """メッセージタイプの色を取得"""
    return TYPE_COLORS.get(msg_type, DEFAULT_COLOR)


def get_type_emoji(msg_type: str) -> str:
    """メッセージタイプの絵文字を取得"""
    if msg_type == "task":
        return "📤"
    elif msg_type == "report":
        return "📥"
    elif msg_type == "shutdown":
        return "🛑"
    return "💬"


def extract_chocobo_id_from_queue(queue_name: str) -> Optional[str]:
    """キュー名からchocobo IDを抽出
    
    Args:
        queue_name: キュー名（例: "summoner:abc123:tasks:1"）
        
    Returns:
        chocobo ID（例: "1"）、抽出できない場合はNone
    """
    if not queue_name:
        return None
    # キュー名が "summoner:{session_id}:tasks:{N}" 形式の場合
    if ":tasks:" in queue_name:
        parts = queue_name.split(":tasks:")
        if len(parts) == 2 and parts[1]:
            return parts[1]
    return None


class SessionList(Static):
    """セッション一覧ウィジェット（選択可能）"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sessions: list[SessionInfo] = []
        self._log_sessions: list[str] = []  # ログのみ存在するセッションID
    
    def compose(self) -> ComposeResult:
        yield ListView(id="session-listview")
    
    def update_sessions(
        self, 
        sessions: list[SessionInfo], 
        log_only_sessions: Optional[list[str]] = None
    ) -> None:
        """セッション一覧を更新
        
        差分更新方式を採用し、DuplicateIdsエラーを回避。
        既存ウィジェットは再利用し、不要なものだけ削除、新規は追加。
        
        Args:
            sessions: アクティブなセッション情報リスト
            log_only_sessions: ログのみ存在するセッションID（アクティブでない）
        """
        self._sessions = sessions
        
        # アクティブセッションのIDセットを作成（重複チェック用）
        active_session_ids = {s.session_id for s in sessions}
        
        # log_only_sessionsからアクティブセッションを除外
        self._log_sessions = [
            sid for sid in (log_only_sessions or [])
            if sid not in active_session_ids
        ]
        
        listview = self.query_one("#session-listview", ListView)
        
        # 既存ウィジェットのIDを収集
        existing_widget_ids: set[str] = set()
        for item in listview.children:
            if item.id:
                existing_widget_ids.add(item.id)
        
        # 今回必要なウィジェットIDを計算
        required_widget_ids: set[str] = set()
        
        # アクティブセッション用のIDを追加
        for session in sessions:
            required_widget_ids.add(f"active-{session.session_id}")
        
        # ログのみセッション用のIDを追加
        for session_id in self._log_sessions:
            required_widget_ids.add(f"log-{session_id}")
        
        # 不要なウィジェットを削除（差分：既存にあるが今回は不要）
        ids_to_remove = existing_widget_ids - required_widget_ids
        for widget_id in ids_to_remove:
            try:
                widget = listview.query_one(f"#{widget_id}", ListItem)
                widget.remove()
            except Exception:
                pass  # ウィジェットが見つからない場合は無視
        
        # 新規ウィジェットを追加（差分：今回必要だが既存にない）
        ids_to_add = required_widget_ids - existing_widget_ids
        
        # アクティブなセッション（新規のみ追加）
        for session in sessions:
            widget_id = f"active-{session.session_id}"
            if widget_id in ids_to_add:
                short_id = session.session_id[:12] + "..." if len(session.session_id) > 15 else session.session_id
                mode_emoji = "🔥" if session.mode == "summoner" else "📋"
                item = ListItem(Label(f"{mode_emoji} {short_id}"), id=widget_id)
                listview.append(item)
        
        # ログのみ存在するセッション（新規のみ追加）
        for session_id in self._log_sessions:
            widget_id = f"log-{session_id}"
            if widget_id in ids_to_add:
                short_id = session_id[:12] + "..." if len(session_id) > 15 else session_id
                item = ListItem(Label(f"📁 {short_id}"), id=widget_id)
                listview.append(item)
    
    def get_session_count(self) -> int:
        """セッション数を取得"""
        return len(self._sessions) + len(self._log_sessions)
    
    def get_session_id_by_index(self, index: int) -> Optional[str]:
        """インデックスからセッションIDを取得"""
        if index < 0:
            return None
        
        # アクティブセッション
        if index < len(self._sessions):
            return self._sessions[index].session_id
        
        # ログのみセッション
        log_index = index - len(self._sessions)
        if log_index < len(self._log_sessions):
            return self._log_sessions[log_index]
        
        return None


class QueueStatus(Static):
    """キューステータスウィジェット"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._task_count = 0
        self._report_count = 0
    
    def compose(self) -> ComposeResult:
        yield Static("─" * 20, classes="divider")
        yield Static("📊 Queue Status", classes="section-title")
        yield Static("─" * 20, classes="divider")
        yield Static("📤 Tasks: 0", id="task-count")
        yield Static("📥 Reports: 0", id="report-count")
    
    def update_status(self, task_count: int, report_count: int) -> None:
        """ステータスを更新"""
        self._task_count = task_count
        self._report_count = report_count
        self.query_one("#task-count", Static).update(f"📤 Tasks: {task_count}")
        self.query_one("#report-count", Static).update(f"📥 Reports: {report_count}")


class MessageStream(Static):
    """メッセージストリームウィジェット"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._messages: list[MonitorMessage] = []
    
    def compose(self) -> ComposeResult:
        yield RichLog(highlight=True, markup=True, wrap=True, id="message-log")
    
    def add_message(self, msg: MonitorMessage, session_id: str = "") -> Optional[tuple[str, str, str]]:
        """メッセージを追加（[sender → receiver] message形式で表示）
        
        メッセージの方向を明確に表示:
        - タスク: [moogle → chocobo-N] instruction...
        - 報告: [chocobo-N → moogle] result...
        - shutdown: [moogle → chocobo-N] 終了
        
        Returns:
            成功時は (msg_type, sender, content) のタプル、失敗時はNone
        """
        self._messages.append(msg)
        log = self.query_one("#message-log", RichLog)
        
        # メッセージ内容をパース
        if not isinstance(msg.parsed_data, dict):
            return None
        
        # "message" 要素のみを対象とする
        message_content = msg.parsed_data.get("message")
        if not message_content:
            return None
        
        # キュー名を取得（タスクの宛先chocobo判定用）
        queue_name = msg.parsed_data.get("list", "")
        target_chocobo_id = extract_chocobo_id_from_queue(queue_name)
        
        # messageの中身をパース（JSON形式）
        try:
            if isinstance(message_content, str):
                message_data = json.loads(message_content)
            else:
                message_data = message_content
        except (json.JSONDecodeError, TypeError):
            return None
        
        if not isinstance(message_data, dict):
            return None
        
        # typeを取得
        msg_type = message_data.get("type", "unknown")
        
        # chocobo_idを取得（報告メッセージ用）
        # chocobo_id を優先、なければ child_id をフォールバック
        chocobo_id = message_data.get("chocobo_id") or message_data.get("child_id")
        
        # 送信者と受信者を決定
        if msg_type == "task":
            sender = "moogle"
            receiver = f"chocobo-{target_chocobo_id}" if target_chocobo_id else "chocobo"
        elif msg_type == "report":
            sender = f"chocobo-{chocobo_id}" if chocobo_id is not None else "chocobo"
            receiver = "moogle"
        elif msg_type == "status":
            sender = f"chocobo-{chocobo_id}" if chocobo_id is not None else "chocobo"
            receiver = "moogle"
        elif msg_type == "shutdown":
            sender = "moogle"
            receiver = f"chocobo-{target_chocobo_id}" if target_chocobo_id else "chocobo"
        else:
            sender = "unknown"
            receiver = "unknown"
        
        # メッセージ文言を決定
        max_length = 50
        if msg_type == "task":
            # instructionまたはpromptをチェック（両方に対応）
            content = message_data.get("instruction", "") or message_data.get("prompt", "")
        elif msg_type == "report":
            status = message_data.get("status", "")
            if status == "success":
                content = message_data.get("result", "")
            else:
                content = message_data.get("error", "")
        elif msg_type == "status":
            content = message_data.get("event", "")
        elif msg_type == "shutdown":
            content = message_data.get("reason", "") or "終了指示"
        else:
            content = str(message_data)
        
        # 文字列に変換し、長い場合は切り詰め
        content = str(content) if content else ""
        display_content = content[:max_length] + "..." if len(content) > max_length else content
        
        # 色と絵文字を取得
        color = get_type_color(msg_type)
        emoji = get_type_emoji(msg_type)
        
        # メッセージを整形: [sender → receiver] message
        text = Text()
        text.append(f"{emoji} ", style="bold")
        text.append("[", style="dim")
        text.append(f"{sender}", style="yellow")
        text.append(" → ", style="dim cyan")
        text.append(f"{receiver}", style="yellow")
        text.append("] ", style="dim")
        text.append(display_content, style="white")
        
        log.write(text)
        
        # ログ保存用に情報を返す（sender → receiver形式）
        direction_info = f"{sender} → {receiver}"
        return (msg_type, direction_info, content)
    
    def add_log_entry(self, entry: LogEntry) -> None:
        """ログエントリを表示（過去ログ読み込み用）
        
        新しい表示形式に対応:
        - タスク: [moogle → chocobo-N] instruction...
        - 報告: [chocobo-N → moogle] result...
        """
        log = self.query_one("#message-log", RichLog)
        
        msg_type = entry.msg_type
        sender = entry.sender
        content = entry.content
        
        # raw_dataから追加情報を抽出
        receiver = "unknown"
        if entry.raw_data:
            # キュー名からchocobo IDを抽出
            queue_name = entry.raw_data.get("list", "")
            target_chocobo_id = extract_chocobo_id_from_queue(queue_name)
            
            message_content = entry.raw_data.get("message")
            if message_content:
                try:
                    if isinstance(message_content, str):
                        message_data = json.loads(message_content)
                    else:
                        message_data = message_content
                    if isinstance(message_data, dict):
                        # instruction または prompt を取得
                        if msg_type == "task":
                            content = message_data.get("instruction", "") or message_data.get("prompt", "") or content
                        
                        # chocobo_id を取得（報告メッセージ用）
                        chocobo_id = message_data.get("chocobo_id") or message_data.get("child_id")
                        
                        # 送信者と受信者を再計算
                        if msg_type == "task":
                            sender = "moogle"
                            receiver = f"chocobo-{target_chocobo_id}" if target_chocobo_id else "chocobo"
                        elif msg_type == "report":
                            sender = f"chocobo-{chocobo_id}" if chocobo_id is not None else "chocobo"
                            receiver = "moogle"
                        elif msg_type == "shutdown":
                            sender = "moogle"
                            receiver = f"chocobo-{target_chocobo_id}" if target_chocobo_id else "chocobo"
                        else:
                            receiver = "moogle"
                except (json.JSONDecodeError, TypeError):
                    pass
        
        # 送信者情報が "sender → receiver" 形式の場合は分割
        if " → " in sender:
            parts = sender.split(" → ")
            if len(parts) == 2:
                sender = parts[0]
                receiver = parts[1]
        
        # 長い場合は切り詰め
        max_length = 50
        display_content = content[:max_length] + "..." if len(content) > max_length else content
        
        # 色と絵文字を取得
        emoji = get_type_emoji(msg_type)
        
        # メッセージを整形: [sender → receiver] message (with timestamp)
        text = Text()
        text.append(f"{emoji} ", style="bold")
        text.append("[", style="dim")
        text.append(f"{sender}", style="yellow")
        text.append(" → ", style="dim cyan")
        text.append(f"{receiver}", style="yellow")
        text.append("] ", style="dim")
        text.append(display_content, style="white")
        text.append(f" ({entry.timestamp[:19]})", style="dim")  # タイムスタンプを追加
        
        log.write(text)
    
    def show_session_header(self, session_id: str, message_count: int) -> None:
        """セッションヘッダーを表示"""
        log = self.query_one("#message-log", RichLog)
        
        short_id = session_id[:12] + "..." if len(session_id) > 15 else session_id
        
        header_text = Text()
        header_text.append("\n" + "═" * 40 + "\n", style="dim cyan")
        header_text.append(f"📂 Session: {short_id}\n", style="bold cyan")
        header_text.append(f"📝 {message_count} messages loaded from log\n", style="dim")
        header_text.append("═" * 40 + "\n", style="dim cyan")
        
        log.write(header_text)
    
    def clear_messages(self) -> None:
        """メッセージをクリア"""
        self._messages.clear()
        log = self.query_one("#message-log", RichLog)
        log.clear()

    def on_mount(self) -> None:
        """マウント時の初期化 - ウェルカムメッセージを表示"""
        log = self.query_one("#message-log", RichLog)
        welcome_text = Text()
        welcome_text.append("🎉 Redis Agent Monitor - Auto Mode\n\n", style="bold cyan")
        welcome_text.append("📖 Features:\n", style="bold yellow")
        welcome_text.append("  • ", style="white")
        welcome_text.append("Automatic monitoring", style="bold green")
        welcome_text.append(" of all active sessions\n", style="white")
        welcome_text.append("  • ", style="white")
        welcome_text.append("Auto-detection", style="bold green")
        welcome_text.append(" of new sessions (every 5s)\n", style="white")
        welcome_text.append("  • Press ", style="white")
        welcome_text.append("l", style="bold green")
        welcome_text.append(" to show/hide session list\n", style="white")
        welcome_text.append("  • Press ", style="white")
        welcome_text.append("c", style="bold green")
        welcome_text.append(" to clear messages\n", style="white")
        welcome_text.append("  • Press ", style="white")
        welcome_text.append("q", style="bold green")
        welcome_text.append(" to quit\n\n", style="white")
        welcome_text.append("─" * 40 + "\n", style="dim")
        log.write(welcome_text)


class StatusBar(Static):
    """ステータスバーウィジェット"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._monitoring_count = 0
    
    def compose(self) -> ComposeResult:
        yield Static("📡 Initializing...", id="status-text")
    
    def update_monitoring_count(self, count: int) -> None:
        """監視中のセッション数を更新"""
        self._monitoring_count = count
        
        if count == 0:
            status = "📡 Scanning for sessions..."
        elif count == 1:
            status = f"🟢 Monitoring {count} session"
        else:
            status = f"🟢 Monitoring {count} sessions"
        
        self.query_one("#status-text", Static).update(status)


class RedisMonitorApp(App):
    """Redis Agent Monitor TUI アプリケーション（自動監視モード）"""
    
    CSS = """
    Screen {
        background: transparent;
    }
    
    /* メインコンテナ - 画面全体を埋める */
    #main-container {
        width: 100%;
        height: 1fr;
        background: transparent;
    }
    
    /* 左パネル - セッション一覧とキューステータス */
    #left-panel {
        width: 1fr;
        height: 100%;
        min-width: 30;
        max-width: 50;
        border: round $primary;
        padding: 1;
        background: transparent;
        color: $text;
    }
    
    /* 右パネル - メッセージストリーム */
    #right-panel {
        width: 3fr;
        height: 100%;
        border: round $primary;
        padding: 1;
        background: transparent;
        color: $text;
    }
    
    /* セクションタイトル */
    .section-title {
        text-style: bold;
        color: $primary-lighten-2;
        padding: 0 0 1 0;
        background: transparent;
    }
    
    /* 区切り線 */
    .divider {
        color: $primary-darken-1;
    }
    
    /* セッション一覧 - 初期状態で非表示 */
    SessionList {
        height: auto;
        max-height: 60%;
        background: transparent;
        display: none;
    }
    
    SessionList.visible {
        display: block;
    }
    
    #session-listview {
        height: auto;
        max-height: 100%;
        border: solid $primary-darken-2;
        margin: 0 0 1 0;
        background: transparent;
        color: $text;
    }
    
    #session-listview > ListItem {
        padding: 0 1;
        background: transparent;
        color: $text;
    }
    
    #session-listview > ListItem:hover {
        background: $primary-darken-2;
        color: white;
    }
    
    #session-listview > ListItem.-highlight {
        background: $primary;
        color: white;
    }
    
    /* キューステータス */
    QueueStatus {
        height: auto;
        padding: 1 0;
        background: transparent;
        color: $text;
    }
    
    QueueStatus Static {
        background: transparent;
        color: $text;
    }
    
    /* メッセージストリーム */
    MessageStream {
        height: 1fr;
        background: transparent;
    }
    
    #message-log {
        height: 100%;
        border: solid $primary-darken-2;
        scrollbar-gutter: stable;
        background: transparent;
        color: $text;
    }
    
    /* ステータスバー */
    StatusBar {
        dock: bottom;
        height: 1;
        background: $primary-darken-3;
        padding: 0 1;
        color: white;
    }
    
    #status-text {
        text-style: bold;
        color: white;
        background: $primary-darken-3;
    }
    
    /* ボタン行 */
    .button-row {
        height: 3;
        margin: 1 0 0 0;
        background: transparent;
    }
    
    .button-row Button {
        margin: 0 1 0 0;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh_sessions", "Refresh"),
        Binding("l", "toggle_session_list", "Sessions"),
        Binding("c", "clear_messages", "Clear"),
    ]
    
    TITLE = "📡 Redis Agent Monitor"
    SUB_TITLE = "Auto-Monitoring Mode"
    
    def __init__(self):
        super().__init__()
        self._config = get_default_config()
        self._scanner: Optional[SessionScanner] = None
        # session_id -> PubSubListener のマッピング
        self._listeners: dict[str, PubSubListener] = {}
        # 監視中のセッションID一覧
        self._monitored_sessions: set[str] = set()
        # ログストレージ
        self._log_storage = LogStorage()
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Horizontal(id="main-container"):
            with Vertical(id="left-panel"):
                yield Static("📋 Sessions", classes="section-title")
                yield Button("📋 Show Sessions [l]", id="btn-show-sessions", variant="default")
                yield SessionList(id="session-list")
                yield QueueStatus(id="queue-status")
                with Horizontal(classes="button-row"):
                    yield Button("🔄 Refresh [r]", id="btn-refresh", variant="default")
            
            with Vertical(id="right-panel"):
                yield Static("💬 Message Stream", classes="section-title")
                yield MessageStream(id="message-stream")
                with Horizontal(classes="button-row"):
                    yield Button("🗑️ Clear [c]", id="btn-clear", variant="warning")
        
        yield StatusBar(id="status-bar")
        yield Footer()
    
    def on_mount(self) -> None:
        """マウント時の初期化 - 自動監視開始"""
        self._scanner = SessionScanner(self._config)
        
        # 初回スキャンと自動監視開始
        self._scan_and_connect()
        
        # 定期的なメッセージポーリング（0.5秒ごと）
        self.set_interval(0.5, self._poll_messages)
        
        # 定期的なセッションスキャン（5秒ごと）
        self.set_interval(5.0, self._scan_and_connect)
        
        # 定期的なキューステータス更新（2秒ごと）
        self.set_interval(2.0, self._update_queue_status)
    
    def on_unmount(self) -> None:
        """アンマウント時のクリーンアップ"""
        # すべてのリスナーを停止
        for listener in self._listeners.values():
            try:
                listener.stop()
            except Exception:
                pass
        self._listeners.clear()
        self._monitored_sessions.clear()
        
        if self._scanner:
            self._scanner.close()
    
    def _scan_and_connect(self) -> None:
        """セッションをスキャンし、新規セッションに自動接続"""
        if not self._scanner:
            return
        
        try:
            sessions = self._scanner.scan_sessions()
            
            # ログのみ存在するセッションを検出
            active_session_ids = {s.session_id for s in sessions}
            log_sessions = self._log_storage.list_sessions()
            log_only_sessions = [s for s in log_sessions if s not in active_session_ids]
            
            # UI更新
            session_list = self.query_one("#session-list", SessionList)
            session_list.update_sessions(sessions, log_only_sessions)
            
            # 新規セッションを検出して接続
            current_session_ids = {s.session_id for s in sessions}
            
            for session in sessions:
                if session.session_id not in self._monitored_sessions:
                    self._connect_to_session(session)
            
            # 終了したセッションのリスナーをクリーンアップ
            ended_sessions = self._monitored_sessions - current_session_ids
            for session_id in ended_sessions:
                self._disconnect_from_session(session_id)
            
            # ステータスバー更新
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.update_monitoring_count(len(self._monitored_sessions))
            
        except Exception as e:
            log_error(e, "RedisMonitorApp._scan_and_connect")
            self.notify(f"Scan error: {e}", severity="error")
    
    def _connect_to_session(self, session: SessionInfo) -> None:
        """セッションに接続"""
        try:
            listener = PubSubListener(
                channel=session.monitor_channel,
                config=self._config,
            )
            listener.start()
            
            self._listeners[session.session_id] = listener
            self._monitored_sessions.add(session.session_id)
            
            short_id = session.session_id[:12] + "..."
            self.notify(f"Connected: {short_id}", severity="information")
            
        except Exception as e:
            log_error(
                e,
                "RedisMonitorApp._connect_to_session",
                {"session_id": session.session_id, "channel": session.monitor_channel},
            )
            self.notify(f"Connection failed: {e}", severity="error")
    
    def _disconnect_from_session(self, session_id: str) -> None:
        """セッションから切断"""
        if session_id in self._listeners:
            try:
                self._listeners[session_id].stop()
            except Exception:
                pass
            del self._listeners[session_id]
        
        self._monitored_sessions.discard(session_id)
        
        short_id = session_id[:12] + "..."
        self.notify(f"Disconnected: {short_id}", severity="warning")
    
    @work(exclusive=True)
    async def action_refresh_sessions(self) -> None:
        """セッション一覧を手動更新"""
        self._scan_and_connect()
        self.notify("Sessions refreshed", severity="information")
    
    def action_clear_messages(self) -> None:
        """メッセージをクリア"""
        message_stream = self.query_one("#message-stream", MessageStream)
        message_stream.clear_messages()
        self.notify("Messages cleared", severity="information")
    
    @on(Button.Pressed, "#btn-refresh")
    def handle_refresh_button(self) -> None:
        """更新ボタン押下"""
        self.action_refresh_sessions()
    
    @on(Button.Pressed, "#btn-clear")
    def handle_clear_button(self) -> None:
        """クリアボタン押下"""
        self.action_clear_messages()
    
    def action_toggle_session_list(self) -> None:
        """セッション一覧の表示/非表示をトグル"""
        session_list = self.query_one("#session-list", SessionList)
        btn = self.query_one("#btn-show-sessions", Button)
        
        if session_list.has_class("visible"):
            session_list.remove_class("visible")
            btn.label = "📋 Show Sessions [l]"
        else:
            session_list.add_class("visible")
            btn.label = "📋 Hide Sessions [l]"
    
    @on(Button.Pressed, "#btn-show-sessions")
    def handle_show_sessions_button(self) -> None:
        """セッション一覧表示ボタン押下"""
        self.action_toggle_session_list()
    
    def _poll_messages(self) -> None:
        """全リスナーからメッセージをポーリング"""
        if not self._listeners:
            return
        
        message_stream = self.query_one("#message-stream", MessageStream)
        
        for session_id, listener in self._listeners.items():
            if not listener.is_running:
                continue
            
            messages = listener.get_messages()
            for msg in messages:
                result = message_stream.add_message(msg, session_id)
                
                # ログに保存
                if result:
                    msg_type, sender, content = result
                    self._log_storage.save_message(
                        session_id=session_id,
                        msg_type=msg_type,
                        sender=sender,
                        content=content,
                        raw_data=msg.parsed_data,
                    )
    
    @on(ListView.Selected, "#session-listview")
    def handle_session_selected(self, event: ListView.Selected) -> None:
        """セッション選択時のハンドラ"""
        session_list = self.query_one("#session-list", SessionList)
        
        # 選択されたインデックスからセッションIDを取得
        if event.list_view.index is not None:
            session_id = session_list.get_session_id_by_index(event.list_view.index)
            if session_id:
                self._load_and_display_session_logs(session_id)
    
    def _load_and_display_session_logs(self, session_id: str) -> None:
        """セッションのログを読み込んで表示"""
        message_stream = self.query_one("#message-stream", MessageStream)
        
        # メッセージをクリア
        message_stream.clear_messages()
        
        # ログを読み込み
        entries = self._log_storage.load_messages(session_id)
        
        if entries:
            # セッションヘッダーを表示
            message_stream.show_session_header(session_id, len(entries))
            
            # 各エントリを表示
            for entry in entries:
                message_stream.add_log_entry(entry)
            
            self.notify(f"Loaded {len(entries)} messages", severity="information")
        else:
            short_id = session_id[:12] + "..." if len(session_id) > 15 else session_id
            self.notify(f"No logs found for {short_id}", severity="warning")
    
    def _update_queue_status(self) -> None:
        """キューステータスを更新（全セッションの合計）"""
        if not self._scanner:
            return
        
        try:
            sessions = self._scanner.scan_sessions()
            total_tasks = 0
            total_reports = 0
            
            for session in sessions:
                if session.session_id in self._monitored_sessions:
                    queue_lengths = self._scanner.get_queue_lengths(session)
                    
                    task_count = sum(
                        v for k, v in queue_lengths.items()
                        if k in session.task_queues
                    )
                    report_count = queue_lengths.get(session.report_queue, 0)
                    
                    total_tasks += task_count
                    total_reports += report_count
            
            queue_status = self.query_one("#queue-status", QueueStatus)
            queue_status.update_status(total_tasks, total_reports)
        except Exception:
            pass  # エラーは無視


def main() -> None:
    """エントリーポイント"""
    app = RedisMonitorApp()
    app.run()


if __name__ == "__main__":
    main()
