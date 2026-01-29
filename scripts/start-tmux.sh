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

# Static session name
SESSION_NAME="dev"

# Check if session already exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
	echo "Session '$SESSION_NAME' already exists. Attaching..."
	tmux attach-session -t "$SESSION_NAME"
	exit 0
fi

# Create new session with window 0 (agent_log)
tmux new-session -d -s "$SESSION_NAME" -n "agent_log" -c "$WORKSPACE_DIR"

# Start markdown viewer in agent_log window if available
MD_VIEWER=""
for viewer in "$WORKSPACE_DIR/scripts/markdown-viewer.sh" \
              "$WORKSPACE_DIR/scripts/markdown-viewer.py" \
              "$WORKSPACE_DIR/scripts/md-viewer.sh"; do
    if [ -x "$viewer" ]; then
        MD_VIEWER="$viewer"
        break
    fi
done

if [ -n "$MD_VIEWER" ]; then
    tmux send-keys -t "$SESSION_NAME:0" "$MD_VIEWER" C-m
fi

# Create window 1 (editor/nvim)
tmux new-window -t "$SESSION_NAME:1" -n "editor" -c "$WORKSPACE_DIR"
# tmux send-keys -t "$SESSION_NAME:1" "nvim ." C-m

# Create window 2 (Claude Code)
tmux new-window -t "$SESSION_NAME:2" -n "copilot" -c "$WORKSPACE_DIR"
# tmux send-keys -t "$SESSION_NAME:2" "cplt" C-m

# Create window 3 (Bash)
tmux new-window -t "$SESSION_NAME:3" -n "bash" -c "$WORKSPACE_DIR"

# Select window 1 (editor) and attach
tmux select-window -t "$SESSION_NAME:1"
tmux attach-session -t "$SESSION_NAME"
