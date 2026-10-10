#!/usr/bin/env bash
set -euo pipefail
TLS_DIR="$HOME/.inventory/tls"
mkdir -p "$TLS_DIR"
chmod 700 "$TLS_DIR"
command -v openssl >/dev/null || { echo "OpenSSL est requis (sudo apt install openssl)." >&2; exit 1; }

if [[ ! -s "$TLS_DIR/ca.key" || ! -s "$TLS_DIR/ca.crt" ]]; then
  openssl req -x509 -newkey rsa:3072 -nodes -days 3650 \
    -keyout "$TLS_DIR/ca.key" -out "$TLS_DIR/ca.crt" \
    -subj "/CN=Inventory Local Certificate Authority" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign"
  chmod 600 "$TLS_DIR/ca.key"
  chmod 644 "$TLS_DIR/ca.crt"
fi

HOST_IPS="$(hostname -I 2>/dev/null || true)"
SAN="DNS:localhost,IP:127.0.0.1"
index=0
for ip in $HOST_IPS; do
  if [[ "$ip" == *:* ]]; then continue; fi
  index=$((index + 1))
  SAN="$SAN,IP:$ip"
done
openssl req -new -newkey rsa:2048 -nodes \
  -keyout "$TLS_DIR/server.key" -out "$TLS_DIR/server.csr" \
  -subj "/CN=Inventory Local Server"
openssl x509 -req -in "$TLS_DIR/server.csr" \
  -CA "$TLS_DIR/ca.crt" -CAkey "$TLS_DIR/ca.key" -CAcreateserial \
  -out "$TLS_DIR/server.crt" -days 825 -sha256 \
  -extfile <(printf 'subjectAltName=%s\nextendedKeyUsage=serverAuth\n' "$SAN")
rm -f "$TLS_DIR/server.csr"
chmod 600 "$TLS_DIR/server.key"
chmod 644 "$TLS_DIR/server.crt"
