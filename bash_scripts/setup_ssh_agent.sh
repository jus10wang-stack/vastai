#!/bin/bash

# Script to set up SSH agent with your encrypted key
# This will allow you to SSH without typing the passphrase every time

echo "🔑 Setting up SSH agent for encrypted key..."

# Kill any existing ssh-agent
pkill -f ssh-agent 2>/dev/null

# Start a new SSH agent and export variables for current session
eval "$(ssh-agent -s)"

echo "🔐 Adding your encrypted SSH key..."

# Use expect to handle the passphrase automatically
expect << 'EOF'
spawn ssh-add /home/ballsac/.ssh/id_ed25519_jason_desktop
expect {
    "Enter passphrase for key*" {
        send "Nipple123#\r"
        expect eof
    }
    "Identity added*" {
        expect eof
    }
    timeout {
        puts "Timeout waiting for passphrase prompt"
        exit 1
    }
}
EOF

# Check if the key was added successfully
if ssh-add -l | grep -q "id_ed25519_jason_desktop"; then
    echo "✅ SSH key added successfully!"
    echo "📋 Current loaded keys:"
    ssh-add -l
    echo ""
    echo "💡 Now you can SSH directly with:"
    echo "   ssh -p <PORT> root@<HOST>"
    echo ""
    echo "🔄 To make this permanent, add these lines to your ~/.bashrc:"
    echo "   eval \"\$(ssh-agent -s)\" >/dev/null 2>&1"
    echo "   ssh-add /home/ballsac/.ssh/id_ed25519_jason_desktop >/dev/null 2>&1"
else
    echo "❌ Failed to add SSH key. Check your passphrase."
    exit 1
fi