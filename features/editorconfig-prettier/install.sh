#!/bin/bash
set -e

VERSION="${VERSION:-latest}"
INSTALL_HELPER_SCRIPTS="${INSTALLHELPERSCRIPTS:-true}"

echo "Installing Prettier for EditorConfig support..."

# Install Prettier globally via npm
if command -v npm &> /dev/null; then
    if [ "$VERSION" = "latest" ]; then
        npm install -g prettier
    else
        npm install -g "prettier@${VERSION}"
    fi
    echo "Prettier installed successfully"
else
    echo "Error: npm is not available. Please ensure Node.js feature is installed first."
    exit 1
fi

# Verify installation
if command -v prettier &> /dev/null; then
    prettier --version
    echo "Prettier is ready to use with EditorConfig support"
else
    echo "Warning: Prettier installation may have failed"
    exit 1
fi

# Install helper scripts if enabled
if [ "$INSTALL_HELPER_SCRIPTS" = "true" ]; then
    echo "Installing helper scripts..."

    # Create editorconfig-check script
    cat > /usr/local/bin/editorconfig-check << 'EOF'
#!/bin/bash
# editorconfig-check: Validate files against EditorConfig rules using Prettier
# Usage: editorconfig-check [pattern]
# Default: Check all files in current directory

set -e

PATTERN="${1:-.}"

echo "Checking EditorConfig compliance with Prettier..."
prettier --check "$PATTERN"
EOF
    chmod +x /usr/local/bin/editorconfig-check

    # Create editorconfig-format script
    cat > /usr/local/bin/editorconfig-format << 'EOF'
#!/bin/bash
# editorconfig-format: Format files according to EditorConfig rules using Prettier
# Usage: editorconfig-format [pattern]
# Default: Format all files in current directory

set -e

PATTERN="${1:-.}"

echo "Formatting files with Prettier (EditorConfig)..."
prettier --write "$PATTERN"
EOF
    chmod +x /usr/local/bin/editorconfig-format

    echo "Helper scripts installed:"
    echo "  - editorconfig-check: Validate files (CI mode)"
    echo "  - editorconfig-format: Format files"
fi

echo "EditorConfig Prettier setup complete!"
