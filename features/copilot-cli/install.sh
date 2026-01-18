#!/bin/bash
set -e

echo "Installing GitHub Copilot CLI..."

# Create .copilot directory for vscode user before mount
# This ensures the directory exists with correct ownership
COPILOT_DIR="/home/vscode/.copilot"
if [ ! -d "$COPILOT_DIR" ]; then
  mkdir -p "$COPILOT_DIR"
  chown vscode:vscode "$COPILOT_DIR"
  echo "Created $COPILOT_DIR with vscode:vscode ownership"
fi

VERSION="${VERSION:-latest}"
INSTALL_DIR="/usr/local/bin"

# Detect architecture
case "$(uname -m)" in
  x86_64|amd64) ARCH="x64" ;;
  aarch64|arm64) ARCH="arm64" ;;
  *) echo "Error: Unsupported architecture $(uname -m)" >&2; exit 1 ;;
esac

# Determine download URL
if [ "$VERSION" = "latest" ]; then
  DOWNLOAD_URL="https://github.com/github/copilot-cli/releases/latest/download/copilot-linux-${ARCH}.tar.gz"
else
  # Prefix version with 'v' if not already present
  case "$VERSION" in
    v*) ;;
    *) VERSION="v$VERSION" ;;
  esac
  DOWNLOAD_URL="https://github.com/github/copilot-cli/releases/download/${VERSION}/copilot-linux-${ARCH}.tar.gz"
fi

echo "Downloading from: $DOWNLOAD_URL"

# Download and extract
TMP_DIR="$(mktemp -d)"
TMP_TARBALL="$TMP_DIR/copilot-linux-${ARCH}.tar.gz"

if command -v curl >/dev/null 2>&1; then
  curl -fsSL "$DOWNLOAD_URL" -o "$TMP_TARBALL"
elif command -v wget >/dev/null 2>&1; then
  wget -qO "$TMP_TARBALL" "$DOWNLOAD_URL"
else
  echo "Error: Neither curl nor wget found."
  rm -rf "$TMP_DIR"
  exit 1
fi

# Validate tarball
if ! tar -tzf "$TMP_TARBALL" >/dev/null 2>&1; then
  echo "Error: Downloaded file is not a valid tarball or is corrupted." >&2
  rm -rf "$TMP_DIR"
  exit 1
fi

# Install binary
mkdir -p "$INSTALL_DIR"
tar -xz -C "$INSTALL_DIR" -f "$TMP_TARBALL"
chmod +x "$INSTALL_DIR/copilot"
rm -rf "$TMP_DIR"

# Verify installation
if command -v copilot >/dev/null 2>&1; then
  echo "GitHub Copilot CLI installed successfully to $INSTALL_DIR/copilot"
else
  echo "Warning: GitHub Copilot CLI installation may have failed"
fi
