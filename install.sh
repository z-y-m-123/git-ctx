#!/usr/bin/env bash
# install.sh — one-click install for git-ctx
# Usage: curl -fsSL <url>/install.sh | bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Determine install directory
if [ -w /usr/local/bin ]; then
    INSTALL_DIR="/usr/local/bin"
elif [ -w "${HOME}/.local/bin" ]; then
    INSTALL_DIR="${HOME}/.local/bin"
else
    INSTALL_DIR="${HOME}/.local/bin"
    mkdir -p "$INSTALL_DIR"
fi

echo "Installing git-ctx to $INSTALL_DIR ..."

# Copy the script and make it executable
cp "$SCRIPT_DIR/git_ctx.py" "$INSTALL_DIR/git-ctx"
chmod +x "$INSTALL_DIR/git-ctx"

# Check if install dir is in PATH
if ! echo "$PATH" | tr ':' '\n' | grep -qxF "$INSTALL_DIR"; then
    echo ""
    echo "⚠  $INSTALL_DIR is not in your PATH."
    echo "   Add this line to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
    echo ""
    echo "       export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi

echo "Done! Run 'git-ctx --help' to get started."
