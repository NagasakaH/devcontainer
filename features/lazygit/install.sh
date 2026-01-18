#!/bin/bash
set -e

VERSION="${VERSION:-0.51.1}"

echo "Installing lazygit v${VERSION}..."

# Detect architecture
ARCH=$(dpkg --print-architecture)
case "$ARCH" in
    amd64) LAZYGIT_ARCH="x86_64" ;;
    arm64) LAZYGIT_ARCH="arm64" ;;
    *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

# Download pre-built binary
cd /tmp
DOWNLOAD_URL="https://github.com/jesseduffield/lazygit/releases/download/v${VERSION}/lazygit_${VERSION}_Linux_${LAZYGIT_ARCH}.tar.gz"

echo "Downloading from: ${DOWNLOAD_URL}"

# Install dependencies if not present
if ! command -v curl &> /dev/null; then
    apt-get update && apt-get install -y --no-install-recommends curl ca-certificates
fi

curl -L "${DOWNLOAD_URL}" -o lazygit.tar.gz
tar -xzf lazygit.tar.gz lazygit
chmod +x lazygit
mv lazygit /usr/local/bin/lazygit

# Cleanup
rm -f lazygit.tar.gz
apt-get clean 2>/dev/null || true
rm -rf /var/lib/apt/lists/* 2>/dev/null || true

echo "lazygit v${VERSION} installed successfully!"
lazygit --version
