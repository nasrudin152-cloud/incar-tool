#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  VASP Tools Suite — Installer
#  Usage: bash install.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASHRC="$HOME/.bashrc"
ALIAS_CMD="alias incar-gen='bash $SCRIPT_DIR/incar-gen.sh'"

echo "═══════════════════════════════════════════════════"
echo "  VASP Tools Suite — Installer"
echo "═══════════════════════════════════════════════════"
echo

# ── 1. Install Python dependencies ───────────────────────────────────────────
echo "[1/2] Installing Python dependencies..."
if command -v pip3 &>/dev/null; then
    pip3 install --user -r "$SCRIPT_DIR/requirements.txt"
elif command -v pip &>/dev/null; then
    pip install --user -r "$SCRIPT_DIR/requirements.txt"
else
    echo "  [ERROR] pip not found. Please install pip first."
    exit 1
fi
echo "  [OK] Python dependencies installed."
echo

# ── 2. Add alias to .bashrc ──────────────────────────────────────────────────
echo "[2/2] Adding alias to $BASHRC..."
if grep -qF "alias incar-gen=" "$BASHRC" 2>/dev/null; then
    # Update existing alias
    sed -i "s|^alias incar-gen=.*|$ALIAS_CMD|" "$BASHRC"
    echo "  [OK] Alias updated (already existed)."
else
    echo "" >> "$BASHRC"
    echo "# VASP Tools Suite" >> "$BASHRC"
    echo "$ALIAS_CMD" >> "$BASHRC"
    echo "  [OK] Alias added."
fi
echo

# ── Done ──────────────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════"
echo "  Installation complete!"
echo "  Run 'source ~/.bashrc' or open a new terminal,"
echo "  then type 'incar-gen' to launch."
echo "═══════════════════════════════════════════════════"
