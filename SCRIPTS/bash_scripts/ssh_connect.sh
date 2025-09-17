#!/bin/bash

# Direct SSH connection script that handles encrypted keys
# Usage: ./ssh_connect.sh <host> <port> [command]
# Example: ./ssh_connect.sh ssh8.vast.ai 24593

if [ $# -lt 2 ]; then
    echo "Usage: $0 <host> <port> [command]"
    echo "Example: $0 ssh8.vast.ai 24593"
    echo "Example: $0 ssh8.vast.ai 24593 'ls -la'"
    exit 1
fi

HOST="$1"
PORT="$2"
COMMAND="${3:-}"
KEY_PATH="/home/ballsac/.ssh/id_ed25519_jason_desktop"

# Load passphrase from .env file
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
ENV_FILE="$SCRIPT_DIR/../.env"

if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | grep 'SSH_PASSPHRASE' | xargs)
fi

if [ -z "$SSH_PASSPHRASE" ]; then
    echo "❌ SSH_PASSPHRASE not found in .env file"
    exit 1
fi

echo "🔗 Connecting to $HOST:$PORT"
echo "🔑 Using key: $KEY_PATH"

# Use expect to handle the SSH connection with passphrase
expect << EOF
set timeout 30
spawn ssh -i "$KEY_PATH" -p "$PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@"$HOST" $COMMAND
expect {
    "Enter passphrase for key*" {
        send "$SSH_PASSPHRASE\r"
        exp_continue
    }
    "assphrase for*" {
        send "$SSH_PASSPHRASE\r"
        exp_continue
    }
    "Password:" {
        send "$SSH_PASSPHRASE\r"
        exp_continue
    }
    "$ " {
        if {"$COMMAND" eq ""} {
            interact
        } else {
            expect eof
        }
    }
    "Connection refused" {
        puts "\n❌ Connection refused - instance may not be running"
        exit 1
    }
    "Permission denied" {
        puts "\n❌ Permission denied - check if your SSH key is added to Vast.ai"
        exit 1
    }
    timeout {
        puts "\n❌ Connection timeout"
        exit 1
    }
    eof {
        if {"$COMMAND" ne ""} {
            exit 0
        }
    }
}
EOF