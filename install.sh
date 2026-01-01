#!/bin/bash

# move to script dir
cd "$(dirname "$0")"

SCRIPT_DIR="$PWD"

# install devcontainer cli
if ! command -v devcontainer &> /dev/null; then
	echo "Installing devcontainer/cli..."
	sudo npm install -g @devcontainers/cli
fi

# install .tmux.conf
if [ -e "$HOME/.tmux.conf" ]; then
	echo "Backing up existing .tmux.conf to .tmux.conf.old"
	mv "$HOME/.tmux.conf" "$HOME/.tmux.conf.old"
fi
echo "Installing .tmux.conf..."
ln -sf "$SCRIPT_DIR/dotfiles/.tmux.conf" "$HOME/.tmux.conf"

# Add bin/ directory to PATH if not already added
BIN_PATH="$SCRIPT_DIR/bin"
SHELL_RC=""

# Detect shell and set appropriate RC file
if [ -n "$ZSH_VERSION" ]; then
	SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
	SHELL_RC="$HOME/.bashrc"
fi

if [ -n "$SHELL_RC" ]; then
	# Check if PATH already contains bin directory
	if ! grep -q "export PATH=\"\$PATH:$BIN_PATH\"" "$SHELL_RC" 2>/dev/null; then
		echo ""
		echo "# DevContainer bin directory" >> "$SHELL_RC"
		echo "export PATH=\"\$PATH:$BIN_PATH\"" >> "$SHELL_RC"
		echo "Added $BIN_PATH to PATH in $SHELL_RC"
		echo "Please run: source $SHELL_RC"
	else
		echo "PATH already includes $BIN_PATH"
	fi
fi

# Make vimcontainer executable
chmod +x "$BIN_PATH/vimcontainer"
echo "Made vimcontainer executable"

# install lazyvim
# https://github.com/NagasakaH/LazyVim
