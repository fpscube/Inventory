#!/usr/bin/env bash
set -euo pipefail
UNIT="$HOME/.config/systemd/user/inventory.service"
systemctl --user disable --now inventory.service 2>/dev/null || true
rm -f "$UNIT"
systemctl --user daemon-reload
rm -rf "$HOME/.local/share/inventory"
echo "Application et service supprimés. Les données de ~/.inventory/ ont été conservées."
