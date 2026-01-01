#!/bin/bash
set -e

VERSION="${VERSION:-latest}"

echo "Installing LuaRocks..."

# Install dependencies
apt-get update
apt-get install -y lua5.4 liblua5.4-dev unzip wget

# Determine the user to install for (DevContainer sets _REMOTE_USER)
INSTALL_USER="${_REMOTE_USER:-${USERNAME:-vscode}}"
USER_HOME=$(getent passwd "${INSTALL_USER}" | cut -d: -f6)

echo "Installing LuaRocks for user: ${INSTALL_USER} (home: ${USER_HOME})"

# Determine version to install
if [ "$VERSION" = "latest" ]; then
    LUAROCKS_VERSION="3.11.1"
else
    LUAROCKS_VERSION="$VERSION"
fi

# Download and install LuaRocks
DOWNLOAD_URL="https://luarocks.org/releases/luarocks-${LUAROCKS_VERSION}.tar.gz"
TEMP_DIR="/tmp/luarocks-install"

mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

echo "Downloading LuaRocks ${LUAROCKS_VERSION} from: ${DOWNLOAD_URL}"
if ! wget -q "$DOWNLOAD_URL" -O luarocks.tar.gz; then
    echo "Error: Failed to download LuaRocks from ${DOWNLOAD_URL}"
    exit 1
fi

# Verify it's a valid tar.gz by checking the first bytes (gzip magic number: 1f 8b)
if ! od -An -tx1 -N2 luarocks.tar.gz | grep -q "1f 8b"; then
    echo "Error: Downloaded file is not a valid gzip archive"
    echo "First 100 bytes of downloaded file:"
    head -c 100 luarocks.tar.gz | od -A x -t x1z -v
    rm luarocks.tar.gz
    exit 1
fi

tar -xzf luarocks.tar.gz
cd "luarocks-${LUAROCKS_VERSION}"

# Configure and install
./configure --prefix=/usr/local --with-lua=/usr --with-lua-include=/usr/include/lua5.4
make
make install

# Clean up
cd /
rm -rf "$TEMP_DIR"

echo ""
echo "LuaRocks ${LUAROCKS_VERSION} installed successfully!"
echo "Installation location: /usr/local/bin/luarocks"
echo ""
echo "Usage:"
echo "  luarocks install <package>     # Install a Lua package"
echo "  luarocks list                  # List installed packages"
echo "  luarocks search <package>      # Search for packages"
