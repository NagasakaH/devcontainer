#!/bin/bash
set -e

VERSION="${VERSION:-latest}"

echo "Installing easydotnet..."

# Check if dotnet is available
if ! command -v dotnet &> /dev/null; then
    echo "Error: dotnet CLI is required but not found. Please install .NET SDK first."
    exit 1
fi

# Determine the user to install for (DevContainer sets _REMOTE_USER)
INSTALL_USER="${_REMOTE_USER:-${USERNAME:-vscode}}"
USER_HOME=$(getent passwd "${INSTALL_USER}" | cut -d: -f6)

echo "Installing easydotnet and dotnet-ef for user: ${INSTALL_USER} (home: ${USER_HOME})"

# Install easydotnet as a global tool for the target user
if [ "$VERSION" = "latest" ]; then
    su - "${INSTALL_USER}" -c "dotnet tool install -g easydotnet"
else
    su - "${INSTALL_USER}" -c "dotnet tool install -g easydotnet --version ${VERSION}"
fi

# Install dotnet-ef (Entity Framework Core tools)
# Using version 8.0.11 for .NET 8 compatibility
# Note: Latest versions (9.0.11, 10.0.0) have broken NuGet packages
echo "Installing dotnet-ef..."
su - "${INSTALL_USER}" -c "dotnet tool install -g dotnet-ef --version 8.0.11"

# Add dotnet tools to PATH for all users via profile.d
cat << 'EOF' > /etc/profile.d/dotnet-tools.sh
export PATH="$PATH:$HOME/.dotnet/tools"
EOF

chmod +x /etc/profile.d/dotnet-tools.sh

# Install netcoredbg (debugger for .NET Core)
echo "Installing netcoredbg..."
NETCOREDBG_VERSION="3.1.3-1062"
NETCOREDBG_DIR="/usr/local/netcoredbg"

# Detect architecture
ARCH=$(dpkg --print-architecture)
case "$ARCH" in
    amd64) NETCOREDBG_ARCH="amd64" ;;
    arm64) NETCOREDBG_ARCH="arm64" ;;
    *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

# Download and install netcoredbg
DOWNLOAD_URL="https://github.com/Samsung/netcoredbg/releases/download/${NETCOREDBG_VERSION}/netcoredbg-linux-${NETCOREDBG_ARCH}.tar.gz"

mkdir -p "$NETCOREDBG_DIR"
cd /tmp

echo "Downloading netcoredbg from: ${DOWNLOAD_URL}"
if ! curl -fsSL "$DOWNLOAD_URL" -o netcoredbg.tar.gz; then
    echo "Error: Failed to download netcoredbg from ${DOWNLOAD_URL}"
    echo "Please check the version and architecture"
    exit 1
fi

# Verify it's a valid tar.gz by checking the first bytes (gzip magic number: 1f 8b)
if ! od -An -tx1 -N2 netcoredbg.tar.gz | grep -q "1f 8b"; then
    echo "Error: Downloaded file is not a valid gzip archive"
    echo "First 100 bytes of downloaded file:"
    head -c 100 netcoredbg.tar.gz | od -A x -t x1z -v
    rm netcoredbg.tar.gz
    exit 1
fi

tar -xzf netcoredbg.tar.gz -C "$NETCOREDBG_DIR" --strip-components=1
rm netcoredbg.tar.gz

# Create symlink to make it accessible
ln -sf "$NETCOREDBG_DIR/netcoredbg" /usr/local/bin/netcoredbg

echo "netcoredbg installed successfully at $NETCOREDBG_DIR"

echo ""
echo "easydotnet, dotnet-ef, and netcoredbg installed successfully for ${INSTALL_USER}!"
echo "Tool locations:"
echo "  - ${USER_HOME}/.dotnet/tools/dotnet-easydotnet"
echo "  - ${USER_HOME}/.dotnet/tools/dotnet-ef"
echo "  - /usr/local/bin/netcoredbg"
echo ""
echo "To use C# LSP with nvim:"
echo "  1. Open a C# file in nvim"
echo "  2. Run :Dotnet to access commands"
echo "  3. The Roslyn LSP will be automatically managed by easy-dotnet.nvim"
echo ""
echo "Debugging:"
echo "  - netcoredbg is installed for .NET debugging with nvim-dap"
echo "  - Entity Framework Core tools (dotnet-ef) are available for database migrations"
