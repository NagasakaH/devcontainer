#!/bin/bash
# =============================================================================
# shfmt Feature Install Script
#
# Installs shfmt - a shell script formatter
# https://github.com/mvdan/sh
# =============================================================================

set -e

VERSION="${VERSION:-3.10.0}"

echo "Installing shfmt v${VERSION}..."

# Detect architecture
ARCH=$(dpkg --print-architecture 2>/dev/null || uname -m)
case "$ARCH" in
    amd64|x86_64)
        SHFMT_ARCH="amd64"
        ;;
    arm64|aarch64)
        SHFMT_ARCH="arm64"
        ;;
    armv7l|armhf)
        SHFMT_ARCH="arm"
        ;;
    *)
        echo "Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

# Detect OS
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
case "$OS" in
    linux)
        SHFMT_OS="linux"
        ;;
    darwin)
        SHFMT_OS="darwin"
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

# Download URL
DOWNLOAD_URL="https://github.com/mvdan/sh/releases/download/v${VERSION}/shfmt_v${VERSION}_${SHFMT_OS}_${SHFMT_ARCH}"

echo "Downloading from: ${DOWNLOAD_URL}"

# Install dependencies if not present
if ! command -v curl &> /dev/null; then
    apt-get update && apt-get install -y --no-install-recommends curl ca-certificates
fi

# Download and install
cd /tmp
curl -fsSL "${DOWNLOAD_URL}" -o shfmt
chmod +x shfmt
mv shfmt /usr/local/bin/shfmt

# Verify installation
echo "shfmt v${VERSION} installed successfully!"
shfmt --version

# Cleanup
apt-get clean 2>/dev/null || true
rm -rf /var/lib/apt/lists/* 2>/dev/null || true
