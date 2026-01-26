#!/bin/bash
set -e

# =============================================================================
# MSSQL MCP Server Installation Script
# =============================================================================
# This script installs the MSSQL MCP (Model Context Protocol) Server
# for AI-powered SQL Server interaction.
#
# Requirements:
#   - .NET 8.0 SDK or later
#
# Options (passed via environment variables):
#   - CONNECTIONSTRING: Default SQL Server connection string
#   - INSTALLPATH: Installation path for binaries (default: /usr/local/mssql-mcp)
# =============================================================================

INSTALL_PATH="${INSTALLPATH:-/usr/local/mssql-mcp}"
CONNECTION_STRING="${CONNECTIONSTRING:-}"

echo "=========================================="
echo "Installing MSSQL MCP Server"
echo "=========================================="
echo "Install path: ${INSTALL_PATH}"

# -----------------------------------------------------------------------------
# Check Prerequisites
# -----------------------------------------------------------------------------

echo ""
echo "[1/5] Checking prerequisites..."

# Check if dotnet is available
if ! command -v dotnet &> /dev/null; then
    echo "Error: .NET SDK is required but not found."
    echo "Please ensure the dotnet feature is installed first:"
    echo '  "ghcr.io/devcontainers/features/dotnet:2": {}'
    exit 1
fi

# Check .NET version
DOTNET_VERSION=$(dotnet --version)
echo "Found .NET SDK version: ${DOTNET_VERSION}"

# Verify .NET 8.0 or higher
MAJOR_VERSION=$(echo "$DOTNET_VERSION" | cut -d. -f1)
if [ "$MAJOR_VERSION" -lt 8 ]; then
    echo "Error: .NET 8.0 or higher is required. Found version: ${DOTNET_VERSION}"
    exit 1
fi

# -----------------------------------------------------------------------------
# Clone or Copy MssqlMcp Source Code
# -----------------------------------------------------------------------------

echo ""
echo "[2/5] Setting up MssqlMcp source code..."

TEMP_DIR=$(mktemp -d)
MSSQL_MCP_SRC="${TEMP_DIR}/MssqlMcp"

# Check if source exists locally (for development/testing)
if [ -d "/workspaces/devcontainer/SQL-AI-samples/MssqlMcp/dotnet/MssqlMcp" ]; then
    echo "Using local source from /workspaces/devcontainer/SQL-AI-samples/MssqlMcp/dotnet/MssqlMcp"
    cp -r /workspaces/devcontainer/SQL-AI-samples/MssqlMcp/dotnet/MssqlMcp "${MSSQL_MCP_SRC}"
else
    echo "Cloning MssqlMcp from GitHub..."
    # Clone only the specific directory needed
    cd "${TEMP_DIR}"
    git clone --depth 1 --filter=blob:none --sparse https://github.com/Azure-Samples/SQL-AI-samples.git
    cd SQL-AI-samples
    git sparse-checkout set MssqlMcp/dotnet/MssqlMcp
    mv MssqlMcp/dotnet/MssqlMcp "${MSSQL_MCP_SRC}"
    cd "${TEMP_DIR}"
    rm -rf SQL-AI-samples
fi

# -----------------------------------------------------------------------------
# Build MssqlMcp
# -----------------------------------------------------------------------------

echo ""
echo "[3/5] Building MssqlMcp..."

cd "${MSSQL_MCP_SRC}"

# Restore dependencies
echo "Restoring dependencies..."
dotnet restore

# Build in Release mode
echo "Building in Release mode..."
dotnet build --configuration Release --no-restore

# Publish as self-contained single file (optional, for portability)
echo "Publishing as optimized binary..."
dotnet publish --configuration Release \
    --output "${TEMP_DIR}/publish" \
    --no-self-contained \
    -p:PublishSingleFile=false

# -----------------------------------------------------------------------------
# Install MssqlMcp
# -----------------------------------------------------------------------------

echo ""
echo "[4/5] Installing MssqlMcp to ${INSTALL_PATH}..."

