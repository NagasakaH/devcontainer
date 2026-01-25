#!/bin/bash
set -e

echo "Installing uv package manager..."

VERSION="${VERSION:-latest}"

# Check if uv is already installed
if command -v uv >/dev/null 2>&1; then
    INSTALLED_VERSION=$(uv --version 2>/dev/null | awk '{print $2}')
    echo "uv is already installed (version: ${INSTALLED_VERSION})"
    
    if [ "$VERSION" = "latest" ]; then
        echo "Skipping installation as uv is already present. Use a specific version to upgrade/downgrade."
        exit 0
    fi
    
    # Check if the installed version matches the requested version
    if [ "$INSTALLED_VERSION" = "$VERSION" ]; then
        echo "Requested version ${VERSION} is already installed. Skipping."
        exit 0
    fi
    
    echo "Proceeding to install requested version: ${VERSION}"
fi

# Detect architecture
ARCH="$(uname -m)"
case "$ARCH" in
    x86_64|amd64)
        echo "Detected architecture: x86_64 (amd64)"
        ;;
    aarch64|arm64)
        echo "Detected architecture: aarch64 (arm64)"
        ;;
    *)
        echo "Error: Unsupported architecture: ${ARCH}" >&2
        exit 1
        ;;
esac

# Detect OS
OS="$(uname -s)"
case "$OS" in
    Linux)
        echo "Detected OS: Linux"
        ;;
    Darwin)
        echo "Detected OS: macOS"
        ;;
    *)
        echo "Error: Unsupported operating system: ${OS}" >&2
        exit 1
        ;;
esac

# Ensure curl is available
if ! command -v curl >/dev/null 2>&1; then
    echo "Error: curl is required but not installed." >&2
    exit 1
fi

# Install uv using the official installer
# The installer automatically handles architecture detection
echo "Installing uv using official installer..."

# Set version environment variable if not latest
if [ "$VERSION" != "latest" ]; then
    # Ensure version doesn't have 'v' prefix (uv uses semantic versioning without v)
    VERSION="${VERSION#v}"
    export UV_INSTALLER_VERSION="$VERSION"
    echo "Installing specific version: ${VERSION}"
fi

# Run the official installer
# - The installer installs to ~/.local/bin by default
# - It handles both amd64 and arm64 architectures
# - It also handles both Linux and macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# The installer adds uv to ~/.local/bin
# Ensure the path is available for verification
export PATH="$HOME/.local/bin:$PATH"

# Also check common installation paths
if [ -f "/root/.local/bin/uv" ]; then
    export PATH="/root/.local/bin:$PATH"
fi

# For devcontainer with vscode user
if [ -f "/home/vscode/.local/bin/uv" ]; then
    export PATH="/home/vscode/.local/bin:$PATH"
fi

# Verify installation
echo ""
echo "Verifying uv installation..."

if command -v uv >/dev/null 2>&1; then
    UV_VERSION=$(uv --version)
    echo "✓ uv installed successfully: ${UV_VERSION}"
    echo ""
    echo "uv is ready to use. Available commands:"
    echo "  - uv pip install <package>  : Install Python packages"
    echo "  - uv venv                   : Create virtual environments"
    echo "  - uv run                    : Run Python scripts"
    echo "  - uv sync                   : Sync project dependencies"
else
    echo "Error: uv installation verification failed." >&2
    echo "Please check the installation manually." >&2
    exit 1
fi
