"""TUI components for the channel viewer application."""

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message as TextualMessage
from textual.reactive import reactive
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

try:
    from .channel import Channel, ChannelManager, ChannelStatus
    from .message import Message
except ImportError:
    from channel import Channel, ChannelManager, ChannelStatus
    from message import Message


class ChannelListItem(ListItem):
    """A list item representing a channel."""

    def __init__(self, channel: Channel) -> None:
        """Initialize with a channel."""
        super().__init__()
        self.channel = channel

    def compose(self) -> ComposeResult:
        """Compose the channel list item."""
        status_icon = self._get_status_icon()
        yield Label(f"{status_icon} {self.channel.name}", id="channel-label")

    def _get_status_icon(self) -> str:
        """Get status icon based on channel status."""
        icons = {
            ChannelStatus.DISCONNECTED: "⚫",
            ChannelStatus.CONNECTING: "🟡",
            ChannelStatus.CONNECTED: "🟢",
            ChannelStatus.ERROR: "🔴",
        }
        return icons.get(self.channel.status, "⚪")

    def update_display(self) -> None:
        """Update the display to reflect current state."""
        label = self.query_one("#channel-label", Label)
        status_icon = self._get_status_icon()
        msg_count = self.channel.message_count()
        label.update(f"{status_icon} {self.channel.name} ({msg_count})")


class MessageDisplay(Static):
    """Widget to display messages for a channel."""

    messages: reactive[list] = reactive(list, recompose=True)

    def __init__(self, **kwargs) -> None:
        """Initialize the message display."""
        super().__init__(**kwargs)
        self._messages: list[Message] = []

    def compose(self) -> ComposeResult:
        """Compose the message display."""
        if not self._messages:
            yield Static("No messages yet...", classes="no-messages")
        else:
            for msg in self._messages[-50:]:  # Show last 50 messages
                yield Static(msg.formatted(), classes="message-line")

    def set_messages(self, messages: list[Message]) -> None:
        """Set messages and refresh display."""
        self._messages = messages
        self.recompose()
        # Auto-scroll to bottom
        self.scroll_end(animate=False)


class StatusBar(Static):
    """Status bar showing connection info."""

    def __init__(self, **kwargs) -> None:
        """Initialize status bar."""
        super().__init__(**kwargs)
        self._channel_count = 0
        self._connected_count = 0
        self._total_messages = 0

    def update_status(
        self, channel_count: int, connected_count: int, total_messages: int
    ) -> None:
        """Update the status bar."""
        self._channel_count = channel_count
        self._connected_count = connected_count
        self._total_messages = total_messages
        self.update(
            f"Channels: {connected_count}/{channel_count} connected | "
            f"Total Messages: {total_messages}"
        )


class NewChannelRequested(TextualMessage):
    """Message sent when a new channel is requested."""

    pass


class DeleteChannelRequested(TextualMessage):
    """Message sent when channel deletion is requested."""

    pass


