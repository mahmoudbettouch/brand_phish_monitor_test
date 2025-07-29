#!/bin/bash

# Certstream Server Setup Script
set -e

echo "Setting up Certstream Server..."

# Create bin directory if it doesn't exist
mkdir -p ./bin
cd ./bin

# Download the certstream server binary
echo "Downloading certstream server binary..."
wget -nv "https://github.com/d-Rickyy-b/certstream-server-go/releases/download/v1.4.0/certstream-server-go_1.4.0_linux_amd64"

# Make the binary executable
chmod u+x ./certstream-server-go_1.4.0_linux_amd64

# Create the config.yaml file
echo "Creating config.yaml..."
cat > ./config.yaml <<EOL
webserver:
  listen_addr: "127.0.0.1"
  listen_port: 8080
  full_url: "/full-stream"
  lite_url: "/"
  domains_only_url: "/domains-only"
  cert_path: ""
  cert_key_path: ""

prometheus:
  enabled: false
  listen_addr: "0.0.0.0"
  listen_port: 8080
  metrics_url: "/metrics"
  expose_system_metrics: false
  real_ip: false
  whitelist:
    - "127.0.0.1/8"
EOL

# Start the certstream server in the background
echo "Starting certstream server from $(pwd)..."
nohup ./certstream-server-go_1.4.0_linux_amd64 > nohup.out 2> nohup.err < /dev/null &

# Store the PID for later reference
SERVER_PID=$!
echo "Certstream server started with PID: $SERVER_PID"

# Wait a moment for the server to start
echo "Waiting for server to initialize..."
sleep 3

# Check if the server is running
if ps -p $SERVER_PID > /dev/null; then
    echo "Server is running successfully!"
    echo "Working directory: $(pwd)"
    echo "Logs: tail -f $(pwd)/nohup.out"
    echo "Errors: tail -f $(pwd)/nohup.err"
    echo "To stop: kill $SERVER_PID"
else
    echo "Server failed to start. Check $(pwd)/nohup.err for errors."
    exit 1
fi

# Test connection (optional - requires certstream python package)
echo ""
echo "To connect with certstream client, run:"
echo "certstream --url ws://127.0.0.1:8080"
echo ""
echo "Or test with curl:"
echo "curl http://127.0.0.1:8080/"