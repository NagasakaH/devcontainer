#!/usr/bin/env python3
"""
DevContainer Feature Initializer - Creates a new feature from template

Usage:
    init_feature.py <feature-name> <pattern>

Patterns:
    npm     - Node.js package installation (e.g., claude-code)
    binary  - Pre-built binary download (e.g., lazygit)
    source  - Build from source (e.g., luarocks)
    dotnet  - .NET global tool (e.g., easydotnet)
    setup   - Directory/config setup (e.g., vimcontainer-setup)

Examples:
    init_feature.py my-tool npm
    init_feature.py my-binary binary
    init_feature.py my-builder source
"""

import sys
from pathlib import Path


def to_json(data, indent=2):
    """Simple JSON serializer for basic types."""
    if isinstance(data, dict):
        items = []
        for k, v in data.items():
            items.append(f'{" " * indent}"{k}": {to_json(v, indent)}')
        inner = ",\n".join(items)
        return "{\n" + inner + "\n}"
    elif isinstance(data, list):
        if not data:
            return "[]"
        items = [f'    "{item}"' for item in data]
        return "[\n" + ",\n".join(items) + "\n  ]"
    elif isinstance(data, str):
        return f'"{data}"'
    elif isinstance(data, bool):
        return "true" if data else "false"
    elif isinstance(data, (int, float)):
        return str(data)
    elif data is None:
        return "null"
    else:
        return f'"{str(data)}"'


def format_json(data):
    """Format dict as pretty-printed JSON."""
    lines = []
    lines.append("{")
    
    items = list(data.items())
    for i, (key, value) in enumerate(items):
        comma = "," if i < len(items) - 1 else ""
        
        if isinstance(value, dict):
            lines.append(f'  "{key}": {{')
            sub_items = list(value.items())
            for j, (k, v) in enumerate(sub_items):
                sub_comma = "," if j < len(sub_items) - 1 else ""
                if isinstance(v, dict):
                    lines.append(f'    "{k}": {{')
                    inner_items = list(v.items())
                    for m, (ik, iv) in enumerate(inner_items):
                        inner_comma = "," if m < len(inner_items) - 1 else ""
                        lines.append(f'      "{ik}": "{iv}"{inner_comma}')
                    lines.append(f'    }}{sub_comma}')
                else:
                    lines.append(f'    "{k}": "{v}"{sub_comma}')
            lines.append(f'  }}{comma}')
        elif isinstance(value, list):
            if not value:
                lines.append(f'  "{key}": []{comma}')
            else:
                lines.append(f'  "{key}": [')
                for k, item in enumerate(value):
                    item_comma = "," if k < len(value) - 1 else ""
                    lines.append(f'    "{item}"{item_comma}')
                lines.append(f'  ]{comma}')
        else:
            lines.append(f'  "{key}": "{value}"{comma}')
    
    lines.append("}")
    return "\n".join(lines)


