#!/usr/bin/env python3
"""
Port Allocator - Manages local port assignment for multiple Vast.ai instances.

Tracks which local ports are allocated to which instances, automatically assigns
the next available port, and persists state across sessions.
"""

import json
import os
import socket
from pathlib import Path
from typing import Optional, Dict, List


class PortAllocator:
    """
    Manages local port allocation for SSH tunnels to Vast.ai instances.

    Features:
    - Auto-assigns next available port starting from base_port (default: 8188)
    - Persists port assignments to ~/.vai_ports.json
    - Checks if ports are actually available before assigning
    - Tracks instance_id → local_port mapping
    """

    def __init__(self, base_port: int = 8188, state_file: Optional[str] = None):
        """
        Initialize the port allocator.

        Args:
            base_port: Starting port number (default: 8188 for ComfyUI)
            state_file: Path to state file (default: ~/.vai_ports.json)
        """
        self.base_port = base_port

        # Default state file location
        if state_file is None:
            state_file = os.path.expanduser("~/.vai_ports.json")

        self.state_file = state_file
        self.allocations: Dict[str, int] = {}  # {instance_id: local_port}

        # Load existing allocations from file
        self._load_state()

    def _load_state(self):
        """Load port allocations from state file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    # Convert string keys back to proper format
                    self.allocations = {str(k): int(v) for k, v in data.items()}
            except Exception as e:
                print(f"⚠️  Warning: Could not load port state from {self.state_file}: {e}")
                self.allocations = {}
        else:
            self.allocations = {}

    def _save_state(self):
        """Persist port allocations to state file."""
        try:
            # Create parent directory if it doesn't exist
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)

            with open(self.state_file, 'w') as f:
                json.dump(self.allocations, f, indent=2)
        except Exception as e:
            print(f"⚠️  Warning: Could not save port state to {self.state_file}: {e}")

    def _is_port_available(self, port: int) -> bool:
        """
        Check if a port is available for binding on localhost.

        Args:
            port: Port number to check

        Returns:
            True if port is available, False otherwise
        """
        try:
            # Try to bind to the port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return True
        except OSError:
            # Port is already in use
            return False

    def _find_next_available_port(self) -> int:
        """
        Find the next available port starting from base_port.

        Checks both:
        1. Allocated ports in state
        2. Actual port availability on the system

        Returns:
            Next available port number
        """
        # Get all currently allocated ports
        allocated_ports = set(self.allocations.values())

        # Start searching from base_port
        candidate_port = self.base_port

        # Keep incrementing until we find an available port
        while True:
            # Check if port is not allocated AND actually available
            if candidate_port not in allocated_ports and self._is_port_available(candidate_port):
                return candidate_port

            candidate_port += 1

            # Safety check: don't go beyond port 65535
            if candidate_port > 65535:
                raise RuntimeError("No available ports found (exceeded port 65535)")

    def allocate(self, instance_id: str) -> int:
        """
        Allocate a local port for the given instance.

        If instance already has a port assigned, return that port.
        Otherwise, find and assign the next available port.

        Args:
            instance_id: Vast.ai instance ID

        Returns:
            Allocated local port number
        """
        # Convert instance_id to string for consistent key handling
        instance_id = str(instance_id)

        # Check if instance already has a port allocated
        if instance_id in self.allocations:
            existing_port = self.allocations[instance_id]
            print(f"📍 Instance {instance_id} already has port {existing_port} allocated")
            return existing_port

        # Find next available port
        port = self._find_next_available_port()

        # Allocate it to this instance
        self.allocations[instance_id] = port

        # Persist to disk
        self._save_state()

        print(f"✅ Allocated port {port} to instance {instance_id}")
        return port

    def get_port(self, instance_id: str) -> Optional[int]:
        """
        Get the allocated port for an instance (if it exists).

        Args:
            instance_id: Vast.ai instance ID

        Returns:
            Allocated port number, or None if not allocated
        """
        return self.allocations.get(str(instance_id))

    def release(self, instance_id: str) -> bool:
        """
        Release the port allocation for an instance.

        Args:
            instance_id: Vast.ai instance ID

        Returns:
            True if port was released, False if instance had no allocation
        """
        instance_id = str(instance_id)

        if instance_id in self.allocations:
            port = self.allocations.pop(instance_id)
            self._save_state()
            print(f"✅ Released port {port} for instance {instance_id}")
            return True
        else:
            print(f"⚠️  Instance {instance_id} has no port allocation")
            return False

    def list_allocations(self) -> Dict[str, int]:
        """
        Get all current port allocations.

        Returns:
            Dictionary of {instance_id: local_port}
        """
        return self.allocations.copy()

    def cleanup_stale_allocations(self, active_instance_ids: List[str]):
        """
        Remove port allocations for instances that no longer exist.

        Args:
            active_instance_ids: List of currently active instance IDs
        """
        active_ids = set(str(id) for id in active_instance_ids)
        stale_ids = set(self.allocations.keys()) - active_ids

        if stale_ids:
            print(f"🧹 Cleaning up {len(stale_ids)} stale port allocation(s)...")
            for instance_id in stale_ids:
                port = self.allocations.pop(instance_id)
                print(f"   Released port {port} for deleted instance {instance_id}")

            self._save_state()
        else:
            print("✅ No stale allocations found")


def main():
    """CLI for testing the port allocator."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python port_allocator.py <command> [args]")
        print("Commands:")
        print("  allocate <instance_id>           - Allocate port for instance")
        print("  get <instance_id>                - Get allocated port")
        print("  release <instance_id>            - Release port allocation")
        print("  list                             - List all allocations")
        print("  cleanup <instance_id1> <id2>...  - Clean up allocations not in list")
        sys.exit(1)

    allocator = PortAllocator()
    command = sys.argv[1]

    if command == "allocate":
        if len(sys.argv) < 3:
            print("Usage: allocate <instance_id>")
            sys.exit(1)
        instance_id = sys.argv[2]
        port = allocator.allocate(instance_id)
        print(f"Port {port} allocated to instance {instance_id}")

    elif command == "get":
        if len(sys.argv) < 3:
            print("Usage: get <instance_id>")
            sys.exit(1)
        instance_id = sys.argv[2]
        port = allocator.get_port(instance_id)
        if port:
            print(f"Instance {instance_id} → Port {port}")
        else:
            print(f"Instance {instance_id} has no allocation")

    elif command == "release":
        if len(sys.argv) < 3:
            print("Usage: release <instance_id>")
            sys.exit(1)
        instance_id = sys.argv[2]
        allocator.release(instance_id)

    elif command == "list":
        allocations = allocator.list_allocations()
        if allocations:
            print("Current port allocations:")
            for instance_id, port in sorted(allocations.items(), key=lambda x: x[1]):
                print(f"  Instance {instance_id} → Port {port}")
        else:
            print("No port allocations")

    elif command == "cleanup":
        if len(sys.argv) < 3:
            print("Usage: cleanup <instance_id1> <id2> ...")
            sys.exit(1)
        active_ids = sys.argv[2:]
        allocator.cleanup_stale_allocations(active_ids)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
