#!/usr/bin/env bash
# install.sh - one-click install for git-ctx
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/z-y-m-123/git-ctx/main/install.sh | bash
#   ./install.sh
set -euo pipefail

REPO_RAW_URL="${GIT_CTX_REPO_RAW_URL:-https://raw.githubusercontent.com/z-y-m-123/git-ctx}"
REF="${GIT_CTX_REF:-main}"
SOURCE_URL="${GIT_CTX_SOURCE_URL:-${REPO_RAW_URL}/${REF}/git_ctx.py}"

find_python() {
    if command -v python3 >/dev/null 2>&1; then
        command -v python3
    elif command -v python >/dev/null 2>&1; then
        command -v python
    else
        return 1
    fi
}

choose_install_dir() {
    if [ -n "${GIT_CTX_INSTALL_DIR:-}" ]; then
        printf '%s\n' "$GIT_CTX_INSTALL_DIR"
    elif [ -d /usr/local/bin ] && [ -w /usr/local/bin ]; then
        printf '%s\n' "/usr/local/bin"
    else
        printf '%s\n' "${HOME}/.local/bin"
    fi
}

download_file() {
    url="$1"
    dest="$2"
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$url" -o "$dest"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO "$dest" "$url"
    else
        echo "Error: curl or wget is required for remote installation." >&2
        exit 1
    fi
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
LOCAL_SOURCE=""
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/git_ctx.py" ]; then
    LOCAL_SOURCE="$SCRIPT_DIR/git_ctx.py"
fi

PYTHON_BIN="$(find_python)" || {
    echo "Error: Python 3.8+ is required but was not found in PATH." >&2
    exit 1
}

INSTALL_DIR="$(choose_install_dir)"
mkdir -p "$INSTALL_DIR"
TARGET="$INSTALL_DIR/git-ctx"

echo "Installing git-ctx to $TARGET ..."

TMP_FILE=""
cleanup() {
    if [ -n "$TMP_FILE" ] && [ -f "$TMP_FILE" ]; then
        rm -f "$TMP_FILE"
    fi
}
trap cleanup EXIT

if [ -n "$LOCAL_SOURCE" ]; then
    cp "$LOCAL_SOURCE" "$TARGET"
else
    TMP_FILE="$(mktemp)"
    download_file "$SOURCE_URL" "$TMP_FILE"
    cp "$TMP_FILE" "$TARGET"
fi

chmod +x "$TARGET"

if ! "$PYTHON_BIN" "$TARGET" --help >/dev/null 2>&1; then
    echo "Warning: installed file could not be executed with $PYTHON_BIN." >&2
fi

if ! printf '%s' "$PATH" | tr ':' '\n' | grep -qxF "$INSTALL_DIR"; then
    echo ""
    echo "Warning: $INSTALL_DIR is not in your PATH."
    echo "Add this line to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
    echo ""
    echo "    export PATH=\"$INSTALL_DIR:\$PATH\""
    echo ""
fi

echo "Done! Run 'git-ctx --help' to get started."