# Pattern-specific defaults
INSTALL_TEMPLATES = {
    "npm": '''#!/bin/bash
set -e

echo "Installing {feature_title}..."

# Check npm availability
if ! command -v npm &> /dev/null; then
    echo "Error: npm is not available. Please ensure Node.js feature is installed first."
    exit 1
fi

# Install package globally via npm
npm install -g {npm_package}

echo "{feature_title} installed successfully"

# Verify installation
if command -v {verify_command} &> /dev/null; then
    {verify_command} --version
else
    echo "Warning: Installation verification failed"
fi
''',

    "binary": '''#!/bin/bash
set -e

VERSION="${{VERSION:-{default_version}}}"

echo "Installing {feature_title} v${{VERSION}}..."

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
DOWNLOAD_URL="{download_url}"

echo "Downloading from: ${{DOWNLOAD_URL}}"
curl -L "${{DOWNLOAD_URL}}" -o {feature_name}.tar.gz

# Extract and install
tar -xzf {feature_name}.tar.gz
chmod +x {binary_name}
mv {binary_name} /usr/local/bin/{binary_name}

# Cleanup
rm -f {feature_name}.tar.gz
apt-get clean 2>/dev/null || true
rm -rf /var/lib/apt/lists/* 2>/dev/null || true

echo "{feature_title} v${{VERSION}} installed successfully!"
{verify_command} --version
''',

    "source": '''#!/bin/bash
set -e

VERSION="${{VERSION:-{default_version}}}"

echo "Installing {feature_title} v${{VERSION}}..."

# Install build dependencies
apt-get update
apt-get install -y build-essential wget

# Download source
TEMP_DIR="/tmp/{feature_name}-install"
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

DOWNLOAD_URL="{download_url}"
echo "Downloading from: ${{DOWNLOAD_URL}}"

wget -q "$DOWNLOAD_URL" -O source.tar.gz

# Verify download
if ! od -An -tx1 -N2 source.tar.gz | grep -q "1f 8b"; then
    echo "Error: Downloaded file is not a valid gzip archive"
    exit 1
fi

tar -xzf source.tar.gz
cd {source_dir}

# Build and install
./configure --prefix=/usr/local
make
make install

# Cleanup
cd /
rm -rf "$TEMP_DIR"

echo "{feature_title} v${{VERSION}} installed successfully!"
{verify_command} --version
''',

    "dotnet": '''#!/bin/bash
set -e

VERSION="${{VERSION:-latest}}"

echo "Installing {feature_title}..."

# Check dotnet availability
if ! command -v dotnet &> /dev/null; then
    echo "Error: dotnet CLI is required but not found. Please install .NET SDK first."
    exit 1
fi

# Determine target user
INSTALL_USER="${{_REMOTE_USER:-${{USERNAME:-vscode}}}}"
USER_HOME=$(getent passwd "${{INSTALL_USER}}" | cut -d: -f6)

echo "Installing {feature_title} for user: ${{INSTALL_USER}}"

# Install as global tool
if [ "$VERSION" = "latest" ]; then
    su - "${{INSTALL_USER}}" -c "dotnet tool install -g {dotnet_package}"
else
    su - "${{INSTALL_USER}}" -c "dotnet tool install -g {dotnet_package} --version ${{VERSION}}"
fi

# Add dotnet tools to PATH
cat << 'EOF' > /etc/profile.d/{feature_name}.sh
export PATH="$PATH:$HOME/.dotnet/tools"
EOF
chmod +x /etc/profile.d/{feature_name}.sh

echo "{feature_title} installed successfully for ${{INSTALL_USER}}!"
echo "Tool location: ${{USER_HOME}}/.dotnet/tools"
''',

    "setup": '''#!/bin/bash
set -e

USERNAME="${{USERNAME:-vscode}}"

echo "Setting up {feature_title} for user: ${{USERNAME}}..."

# Create necessary directories
TARGET_DIR="/home/${{USERNAME}}/{target_path}"
mkdir -p "${{TARGET_DIR}}"

echo "Created directory: ${{TARGET_DIR}}"

# Set ownership
if id "${{USERNAME}}" &>/dev/null; then
    chown -R "${{USERNAME}}:${{USERNAME}}" "${{TARGET_DIR}}"
    echo "Ownership set to ${{USERNAME}}:${{USERNAME}}"
else
    echo "Warning: User ${{USERNAME}} does not exist. Skipping ownership change."
fi

echo "{feature_title} setup completed successfully"
'''
}

# Pattern-specific defaults
PATTERN_DEFAULTS = {
    "npm": {
        "description": "Installs {feature_title} via npm",
        "default_version": "latest",
        "installsAfter": ["ghcr.io/devcontainers/features/node"],
        "npm_package": "{feature_name}",
        "verify_command": "{feature_name}"
    },
    "binary": {
        "description": "Installs {feature_title} pre-built binary",
        "default_version": "1.0.0",
        "installsAfter": [],
        "download_url": "https://github.com/OWNER/REPO/releases/download/v${{VERSION}}/{feature_name}_${{VERSION}}_Linux_${{TARGET_ARCH}}.tar.gz",
        "binary_name": "{feature_name}",
        "verify_command": "{feature_name}"
    },
    "source": {
        "description": "Installs {feature_title} from source",
        "default_version": "1.0.0",
        "installsAfter": [],
        "download_url": "https://example.com/releases/{feature_name}-${{VERSION}}.tar.gz",
        "source_dir": "{feature_name}-${{VERSION}}",
        "verify_command": "{feature_name}"
    },
    "dotnet": {
        "description": "Installs {feature_title} as a .NET global tool",
        "default_version": "latest",
        "installsAfter": ["ghcr.io/devcontainers/features/dotnet"],
        "dotnet_package": "{feature_name}"
    },
    "setup": {
        "description": "Sets up {feature_title} directory and configuration",
        "default_version": "1.0.0",
        "installsAfter": [],
        "target_path": ".local/share/{feature_name}"
    }
}