class ChannelViewerApp(App):
    """Main TUI application for viewing channel messages."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 2;
        grid-columns: 1fr 3fr;
        grid-rows: 1fr auto;
    }

    #channel-list-container {
        border: solid green;
        height: 100%;
        padding: 1;
    }

    #channel-list {
        height: 100%;
    }

    #message-container {
        border: solid blue;
        height: 100%;
        padding: 1;
    }

    #message-display {
        height: 100%;
        overflow-y: auto;
    }

    #status-bar {
        column-span: 2;
        height: 3;
        border: solid yellow;
        padding: 1;
        text-align: center;
    }

    .message-line {
        padding: 0 1;
    }

    .no-messages {
        color: $text-muted;
        text-style: italic;
        padding: 1;
    }

    #channel-title {
        text-style: bold;
        padding-bottom: 1;
    }

    #message-title {
        text-style: bold;
        padding-bottom: 1;
    }

    ChannelListItem {
        padding: 0 1;
    }

    ChannelListItem:hover {
        background: $surface-lighten-1;
    }

    ListView > ListItem.--highlight {
        background: $accent;
    }
    """

    BINDINGS = [
        Binding("n", "new_channel", "New Channel"),
        Binding("d", "delete_channel", "Delete Channel"),
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self) -> None:
        """Initialize the application."""
        super().__init__()
        self._manager = ChannelManager(
            on_message_received=self._on_message_received,
            on_status_changed=self._on_status_changed,
        )
        self._selected_channel_id: str | None = None
        self._refresh_timer = None

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header()

        with Container(id="channel-list-container"):
            yield Label("📡 Channels", id="channel-title")
            yield ListView(id="channel-list")

        with Container(id="message-container"):
            yield Label("💬 Messages", id="message-title")
            yield MessageDisplay(id="message-display")

        yield StatusBar(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        # Create initial channels
        self._manager.create_channel("General")
        self._manager.create_channel("Random")
        self._manager.create_channel("Alerts")

        # Refresh the channel list
        self._refresh_channel_list()

        # Start periodic refresh timer
        self._refresh_timer = self.set_interval(1.0, self._periodic_refresh)

    def _refresh_channel_list(self) -> None:
        """Refresh the channel list view."""
        list_view = self.query_one("#channel-list", ListView)
        list_view.clear()

        for channel in self._manager.get_all_channels():
            item = ChannelListItem(channel)
            list_view.append(item)

        # Select first channel if none selected
        if self._selected_channel_id is None:
            channels = self._manager.get_all_channels()
            if channels:
                self._selected_channel_id = channels[0].id
                if list_view.children:
                    list_view.index = 0

        self._refresh_messages()
        self._refresh_status()

    def _refresh_messages(self) -> None:
        """Refresh the message display for selected channel."""
        display = self.query_one("#message-display", MessageDisplay)
        title = self.query_one("#message-title", Label)

        if self._selected_channel_id:
            channel = self._manager.get_channel(self._selected_channel_id)
            if channel:
                title.update(f"💬 {channel.name}")
                display.set_messages(channel.get_messages())
                return

        title.update("💬 Messages")
        display.set_messages([])

    def _refresh_status(self) -> None:
        """Refresh the status bar."""
        status_bar = self.query_one("#status-bar", StatusBar)
        channels = self._manager.get_all_channels()
        status_bar.update_status(
            channel_count=len(channels),
            connected_count=self._manager.connected_count(),
            total_messages=self._manager.total_message_count(),
        )

    def _periodic_refresh(self) -> None:
        """Periodic refresh callback."""
        # Update channel list items
        list_view = self.query_one("#channel-list", ListView)
        for item in list_view.children:
            if isinstance(item, ChannelListItem):
                item.update_display()

        # Refresh messages and status
        self._refresh_messages()
        self._refresh_status()

    def _on_message_received(self, channel_id: str, message: Message) -> None:
        """Callback when a message is received."""
        # UI will be updated by periodic refresh
        pass

    def _on_status_changed(self, channel_id: str, status: ChannelStatus) -> None:
        """Callback when channel status changes."""
        # UI will be updated by periodic refresh
        pass

    @on(ListView.Selected)
    def on_channel_selected(self, event: ListView.Selected) -> None:
        """Handle channel selection."""
        if isinstance(event.item, ChannelListItem):
            self._selected_channel_id = event.item.channel.id
            self._refresh_messages()

    def action_new_channel(self) -> None:
        """Create a new channel."""
        self._manager.create_channel()
        self._refresh_channel_list()
        self.notify("New channel created!")

    def action_delete_channel(self) -> None:
        """Delete the selected channel."""
        if self._selected_channel_id:
            channel = self._manager.get_channel(self._selected_channel_id)
            if channel:
                name = channel.name
                self._manager.delete_channel(self._selected_channel_id)
                self._selected_channel_id = None
                self._refresh_channel_list()
                self.notify(f"Channel '{name}' deleted!")
        else:
            self.notify("No channel selected!", severity="warning")

    def action_refresh(self) -> None:
        """Manual refresh."""
        self._refresh_channel_list()
        self.notify("Refreshed!")

    def action_quit(self) -> None:
        """Quit the application."""
        self._manager.shutdown()
        self.exit()
