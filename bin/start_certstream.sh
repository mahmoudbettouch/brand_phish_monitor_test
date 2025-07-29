#!/bin/bash

# Set working directory
DIR="$(cd "$(dirname "$0")" && pwd)"
BINARY="$DIR/certstream-server-go"
CONFIG="$DIR/config.yaml"
DOWNLOAD_URL="https://github.com/d-Rickyy-b/certstream-server-go/releases/download/v1.4.0/certstream-server-go_1.4.0_linux_amd64"

# Check if binary exists
if [ ! -f "$BINARY" ]; then
    echo "[INFO] CertStream binary not found. Downloading..."
    wget -nv "$DOWNLOAD_URL" -O "$BINARY"
    chmod +x "$BINARY"
    echo "[INFO] Download complete."
fi

# Start CertStream server
nohup "$BINARY" > "$DIR/nohup.out" 2> "$DIR/nohup.err" < /dev/null &
echo "[INFO] CertStream server started at ws://127.0.0.1:8080"