def title_case(name: str) -> str:
    """Convert kebab-case to Title Case."""
    return ' '.join(word.capitalize() for word in name.split('-'))


def init_feature(feature_name: str, pattern: str):
    """Initialize a new DevContainer feature."""
    
    if pattern not in INSTALL_TEMPLATES:
        print(f"❌ Unknown pattern: {pattern}")
        print(f"   Available patterns: {', '.join(INSTALL_TEMPLATES.keys())}")
        return False
    
    # Determine paths - navigate from skills/feature-creator/scripts to repository root
    script_dir = Path(__file__).parent.resolve()
    repo_root = script_dir.parent.parent.parent  # skills/feature-creator/scripts -> repo root
    features_dir = repo_root / "features"
    feature_dir = features_dir / feature_name
    
    # Check if already exists
    if feature_dir.exists():
        print(f"❌ Feature directory already exists: {feature_dir}")
        return False
    
    # Create feature directory
    feature_dir.mkdir(parents=True)
    print(f"✅ Created directory: {feature_dir}")
    
    # Prepare template values
    feature_title = title_case(feature_name)
    defaults = PATTERN_DEFAULTS[pattern].copy()
    
    # Substitute feature_name in defaults
    for key, value in defaults.items():
        if isinstance(value, str):
            defaults[key] = value.format(feature_name=feature_name, feature_title=feature_title)
    
    # Create devcontainer-feature.json using json module
    json_data = {
        "id": feature_name,
        "version": "1.0.0",
        "name": feature_title,
        "description": defaults["description"],
        "options": {
            "version": {
                "type": "string",
                "default": defaults["default_version"],
                "description": "Version to install"
            }
        }
    }
    
    # Add installsAfter if dependencies exist
    if defaults.get("installsAfter"):
        json_data["installsAfter"] = defaults["installsAfter"]
    
    json_path = feature_dir / "devcontainer-feature.json"
    json_path.write_text(format_json(json_data) + "\n")
    print(f"✅ Created devcontainer-feature.json")
    
    # Create install.sh
    install_template = INSTALL_TEMPLATES[pattern]
    install_content = install_template.format(
        feature_name=feature_name,
        feature_title=feature_title,
        **{k: v for k, v in defaults.items() if k not in ["description", "installsAfter"]}
    )
    
    install_path = feature_dir / "install.sh"
    install_path.write_text(install_content)
    install_path.chmod(0o755)
    print(f"✅ Created install.sh ({pattern} pattern)")
    
    # Print next steps
    print(f"\n✅ Feature '{feature_name}' initialized at {feature_dir}")
    print("\nNext steps:")
    print("1. Edit devcontainer-feature.json:")
    print("   - Update name and description")
    print("   - Adjust options if needed")
    if pattern == "binary":
        print("2. Edit install.sh:")
        print("   - Update DOWNLOAD_URL with actual GitHub release URL")
        print("   - Verify binary name and extraction path")
    elif pattern == "source":
        print("2. Edit install.sh:")
        print("   - Update DOWNLOAD_URL")
        print("   - Adjust build commands (./configure, make, etc.)")
    elif pattern == "npm":
        print("2. Edit install.sh:")
        print("   - Update npm package name if different from feature name")
        print("   - Update verify command")
    elif pattern == "dotnet":
        print("2. Edit install.sh:")
        print("   - Update dotnet package name")
    elif pattern == "setup":
        print("2. Edit install.sh:")
        print("   - Update target directory path")
        print("   - Add any configuration steps")
    print("3. Test the feature locally")
    
    return True


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    
    feature_name = sys.argv[1]
    pattern = sys.argv[2]
    
    # Validate feature name
    if not feature_name.replace('-', '').replace('_', '').isalnum():
        print(f"❌ Invalid feature name: {feature_name}")
        print("   Use lowercase letters, numbers, and hyphens only")
        sys.exit(1)
    
    print(f"🚀 Initializing feature: {feature_name}")
    print(f"   Pattern: {pattern}")
    print()
    
    if init_feature(feature_name, pattern):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
