# DevContainer Feature install.sh Patterns

Complete templates and best practices for each installation pattern.

## Common Header

Every install.sh must start with:

```bash
#!/bin/bash
set -e
```

## Pattern 1: npm Package

**Use for**: Node.js packages from npm registry

**Examples in repo**: claude-code, editorconfig-prettier

```bash
#!/bin/bash
set -e

echo "Installing <Package Name>..."

# Check npm availability
if ! command -v npm &> /dev/null; then
    echo "Error: npm is not available. Please ensure Node.js feature is installed first."
    exit 1
fi

# Install package globally via npm
npm install -g <package-name>

echo "<Package Name> installed successfully"

# Verify installation
if command -v <command-name> &> /dev/null; then
    <command-name> --version
    echo "<Package Name> is ready to use"
else
    echo "Warning: <Package Name> installation may have failed"
fi
```

**devcontainer-feature.json requirements**:
```json
{
  "installsAfter": ["ghcr.io/devcontainers/features/node"]
}
```

---

## Pattern 2: Binary Download

**Use for**: Pre-built binaries from GitHub releases or other sources

**Examples in repo**: lazygit, copilot-cli, tree-sitter, yazi

```bash
#!/bin/bash
set -e

VERSION="${VERSION:-1.0.0}"

echo "Installing <Tool Name> v${VERSION}..."

# Detect architecture
ARCH=$(dpkg --print-architecture)
case "$ARCH" in
    amd64) TARGET_ARCH="x86_64" ;;
    arm64) TARGET_ARCH="arm64" ;;
    *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

# Install dependencies if needed
if ! command -v curl &> /dev/null; then
    apt-get update && apt-get install -y --no-install-recommends curl ca-certificates
fi

# Download pre-built binary
cd /tmp
DOWNLOAD_URL="https://github.com/OWNER/REPO/releases/download/v${VERSION}/tool_${VERSION}_Linux_${TARGET_ARCH}.tar.gz"

echo "Downloading from: ${DOWNLOAD_URL}"
curl -L "${DOWNLOAD_URL}" -o tool.tar.gz

# Extract and install
tar -xzf tool.tar.gz tool
chmod +x tool
mv tool /usr/local/bin/tool

# Cleanup
rm -f tool.tar.gz
apt-get clean 2>/dev/null || true
rm -rf /var/lib/apt/lists/* 2>/dev/null || true

echo "<Tool Name> v${VERSION} installed successfully!"
tool --version
```

**Architecture mapping variations**:

Some projects use different naming:
- `x86_64` / `arm64` (most common)
- `amd64` / `arm64`
- `Linux_x86_64` / `Linux_arm64`
- `linux-amd64` / `linux-arm64`

Check the actual release assets to determine correct naming.

---

## Pattern 3: Source Build

**Use for**: Tools that need compilation from source

**Examples in repo**: luarocks

```bash
#!/bin/bash
set -e

VERSION="${VERSION:-latest}"

echo "Installing <Tool Name>..."

# Install build dependencies
apt-get update
apt-get install -y build-essential wget

# Determine version
if [ "$VERSION" = "latest" ]; then
    ACTUAL_VERSION="1.0.0"  # Set default or fetch latest
else
    ACTUAL_VERSION="$VERSION"
fi

# Download source
TEMP_DIR="/tmp/tool-install"
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

DOWNLOAD_URL="https://example.com/releases/tool-${ACTUAL_VERSION}.tar.gz"
echo "Downloading from: ${DOWNLOAD_URL}"

wget -q "$DOWNLOAD_URL" -o source.tar.gz

# Verify download (gzip magic number: 1f 8b)
if ! od -An -tx1 -N2 source.tar.gz | grep -q "1f 8b"; then
    echo "Error: Downloaded file is not a valid gzip archive"
    exit 1
fi

tar -xzf source.tar.gz
cd "tool-${ACTUAL_VERSION}"

# Build and install
./configure --prefix=/usr/local
make
make install

# Cleanup
cd /
rm -rf "$TEMP_DIR"

echo "<Tool Name> ${ACTUAL_VERSION} installed successfully!"
tool --version
```

---

## Pattern 4: dotnet Tool

