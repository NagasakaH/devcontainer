#!/bin/bash
# Start tmux session with 3 windows for development

# Ensure UTF-8 locale for proper icon display
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# Get workspace directory (first directory in /workspaces/)
WORKSPACE_DIR=$(ls -d /workspaces/*/ 2>/dev/null | head -n 1)

if [ -z "$WORKSPACE_DIR" ]; then
    echo "Error: No workspace directory found in /workspaces/"
    exit 1
fi

# Remove trailing slash
WORKSPACE_DIR=${WORKSPACE_DIR%/}

SESSION_NAME="dev"

# Check if session already exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Session '$SESSION_NAME' already exists. Attaching..."
    tmux attach-session -t "$SESSION_NAME"
    exit 0
fi

# Create new session with first window (nvim)
tmux new-session -d -s "$SESSION_NAME" -n "nvim" -c "$WORKSPACE_DIR"
tmux send-keys -t "$SESSION_NAME:1" "nvim ." C-m

# Create second window (Claude Code)
tmux new-window -t "$SESSION_NAME:2" -n "claude" -c "$WORKSPACE_DIR"
tmux send-keys -t "$SESSION_NAME:2" "claude" C-m

# Create third window (Bash)
tmux new-window -t "$SESSION_NAME:3" -n "bash" -c "$WORKSPACE_DIR"

# Select first window and attach
tmux select-window -t "$SESSION_NAME:1"
tmux attach-session -t "$SESSION_NAME"