# Create installation directory
mkdir -p "${INSTALL_PATH}"

# Copy published files
cp -r "${TEMP_DIR}/publish/"* "${INSTALL_PATH}/"

# Create wrapper script for easy execution
cat > "${INSTALL_PATH}/mssql-mcp" << WRAPPER_EOF
#!/bin/bash
# MSSQL MCP Server Wrapper Script

# Run the MssqlMcp server
exec dotnet "${INSTALL_PATH}/MssqlMcp.dll" "\$@"
WRAPPER_EOF

chmod +x "${INSTALL_PATH}/mssql-mcp"

# Create symlink in /usr/local/bin for PATH accessibility
ln -sf "${INSTALL_PATH}/mssql-mcp" /usr/local/bin/mssql-mcp

# -----------------------------------------------------------------------------
# Configure Environment
# -----------------------------------------------------------------------------

echo ""
echo "[5/5] Configuring environment..."

# Set up connection string if provided
if [ -n "${CONNECTION_STRING}" ]; then
    echo "Setting up default connection string..."
    cat > /etc/profile.d/mssql-mcp.sh << EOF
# MSSQL MCP Server Configuration
export MSSQL_CONNECTION_STRING="${CONNECTION_STRING}"
EOF
    chmod +x /etc/profile.d/mssql-mcp.sh
else
    # Create profile script without connection string
    cat > /etc/profile.d/mssql-mcp.sh << 'EOF'
# MSSQL MCP Server Configuration
# Set MSSQL_CONNECTION_STRING environment variable to configure the connection
# Example: export MSSQL_CONNECTION_STRING="Server=localhost;Database=mydb;User Id=sa;Password=xxx;TrustServerCertificate=true"
EOF
    chmod +x /etc/profile.d/mssql-mcp.sh
fi

# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------

echo ""
echo "Cleaning up temporary files..."
rm -rf "${TEMP_DIR}"

# -----------------------------------------------------------------------------
# Verify Installation
# -----------------------------------------------------------------------------

echo ""
echo "=========================================="
echo "Verifying installation..."
echo "=========================================="

if [ -f "${INSTALL_PATH}/MssqlMcp.dll" ]; then
    echo "✓ MssqlMcp.dll found at ${INSTALL_PATH}"
else
    echo "✗ Error: MssqlMcp.dll not found"
    exit 1
fi

if [ -x "${INSTALL_PATH}/mssql-mcp" ]; then
    echo "✓ mssql-mcp wrapper script is executable"
else
    echo "✗ Error: mssql-mcp wrapper script not found or not executable"
    exit 1
fi

if command -v mssql-mcp &> /dev/null; then
    echo "✓ mssql-mcp is available in PATH"
else
    echo "✓ mssql-mcp installed (symlink created at /usr/local/bin/mssql-mcp)"
fi

# -----------------------------------------------------------------------------
# Print Usage Information
# -----------------------------------------------------------------------------

echo ""
echo "=========================================="
echo "MSSQL MCP Server installed successfully!"
echo "=========================================="
echo ""
echo "Installation location: ${INSTALL_PATH}"
echo ""
echo "Usage:"
echo "  1. Set the connection string environment variable:"
echo "     export MSSQL_CONNECTION_STRING=\"Server=localhost;Database=mydb;User Id=sa;Password=xxx;TrustServerCertificate=true\""
echo ""
echo "  2. Run the MCP server:"
echo "     mssql-mcp"
echo ""
echo "  3. Configure in Claude Desktop or other MCP clients:"
echo "     {"
echo "       \"mcpServers\": {"
echo "         \"mssql\": {"
echo "           \"command\": \"mssql-mcp\","
echo "           \"env\": {"
echo "             \"MSSQL_CONNECTION_STRING\": \"your-connection-string\""
echo "           }"
echo "         }"
echo "       }"
echo "     }"
echo ""
echo "For more information, visit:"
echo "  https://github.com/Azure-Samples/SQL-AI-samples/tree/main/MssqlMcp"
echo "=========================================="
