# key_manager.py - ML-KEM Key Management for PQC Chat
import os
import sys
import base64
import json
import hashlib
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.pqc_crypto_utils import PQCKeyExchange

class KeyManager:
    """Manages ML-KEM keypairs for server and clients with persistent storage."""
    
    def __init__(self, keys_dir="keys"):
        """Initialize key manager with specified keys directory."""
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(exist_ok=True)
        print(f"[KEY_MANAGER] Using keys directory: {self.keys_dir.absolute()}")
        
        try:
            self.pqc_exchange = PQCKeyExchange()
        except Exception as e:
            print(f"[KEY_MANAGER] Failed to initialize PQC: {e}")
            raise
    
    def generate_server_keypair(self, server_id="main_server"):
        """Generate and save a keypair for the server."""
        try:
            print(f"[KEY_MANAGER] Generating new server keypair for '{server_id}'...")
            
            # Generate keypair
            public_key, secret_key = self.pqc_exchange.generate_keypair()
            if not public_key or not secret_key:
                raise RuntimeError("Failed to generate server keypair")
            
            # Save keys
            server_dir = self.keys_dir / "server" / server_id
            server_dir.mkdir(parents=True, exist_ok=True)
            
            public_key_path = server_dir / "public_key.bin"
            secret_key_path = server_dir / "secret_key.bin"
            
            with open(public_key_path, 'wb') as f:
                f.write(public_key)
            with open(secret_key_path, 'wb') as f:
                f.write(secret_key)
            
            # Create metadata file
            metadata = {
                "server_id": server_id,
                "algorithm": "ML-KEM-512",
                "public_key_length": len(public_key),
                "secret_key_length": len(secret_key),
                "created_at": self._get_timestamp()
            }
            
            metadata_path = server_dir / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"[KEY_MANAGER] Server keypair saved:")
            print(f"  Public key: {public_key_path}")
            print(f"  Secret key: {secret_key_path}")
            print(f"  Metadata: {metadata_path}")
            
            return public_key, secret_key
            
        except Exception as e:
            print(f"[KEY_MANAGER] Failed to generate server keypair: {e}")
            raise
    
    def generate_client_keypair(self, client_name):
        """Generate and save a keypair for a client."""
        try:
            # Validate client name
            if not self._is_valid_name(client_name):
                raise ValueError("Client name must contain only alphanumeric characters and underscores")
            
            print(f"[KEY_MANAGER] Generating new client keypair for '{client_name}'...")
            
            # Generate keypair
            public_key, secret_key = self.pqc_exchange.generate_keypair()
            if not public_key or not secret_key:
                raise RuntimeError("Failed to generate client keypair")
            
            # Save keys
            client_dir = self.keys_dir / "clients" / client_name
            client_dir.mkdir(parents=True, exist_ok=True)
            
            public_key_path = client_dir / "public_key.bin"
            secret_key_path = client_dir / "secret_key.bin"
            
            with open(public_key_path, 'wb') as f:
                f.write(public_key)
            with open(secret_key_path, 'wb') as f:
                f.write(secret_key)
            
            # Create metadata file
            metadata = {
                "client_name": client_name,
                "algorithm": "ML-KEM-512",
                "public_key_length": len(public_key),
                "secret_key_length": len(secret_key),
                "created_at": self._get_timestamp()
            }
            
            metadata_path = client_dir / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"[KEY_MANAGER] Client keypair saved:")
            print(f"  Public key: {public_key_path}")
            print(f"  Secret key: {secret_key_path}")
            print(f"  Metadata: {metadata_path}")
            
            return public_key, secret_key
            
        except Exception as e:
            print(f"[KEY_MANAGER] Failed to generate client keypair: {e}")
            raise
    
    def load_server_keypair(self, server_id="main_server"):
        """Load server keypair from storage."""
        try:
            server_dir = self.keys_dir / "server" / server_id
            
            if not server_dir.exists():
                print(f"[KEY_MANAGER] Server keypair not found for '{server_id}'. Generate one first.")
                return None, None
            
            public_key_path = server_dir / "public_key.bin"
            secret_key_path = server_dir / "secret_key.bin"
            
            if not public_key_path.exists() or not secret_key_path.exists():
                print(f"[KEY_MANAGER] Incomplete server keypair for '{server_id}'")
                return None, None
            
            with open(public_key_path, 'rb') as f:
                public_key = f.read()
            with open(secret_key_path, 'rb') as f:
                secret_key = f.read()
            
            print(f"[KEY_MANAGER] Loaded server keypair for '{server_id}'")
            return public_key, secret_key
            
        except Exception as e:
            print(f"[KEY_MANAGER] Failed to load server keypair: {e}")
            return None, None
    
    def load_client_keypair(self, client_name):
        """Load client keypair from storage."""
        try:
            client_dir = self.keys_dir / "clients" / client_name
            
            if not client_dir.exists():
                print(f"[KEY_MANAGER] Client keypair not found for '{client_name}'. Generate one first.")
                return None, None
            
            public_key_path = client_dir / "public_key.bin"
            secret_key_path = client_dir / "secret_key.bin"
            
            if not public_key_path.exists() or not secret_key_path.exists():
                print(f"[KEY_MANAGER] Incomplete client keypair for '{client_name}'")
                return None, None
            
            with open(public_key_path, 'rb') as f:
                public_key = f.read()
            with open(secret_key_path, 'rb') as f:
                secret_key = f.read()
            
            print(f"[KEY_MANAGER] Loaded client keypair for '{client_name}'")
            return public_key, secret_key
            
        except Exception as e:
            print(f"[KEY_MANAGER] Failed to load client keypair: {e}")
            return None, None
    
    def list_server_keys(self):
        """List available server keypairs."""
        server_dir = self.keys_dir / "server"
        if not server_dir.exists():
            return []
        
        servers = []
        for item in server_dir.iterdir():
            if item.is_dir() and (item / "public_key.bin").exists():
                servers.append(item.name)
        
        return servers
    
    def list_client_keys(self):
        """List available client keypairs."""
        clients_dir = self.keys_dir / "clients"
        if not clients_dir.exists():
            return []
        
        clients = []
        for item in clients_dir.iterdir():
            if item.is_dir() and (item / "public_key.bin").exists():
                clients.append(item.name)
        
        return clients
    
    def export_public_key(self, entity_type, entity_name):
        """Export a public key as base64 for sharing."""
        try:
            if entity_type == "server":
                public_key, _ = self.load_server_keypair(entity_name)
            elif entity_type == "client":
                public_key, _ = self.load_client_keypair(entity_name)
            else:
                raise ValueError("entity_type must be 'server' or 'client'")
            
            if public_key:
                return base64.b64encode(public_key).decode('utf-8')
            else:
                return None
                
        except Exception as e:
            print(f"[KEY_MANAGER] Failed to export public key: {e}")
            return None
    
    def verify_keypair(self, public_key, secret_key):
        """Verify that a keypair is valid by testing encapsulation/decapsulation."""
        try:
            # Test encapsulation with public key
            ciphertext, shared_secret1 = self.pqc_exchange.encapsulate(public_key)
            if not ciphertext or not shared_secret1:
                return False
            
            # Test decapsulation with secret key
            shared_secret2 = self.pqc_exchange.decapsulate(secret_key, ciphertext)
            if not shared_secret2:
                return False
            
            # Check if shared secrets match
            return shared_secret1 == shared_secret2
            
        except Exception as e:
            print(f"[KEY_MANAGER] Keypair verification failed: {e}")
            return False
    
    def _is_valid_name(self, name):
        """Check if a name contains only valid characters."""
        return name.replace('_', '').replace('-', '').isalnum()
    
    def _get_timestamp(self):
        """Get current timestamp as string."""
        from datetime import datetime
        return datetime.now().isoformat()