**Use for**: .NET global tools

**Examples in repo**: easydotnet

```bash
#!/bin/bash
set -e

VERSION="${VERSION:-latest}"

echo "Installing <Tool Name>..."

# Check dotnet availability
if ! command -v dotnet &> /dev/null; then
    echo "Error: dotnet CLI is required but not found. Please install .NET SDK first."
    exit 1
fi

# Determine target user (DevContainer sets _REMOTE_USER)
INSTALL_USER="${_REMOTE_USER:-${USERNAME:-vscode}}"
USER_HOME=$(getent passwd "${INSTALL_USER}" | cut -d: -f6)

echo "Installing <Tool Name> for user: ${INSTALL_USER} (home: ${USER_HOME})"

# Install as global tool
if [ "$VERSION" = "latest" ]; then
    su - "${INSTALL_USER}" -c "dotnet tool install -g <package-name>"
else
    su - "${INSTALL_USER}" -c "dotnet tool install -g <package-name> --version ${VERSION}"
fi

# Add dotnet tools to PATH for all users
cat << 'EOF' > /etc/profile.d/dotnet-tools.sh
export PATH="$PATH:$HOME/.dotnet/tools"
EOF
chmod +x /etc/profile.d/dotnet-tools.sh

echo "<Tool Name> installed successfully for ${INSTALL_USER}!"
echo "Tool location: ${USER_HOME}/.dotnet/tools"
```

**devcontainer-feature.json requirements**:
```json
{
  "installsAfter": ["ghcr.io/devcontainers/features/dotnet"]
}
```

---

## Pattern 5: Directory Setup

**Use for**: Creating directories, setting permissions, basic configuration

**Examples in repo**: vimcontainer-setup

```bash
#!/bin/bash
set -e

USERNAME="${USERNAME:-vscode}"

echo "Setting up <Feature Name> for user: ${USERNAME}..."

# Create necessary directories
TARGET_DIR="/home/${USERNAME}/.local/share/tool"
mkdir -p "${TARGET_DIR}"

echo "Created directory: ${TARGET_DIR}"

# Set ownership
if id "${USERNAME}" &>/dev/null; then
    chown -R "${USERNAME}:${USERNAME}" "/home/${USERNAME}/.local"
    echo "Ownership set to ${USERNAME}:${USERNAME}"
else
    echo "Warning: User ${USERNAME} does not exist. Skipping ownership change."
fi

# Optional: Create configuration file
cat << 'EOF' > "${TARGET_DIR}/config.json"
{
  "setting": "value"
}
EOF

echo "<Feature Name> setup completed successfully"
```

---

## Best Practices

### Error Messages

Always provide clear, actionable error messages:

```bash
# Good
echo "Error: npm is not available. Please ensure Node.js feature is installed first."

# Bad
echo "Error"
```

### Cleanup

Always clean up temporary files and apt cache:

```bash
# Cleanup temp files
rm -f /tmp/download.tar.gz

# Cleanup apt cache
apt-get clean 2>/dev/null || true
rm -rf /var/lib/apt/lists/* 2>/dev/null || true
```

### Verification

Verify installation succeeded:

```bash
if command -v tool &> /dev/null; then
    tool --version
    echo "Tool is ready to use"
else
    echo "Warning: Tool installation may have failed"
fi
```

### User Context

When installing user-specific tools:

```bash
# Get the remote user (set by DevContainer)
INSTALL_USER="${_REMOTE_USER:-${USERNAME:-vscode}}"
USER_HOME=$(getent passwd "${INSTALL_USER}" | cut -d: -f6)

# Install for specific user
su - "${INSTALL_USER}" -c "command to run as user"
```

### Version Handling

Support version options from devcontainer-feature.json:

```bash
# Use VERSION env var with fallback
VERSION="${VERSION:-1.0.0}"

# Handle "latest" specially if needed
if [ "$VERSION" = "latest" ]; then
    VERSION="1.0.0"  # or fetch actual latest
fi
```

### Progress Output

Provide clear progress indication:

```bash
echo "Step 1: Downloading..."
# download code

echo "Step 2: Installing..."
# install code

echo "Installation complete!"
```
