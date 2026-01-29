#!/bin/bash
# =============================================================================
# redis-utils Feature Install Script
#
# Installs redis-utils - Redis operation CLI tools
# Provides: redis-util, redis-rpush, redis-blpop, redis-orch
# =============================================================================

set -e

echo "Installing redis-utils..."

# Define the source path (repository location in devcontainer)
REDIS_UTILS_SOURCE="/workspaces/devcontainer/scripts/redis-utils"

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not available. Please ensure uv feature is installed first."
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not available. Please ensure Python feature is installed first."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python version: ${PYTHON_VERSION}"

# Create a script that will install redis-utils on first container start
# This is necessary because /workspaces is not mounted during feature installation
INSTALL_SCRIPT="/usr/local/bin/redis-utils-setup"

cat > "${INSTALL_SCRIPT}" << 'EOF'
#!/bin/bash
set -e

REDIS_UTILS_SOURCE="/workspaces/devcontainer/scripts/redis-utils"
MARKER_FILE="/usr/local/share/.redis-utils-installed"

# Skip if already installed
if [ -f "${MARKER_FILE}" ]; then
    exit 0
fi

# Check if source directory exists
if [ ! -d "${REDIS_UTILS_SOURCE}" ]; then
    echo "Warning: redis-utils source not found at ${REDIS_UTILS_SOURCE}"
    echo "redis-utils will not be available until the source is mounted."
    exit 0
fi

echo "Installing redis-utils from ${REDIS_UTILS_SOURCE}..."

# Install using uv pip with system flag
if command -v uv &> /dev/null; then
    uv pip install --system "${REDIS_UTILS_SOURCE}"
else
    # Fallback to pip if uv is not available
    pip install "${REDIS_UTILS_SOURCE}"
fi

# Verify installation
echo "Verifying redis-utils installation..."

if command -v redis-util &> /dev/null; then
    echo "✓ redis-util command is available"
    redis-util --help || true
else
    echo "✗ redis-util command not found"
fi

if command -v redis-rpush &> /dev/null; then
    echo "✓ redis-rpush command is available"
else
    echo "✗ redis-rpush command not found"
fi

if command -v redis-blpop &> /dev/null; then
    echo "✓ redis-blpop command is available"
else
    echo "✗ redis-blpop command not found"
fi

if command -v redis-orch &> /dev/null; then
    echo "✓ redis-orch command is available"
else
    echo "✗ redis-orch command not found"
fi

# Create marker file to indicate successful installation
touch "${MARKER_FILE}"
echo "redis-utils installation complete!"
EOF

chmod +x "${INSTALL_SCRIPT}"

# Create a profile.d script to run setup on shell login
PROFILE_SCRIPT="/etc/profile.d/redis-utils.sh"
cat > "${PROFILE_SCRIPT}" << 'EOF'
# Run redis-utils setup if not already installed
if [ -x /usr/local/bin/redis-utils-setup ]; then
    /usr/local/bin/redis-utils-setup 2>/dev/null || true
fi
EOF

chmod +x "${PROFILE_SCRIPT}"

echo "redis-utils feature installed successfully!"
echo "Note: redis-utils will be installed from source on first container start."
echo "The following commands will be available:"
echo "  - redis-util    : Main CLI tool"
echo "  - redis-rpush   : RPUSH command"
echo "  - redis-blpop   : BLPOP command"
echo "  - redis-orch    : Orchestration command"
