#!/bin/bash
set -e

VERSION="${VERSION:-10.2.0}"

echo "Installing fd v${VERSION}..."

# Detect architecture
ARCH=$(dpkg --print-architecture)
case "$ARCH" in
    amd64) FD_ARCH="x86_64" ;;
    arm64) FD_ARCH="aarch64" ;;
    *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

# Download pre-built binary
cd /tmp
DOWNLOAD_URL="https://github.com/sharkdp/fd/releases/download/v${VERSION}/fd-v${VERSION}-${FD_ARCH}-unknown-linux-gnu.tar.gz"

echo "Downloading from: ${DOWNLOAD_URL}"

# Install dependencies if not present
if ! command -v curl &> /dev/null; then
    apt-get update && apt-get install -y --no-install-recommends curl ca-certificates
fi

curl -L "${DOWNLOAD_URL}" -o fd.tar.gz
tar -xzf fd.tar.gz
chmod +x fd-v${VERSION}-${FD_ARCH}-unknown-linux-gnu/fd
mv fd-v${VERSION}-${FD_ARCH}-unknown-linux-gnu/fd /usr/local/bin/fd

# Cleanup
rm -rf fd.tar.gz fd-v${VERSION}-${FD_ARCH}-unknown-linux-gnu
apt-get clean 2>/dev/null || true
rm -rf /var/lib/apt/lists/* 2>/dev/null || true

echo "fd v${VERSION} installed successfully!"
fd --version
