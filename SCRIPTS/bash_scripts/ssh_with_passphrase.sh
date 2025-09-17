#!/bin/bash

# SSH connection script that handles encrypted keys
# Usage: ./ssh_with_passphrase.sh <host> <port> <command>

HOST="$1"
PORT="$2"
COMMAND="$3"
KEY_PATH="$HOME/.ssh/id_ed25519_jason_desktop"

# Read passphrase from environment
if [ -f "$(dirname "$0")/../.env" ]; then
    export $(grep -v '^#' "$(dirname "$0")/../.env" | grep 'SSH_PASSPHRASE' | xargs)
fi

if [ -z "$SSH_PASSPHRASE" ]; then
    echo "❌ SSH_PASSPHRASE not set in environment"
    exit 1
fi

# Use sshpass if available, otherwise use expect
if command -v sshpass >/dev/null 2>&1; then
    # Use sshpass (not typically for SSH keys, but let's try)
    ssh -i "$KEY_PATH" -p "$PORT" -o StrictHostKeyChecking=no root@"$HOST" "$COMMAND"
else
    # Use expect to handle the passphrase
    expect << EOF
spawn ssh -i "$KEY_PATH" -p "$PORT" -o StrictHostKeyChecking=no root@"$HOST" $COMMAND
expect {
    "Enter passphrase for key*" {
        send "$SSH_PASSPHRASE\r"
        exp_continue
    }
    "Password:" {
        send "$SSH_PASSPHRASE\r"
        exp_continue
    }
    eof
}
EOF
fi