def main():
    """Command-line interface for key management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ML-KEM Key Manager for PQC Chat")
    parser.add_argument("--keys-dir", default="keys", help="Directory to store keys")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Generate server keypair
    server_parser = subparsers.add_parser("generate-server", help="Generate server keypair")
    server_parser.add_argument("--server-id", default="main_server", help="Server identifier")
    
    # Generate client keypair
    client_parser = subparsers.add_parser("generate-client", help="Generate client keypair")
    client_parser.add_argument("client_name", help="Client name")
    
    # List keys
    list_parser = subparsers.add_parser("list", help="List available keys")
    list_parser.add_argument("type", choices=["server", "client", "all"], help="Type of keys to list")
    
    # Export public key
    export_parser = subparsers.add_parser("export", help="Export public key as base64")
    export_parser.add_argument("type", choices=["server", "client"], help="Entity type")
    export_parser.add_argument("name", help="Entity name")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        key_manager = KeyManager(args.keys_dir)
        
        if args.command == "generate-server":
            key_manager.generate_server_keypair(args.server_id)
            
        elif args.command == "generate-client":
            key_manager.generate_client_keypair(args.client_name)
            
        elif args.command == "list":
            if args.type in ["server", "all"]:
                servers = key_manager.list_server_keys()
                print(f"Server keys ({len(servers)}):")
                for server in servers:
                    print(f"  - {server}")
            
            if args.type in ["client", "all"]:
                clients = key_manager.list_client_keys()
                print(f"Client keys ({len(clients)}):")
                for client in clients:
                    print(f"  - {client}")
        
        elif args.command == "export":
            public_key_b64 = key_manager.export_public_key(args.type, args.name)
            if public_key_b64:
                print(f"Public key for {args.type} '{args.name}':")
                print(public_key_b64)
            else:
                print(f"Failed to export public key for {args.type} '{args.name}'")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 