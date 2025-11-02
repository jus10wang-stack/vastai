#!/usr/bin/env python3
"""
SSH utility functions for Vast.ai instance management.
Provides portable SSH key detection across different user environments.
"""

import os


def detect_ssh_key(preferred_key=None):
    """
    Auto-detect SSH key path with flexible fallback strategy.

    Priority order:
    1. Explicit preferred_key argument (if provided and exists)
    2. VAST_SSH_KEY environment variable (if set and exists)
    3. Common SSH key locations (checked in order)
    4. Fallback to ~/.ssh/id_ed25519_vastai (even if doesn't exist)

    Args:
        preferred_key (str, optional): Preferred SSH key path to use if it exists

    Returns:
        str: Absolute path to SSH key file

    Examples:
        >>> detect_ssh_key()
        '/home/user/.ssh/id_ed25519_vastai'

        >>> os.environ['VAST_SSH_KEY'] = '~/.ssh/custom_key'
        >>> detect_ssh_key()
        '/home/user/.ssh/custom_key'

        >>> detect_ssh_key(preferred_key='~/.ssh/my_key')
        '/home/user/.ssh/my_key'
    """
    # Priority 1: Explicit preferred key
    if preferred_key:
        expanded_path = os.path.expanduser(preferred_key)
        if os.path.exists(expanded_path):
            return expanded_path

    # Priority 2: Environment variable
    env_key = os.getenv("VAST_SSH_KEY")
    if env_key:
        expanded_path = os.path.expanduser(env_key)
        if os.path.exists(expanded_path):
            return expanded_path

    # Priority 3: Check common SSH key locations (Vast.ai specific first)
    common_keys = [
        "~/.ssh/id_ed25519_vastai",       # Vast.ai specific key (unencrypted) - PRIMARY
        "~/.ssh/id_ed25519",              # Standard Ed25519 key
        "~/.ssh/id_rsa",                  # Standard RSA key
        "~/.ssh/id_ecdsa",                # Standard ECDSA key
    ]

    for key_path in common_keys:
        expanded_path = os.path.expanduser(key_path)
        if os.path.exists(expanded_path):
            return expanded_path

    # Priority 4: Fallback to Vast.ai specific key (may not exist, but reasonable default)
    fallback = os.path.expanduser("~/.ssh/id_ed25519_vastai")
    return fallback


def get_ssh_command_string(ssh_host, ssh_port, local_port=8188, remote_port=8188, ssh_key_path=None):
    """
    Generate a portable SSH command string for port forwarding.

    Args:
        ssh_host (str): SSH hostname (e.g., 'ssh5.vast.ai')
        ssh_port (int): SSH port number (e.g., 12345)
        local_port (int): Local port to forward to (default: 8188)
        remote_port (int): Remote port to forward from (default: 8188)
        ssh_key_path (str, optional): SSH key path (auto-detected if not provided)

    Returns:
        str: Complete SSH command string ready for execution

    Example:
        >>> get_ssh_command_string('ssh5.vast.ai', 12345)
        'ssh -i ~/.ssh/id_ed25519_vastai -p 12345 root@ssh5.vast.ai -L 8188:localhost:8188'
    """
    # Auto-detect SSH key if not provided
    if not ssh_key_path:
        ssh_key_path = detect_ssh_key()

    # Use ~ notation if path is in user's home directory for better portability
    home_dir = os.path.expanduser("~")
    if ssh_key_path.startswith(home_dir):
        # Replace absolute home path with ~ for portability
        display_path = ssh_key_path.replace(home_dir, "~", 1)
    else:
        display_path = ssh_key_path

    return f"ssh -i {display_path} -p {ssh_port} root@{ssh_host} -L {local_port}:localhost:{remote_port}"
