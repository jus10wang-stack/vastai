#!/usr/bin/env python3
"""
Show which SSH key will be used by vai commands.
Useful for debugging and verification.
"""

import sys
import os

# Add parent directory to import utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from ssh_utils import detect_ssh_key


def main():
    """Display the SSH key that will be used."""
    ssh_key = detect_ssh_key()

    print("🔑 SSH Key Detection")
    print("=" * 60)
    print(f"Detected key: {ssh_key}")
    print(f"Key exists:   {'✅ Yes' if os.path.exists(ssh_key) else '❌ No'}")

    # Show if environment variable is set
    env_key = os.getenv("VAST_SSH_KEY")
    if env_key:
        expanded_env = os.path.expanduser(env_key)
        print(f"VAST_SSH_KEY: {env_key} {'✅ (override active)' if expanded_env == ssh_key else '⚠️  (not found, using fallback)'}")
    else:
        print(f"VAST_SSH_KEY: Not set (using auto-detection)")

    print("=" * 60)
    print("\n💡 To use a different key:")
    print("   Option 1 (Recommended): Edit your config file")
    print('      "ssh_key_path": "~/.ssh/your_key"')
    print("")
    print("   Option 2: Set environment variable")
    print('      export VAST_SSH_KEY="~/.ssh/your_key"')

    # Show key details if it exists
    if os.path.exists(ssh_key):
        import subprocess
        try:
            result = subprocess.run(
                ['ssh-keygen', '-l', '-f', ssh_key],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"\n🔐 Key fingerprint:")
                print(f"   {result.stdout.strip()}")
        except Exception as e:
            pass
    else:
        print(f"\n⚠️  SSH key not found at: {ssh_key}")
        print(f"   Create it with: ssh-keygen -t ed25519 -f {ssh_key}")


if __name__ == "__main__":
    main()
