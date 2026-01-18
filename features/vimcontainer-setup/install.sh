#!/bin/bash
set -e

USERNAME="${USERNAME:-vscode}"

echo "Setting up Neovim data directory for user: ${USERNAME}..."

# Create the nvim data directory
NVIM_DATA_DIR="/home/${USERNAME}/.local/share/nvim"
mkdir -p "${NVIM_DATA_DIR}"

echo "Created directory: ${NVIM_DATA_DIR}"

# Set ownership to the specified user
if id "${USERNAME}" &>/dev/null; then
    chown -R "${USERNAME}:${USERNAME}" "/home/${USERNAME}/.local"
    echo "Ownership set to ${USERNAME}:${USERNAME}"
else
    echo "Warning: User ${USERNAME} does not exist. Skipping ownership change."
fi

echo "Neovim data directory setup completed successfully"
