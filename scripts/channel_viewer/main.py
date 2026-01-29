#!/usr/bin/env python3
"""TUI Channel Message Viewer - Entry Point.

A TUI application that displays messages from multiple channels.
Each channel receives messages in background threads and you can
switch between channels to view their messages.

Usage:
    python main.py

Key bindings:
    n - Create new channel
    d - Delete selected channel
    q - Quit application
    Up/Down - Select channel
"""

from tui import ChannelViewerApp


def main() -> None:
    """Run the TUI Channel Viewer application."""
    app = ChannelViewerApp()
    app.run()


if __name__ == "__main__":
    main()
