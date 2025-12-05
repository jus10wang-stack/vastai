#!/usr/bin/env python3
"""
SSH Tunnel Manager - Manages SSH tunnels for multiple Vast.ai instances.

Automatically creates, tracks, and manages SSH tunnels in the background,
allowing multiple instances to be accessed via different localhost ports.
"""

import json
import os
import subprocess
import signal
import time
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

from .port_allocator import PortAllocator
from .ssh_utils import detect_ssh_key


class TunnelManager:
    """
    Manages SSH tunnels for multiple Vast.ai instances.

    Features:
    - Auto-creates SSH tunnels in background using subprocess
    - Tracks tunnel PIDs for graceful shutdown
    - Persists tunnel state to ~/.vai_tunnels.json
    - Integrates with PortAllocator for port assignment
    - Handles tunnel cleanup on instance destruction
    """

    def __init__(self, state_file: Optional[str] = None, port_allocator: Optional[PortAllocator] = None):
        """
        Initialize the tunnel manager.

        Args:
            state_file: Path to state file (default: ~/.vai_tunnels.json)
            port_allocator: PortAllocator instance (creates new one if not provided)
        """
        # Default state file location
        if state_file is None:
            state_file = os.path.expanduser("~/.vai_tunnels.json")

        self.state_file = state_file

        # Initialize or use provided port allocator
        self.port_allocator = port_allocator or PortAllocator()

        # {instance_id: {local_port, ssh_host, ssh_port, remote_port, pid, created_at, ssh_key_path}}
        self.tunnels: Dict[str, Dict] = {}

        # Load existing tunnel state
        self._load_state()

        # Clean up any dead tunnels (PIDs that no longer exist)
        self._cleanup_dead_tunnels()

    def _load_state(self):
        """Load tunnel state from file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    self.tunnels = json.load(f)
                    # Convert string keys to proper format
                    self.tunnels = {str(k): v for k, v in self.tunnels.items()}
            except Exception as e:
                print(f"⚠️  Warning: Could not load tunnel state from {self.state_file}: {e}")
                self.tunnels = {}
        else:
            self.tunnels = {}

    def _save_state(self):
        """Persist tunnel state to file."""
        try:
            # Create parent directory if needed
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)

            with open(self.state_file, 'w') as f:
                json.dump(self.tunnels, f, indent=2)
        except Exception as e:
            print(f"⚠️  Warning: Could not save tunnel state to {self.state_file}: {e}")

    def _is_process_running(self, pid: int) -> bool:
        """
        Check if a process with given PID is still running.

        Args:
            pid: Process ID

        Returns:
            True if process exists, False otherwise
        """
        try:
            # Send signal 0 to check if process exists (doesn't actually kill it)
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def _cleanup_dead_tunnels(self):
        """Remove tunnel entries for processes that are no longer running."""
        dead_instances = []

        for instance_id, tunnel_info in self.tunnels.items():
            pid = tunnel_info.get('pid')
            if pid and not self._is_process_running(pid):
                dead_instances.append(instance_id)

        if dead_instances:
            print(f"🧹 Cleaning up {len(dead_instances)} dead tunnel(s)...")
            for instance_id in dead_instances:
                tunnel_info = self.tunnels.pop(instance_id)
                print(f"   Removed dead tunnel for instance {instance_id} (port {tunnel_info['local_port']})")

            self._save_state()

    def create_tunnel(
        self,
        instance_id: str,
        ssh_host: str,
        ssh_port: int,
        remote_port: int = 8188,
        ssh_key_path: Optional[str] = None
    ) -> int:
        """
        Create an SSH tunnel for the given instance.

        Args:
            instance_id: Vast.ai instance ID
            ssh_host: SSH hostname (e.g., ssh4.vast.ai)
            ssh_port: SSH port
            remote_port: Remote port to forward (default: 8188 for ComfyUI)
            ssh_key_path: Path to SSH private key (auto-detects if None)

        Returns:
            Local port number where tunnel is accessible
        """
        instance_id = str(instance_id)

        # Check if tunnel already exists
        if instance_id in self.tunnels:
            existing = self.tunnels[instance_id]
            # Verify the process is still running
            if self._is_process_running(existing.get('pid', 0)):
                print(f"📍 Tunnel already exists for instance {instance_id} on port {existing['local_port']}")
                return existing['local_port']
            else:
                print(f"⚠️  Found dead tunnel for instance {instance_id}, recreating...")
                self.tunnels.pop(instance_id)

        # Auto-detect SSH key if not provided
        if ssh_key_path is None:
            ssh_key_path = detect_ssh_key()

        # Allocate a local port
        local_port = self.port_allocator.allocate(instance_id)

        # Build SSH tunnel command
        # -N: No remote command execution (just tunnel)
        # -L: Local port forwarding
        # -o ServerAliveInterval=60: Keep connection alive
        # -o ServerAliveCountMax=3: Max keepalive failures before disconnect
        # -o StrictHostKeyChecking=no: Auto-accept host keys
        cmd = [
            "ssh",
            "-N",  # No remote command
            "-L", f"{local_port}:localhost:{remote_port}",  # Port forwarding
            "-p", str(ssh_port),  # SSH port
            "-i", ssh_key_path,  # SSH key
            "-o", "ServerAliveInterval=60",  # Keepalive every 60s
            "-o", "ServerAliveCountMax=3",  # Max 3 failures
            "-o", "StrictHostKeyChecking=no",  # Auto-accept host keys
            "-o", "UserKnownHostsFile=/dev/null",  # Don't save to known_hosts
            f"root@{ssh_host}"
        ]

        # Launch SSH tunnel as background process
        try:
            print(f"🔗 Creating SSH tunnel for instance {instance_id}...")
            print(f"   Local: localhost:{local_port} → Remote: {ssh_host}:{ssh_port} (port {remote_port})")

            # Start process in background, detached from current session
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True  # Detach from parent
            )

            # Give it a moment to establish connection
            time.sleep(2)

            # Verify process is still running (didn't immediately fail)
            if not self._is_process_running(process.pid):
                raise RuntimeError("SSH tunnel process died immediately after launch")

            # Store tunnel info
            self.tunnels[instance_id] = {
                "local_port": local_port,
                "ssh_host": ssh_host,
                "ssh_port": ssh_port,
                "remote_port": remote_port,
                "pid": process.pid,
                "created_at": datetime.now().isoformat(),
                "ssh_key_path": ssh_key_path
            }

            # Save state
            self._save_state()

            print(f"✅ Tunnel created successfully!")
            print(f"   PID: {process.pid}")
            print(f"   Access at: http://localhost:{local_port}")

            return local_port

        except Exception as e:
            print(f"❌ Failed to create SSH tunnel: {e}")
            # Release the allocated port
            self.port_allocator.release(instance_id)
            raise

    def get_tunnel(self, instance_id: str) -> Optional[Dict]:
        """
        Get tunnel information for an instance.

        Args:
            instance_id: Vast.ai instance ID

        Returns:
            Tunnel info dict, or None if no tunnel exists
        """
        return self.tunnels.get(str(instance_id))

    def close_tunnel(self, instance_id: str) -> bool:
        """
        Close the SSH tunnel for an instance.

        Args:
            instance_id: Vast.ai instance ID

        Returns:
            True if tunnel was closed, False if no tunnel existed
        """
        instance_id = str(instance_id)

        if instance_id not in self.tunnels:
            print(f"⚠️  No tunnel exists for instance {instance_id}")
            return False

        tunnel_info = self.tunnels[instance_id]
        pid = tunnel_info.get('pid')
        local_port = tunnel_info.get('local_port')

        # Kill the SSH process
        if pid:
            try:
                if self._is_process_running(pid):
                    os.kill(pid, signal.SIGTERM)
                    print(f"✅ Closed tunnel for instance {instance_id} (port {local_port}, PID {pid})")
                else:
                    print(f"⚠️  Tunnel process {pid} was already dead")
            except Exception as e:
                print(f"⚠️  Error killing process {pid}: {e}")

        # Remove from state
        self.tunnels.pop(instance_id)

        # Release the port allocation
        self.port_allocator.release(instance_id)

        # Save state
        self._save_state()

        return True

    def close_all_tunnels(self):
        """Close all active SSH tunnels."""
        if not self.tunnels:
            print("✅ No active tunnels to close")
            return

        instance_ids = list(self.tunnels.keys())
        print(f"🔒 Closing {len(instance_ids)} tunnel(s)...")

        for instance_id in instance_ids:
            self.close_tunnel(instance_id)

        print("✅ All tunnels closed")

    def list_tunnels(self) -> Dict[str, Dict]:
        """
        Get all active tunnels.

        Returns:
            Dictionary of {instance_id: tunnel_info}
        """
        # Clean up dead tunnels first
        self._cleanup_dead_tunnels()

        return self.tunnels.copy()

    def print_tunnels_table(self):
        """Print a formatted table of all active tunnels."""
        tunnels = self.list_tunnels()

        if not tunnels:
            print("📭 No active SSH tunnels")
            return

        print("\n📡 Active SSH Tunnels:")
        print("=" * 80)
        print(f"{'Instance ID':<15} {'SSH Host:Port':<30} {'Local Port':<12} {'PID':<10}")
        print("-" * 80)

        for instance_id, info in sorted(tunnels.items(), key=lambda x: x[1]['local_port']):
            ssh_location = f"{info['ssh_host']}:{info['ssh_port']}"
            local_port = info['local_port']
            pid = info.get('pid', 'N/A')

            print(f"{instance_id:<15} {ssh_location:<30} {local_port:<12} {pid:<10}")

        print("=" * 80)
        print(f"Total: {len(tunnels)} active tunnel(s)")
        print()


def main():
    """CLI for testing the tunnel manager."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python tunnel_manager.py <command> [args]")
        print("Commands:")
        print("  create <instance_id> <ssh_host> <ssh_port>  - Create tunnel")
        print("  get <instance_id>                           - Get tunnel info")
        print("  close <instance_id>                         - Close tunnel")
        print("  close-all                                   - Close all tunnels")
        print("  list                                        - List all tunnels")
        sys.exit(1)

    manager = TunnelManager()
    command = sys.argv[1]

    if command == "create":
        if len(sys.argv) < 5:
            print("Usage: create <instance_id> <ssh_host> <ssh_port> [remote_port]")
            sys.exit(1)
        instance_id = sys.argv[2]
        ssh_host = sys.argv[3]
        ssh_port = int(sys.argv[4])
        remote_port = int(sys.argv[5]) if len(sys.argv) > 5 else 8188

        local_port = manager.create_tunnel(instance_id, ssh_host, ssh_port, remote_port)
        print(f"\n🌐 Access ComfyUI at: http://localhost:{local_port}")

    elif command == "get":
        if len(sys.argv) < 3:
            print("Usage: get <instance_id>")
            sys.exit(1)
        instance_id = sys.argv[2]
        tunnel = manager.get_tunnel(instance_id)
        if tunnel:
            print(f"Tunnel for instance {instance_id}:")
            print(json.dumps(tunnel, indent=2))
        else:
            print(f"No tunnel exists for instance {instance_id}")

    elif command == "close":
        if len(sys.argv) < 3:
            print("Usage: close <instance_id>")
            sys.exit(1)
        instance_id = sys.argv[2]
        manager.close_tunnel(instance_id)

    elif command == "close-all":
        manager.close_all_tunnels()

    elif command == "list":
        manager.print_tunnels_table()

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
