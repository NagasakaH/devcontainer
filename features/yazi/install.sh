#!/bin/bash
set -e

VERSION="${VERSION:-0.4.2}"

echo "Installing yazi v${VERSION}..."

# Detect architecture
ARCH=$(dpkg --print-architecture)
case "$ARCH" in
    amd64) ARCH_SUFFIX="x86_64" ;;
    arm64) ARCH_SUFFIX="aarch64" ;;
    *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

# Download pre-built binary
cd /tmp
DOWNLOAD_URL="https://github.com/sxyazi/yazi/releases/download/v${VERSION}/yazi-${ARCH_SUFFIX}-unknown-linux-gnu.zip"

echo "Downloading from: ${DOWNLOAD_URL}"
apt-get update && apt-get install -y --no-install-recommends curl ca-certificates unzip

curl -L "${DOWNLOAD_URL}" -o yazi.zip
unzip yazi.zip -d yazi-extracted

# Install binaries (yazi and ya)
chmod +x yazi-extracted/yazi-${ARCH_SUFFIX}-unknown-linux-gnu/yazi
chmod +x yazi-extracted/yazi-${ARCH_SUFFIX}-unknown-linux-gnu/ya
mv yazi-extracted/yazi-${ARCH_SUFFIX}-unknown-linux-gnu/yazi /usr/local/bin/yazi
mv yazi-extracted/yazi-${ARCH_SUFFIX}-unknown-linux-gnu/ya /usr/local/bin/ya

# Cleanup
rm -rf yazi.zip yazi-extracted
apt-get clean
rm -rf /var/lib/apt/lists/*

echo "yazi v${VERSION} installed successfully!"
yazi --version
