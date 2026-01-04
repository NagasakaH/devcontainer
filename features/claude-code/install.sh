#!/bin/bash
set -e

echo "Installing Claude Code CLI..."

# Install Claude Code CLI globally via npm
if command -v npm &> /dev/null; then
    npm install -g @anthropic-ai/claude-code
    echo "Claude Code CLI installed successfully"
else
    echo "Error: npm is not available. Please ensure Node.js feature is installed first."
    exit 1
fi

# Verify installation
if command -v claude &> /dev/null; then
    claude --version
    echo "Claude Code CLI is ready to use"
else
    echo "Warning: Claude Code CLI installation may have failed"
fi
