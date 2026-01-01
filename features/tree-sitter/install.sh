#!/bin/bash
set -e

VERSION="${VERSION:-0.25.10}"

echo "Installing tree-sitter v${VERSION}..."

# Detect architecture
ARCH=$(dpkg --print-architecture)
case "$ARCH" in
    amd64) ARCH_SUFFIX="x64" ;;
    arm64) ARCH_SUFFIX="arm64" ;;
    *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

# Download pre-built binary
cd /tmp
DOWNLOAD_URL="https://github.com/tree-sitter/tree-sitter/releases/download/v${VERSION}/tree-sitter-linux-${ARCH_SUFFIX}.gz"

echo "Downloading from: ${DOWNLOAD_URL}"
apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

curl -L "${DOWNLOAD_URL}" -o tree-sitter.gz
gunzip tree-sitter.gz
chmod +x tree-sitter
mv tree-sitter /usr/local/bin/tree-sitter

# Cleanup
apt-get clean
rm -rf /var/lib/apt/lists/*

echo "tree-sitter v${VERSION} installed successfully!"
tree-sitter --version
