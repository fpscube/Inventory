#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
INSTALL_DIR="$HOME/.local/share/inventory"
APP_DIR="$INSTALL_DIR/app"
VENV_DIR="$INSTALL_DIR/venv"
UNIT_DIR="$HOME/.config/systemd/user"

if [[ ! -r /etc/os-release ]]; then
  echo "Impossible de déterminer la distribution Linux." >&2; exit 1
fi
# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID:-}" != ubuntu ]]; then
  echo "Cette installation cible Ubuntu. Système détecté : ${PRETTY_NAME:-inconnu}." >&2; exit 1
fi
if ! command -v python3 >/dev/null || ! command -v systemctl >/dev/null || ! command -v openssl >/dev/null; then
  echo "Prérequis manquants : python3, systemd et openssl sont nécessaires." >&2; exit 1
fi
if ! python3 -m venv --help >/dev/null 2>&1; then
  echo "Le module venv manque. Installez-le avec : sudo apt install python3-venv" >&2; exit 1
fi

mkdir -p "$APP_DIR" "$UNIT_DIR" "$HOME/.inventory"
( cd "$PROJECT_DIR" && tar --exclude='./.git' --exclude='./.venv' --exclude='__pycache__' -cf - . ) | ( cd "$APP_DIR" && tar -xf - )
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"
"$APP_DIR/scripts/setup-tls.sh"
install -m 0644 "$APP_DIR/systemd/inventory.service" "$UNIT_DIR/inventory.service"
systemctl --user daemon-reload
systemctl --user enable inventory.service
if systemctl --user is-active --quiet inventory.service; then
  systemctl --user restart inventory.service
else
  systemctl --user start inventory.service
fi

if command -v loginctl >/dev/null && loginctl enable-linger "$USER" 2>/dev/null; then
  echo "Démarrage avant ouverture de session activé (linger)."
else
  echo "Le service fonctionne pour votre session, mais l’activation de linger demande sudo."
  echo "Lancez : sudo loginctl enable-linger $USER"
fi

echo
echo "Inventaire installé et démarré."
echo "Accès standard : http://IP_DU_PC:18765"
echo "Accès dictée HTTPS : https://IP_DU_PC:18766"
echo "Données : $HOME/.inventory"
echo "État : systemctl --user status inventory.service"
echo "Journaux : journalctl --user -u inventory.service -f"
echo "Adresse(s) réseau :"
if command -v hostname >/dev/null; then
  while IFS= read -r ip; do
    [[ -n "$ip" ]] || continue
    echo "  Page : http://$ip:18765"
    echo "  Dictée HTTPS : https://$ip:18766"
    echo "  Certificat pour dictée : http://$ip:18767/ca.crt"
  done < <(hostname -I | tr ' ' '\n')
fi
