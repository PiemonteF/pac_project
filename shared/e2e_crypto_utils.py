#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
E2E Crypto Utils - Utilitários para Criptografia End-to-End Real
Gerencia sessões E2E e criptografia direta entre clientes usando ML-KEM + AES.
"""

import os
import json
import base64
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .pqc_crypto_utils import PQCKeyExchange, PQCAESCrypto

@dataclass
class E2ESession:
    client_a: str
    client_b: str
    aes_key: bytes
    crypto: PQCAESCrypto
    created_at: datetime
    
    def __post_init__(self):
        if not hasattr(self, 'crypto') or self.crypto is None:
            self.crypto = PQCAESCrypto(self.aes_key)
    
    def encrypt_message(self, message: str) -> str:
        return self.crypto.encrypt(message)
    
    def decrypt_message(self, encrypted_message: str) -> str:
        return self.crypto.decrypt(encrypted_message)
    
    def get_session_id(self) -> str:
        clients = sorted([self.client_a, self.client_b])
        return f"{clients[0]}_{clients[1]}"
    
    def __str__(self):
        return f"E2E({self.client_a} ↔ {self.client_b})"

class E2ESessionManager:    
    def __init__(self):
        """Initialize the E2E session manager."""
        self.sessions: Dict[str, E2ESession] = {}
        self.pqc_exchange = PQCKeyExchange()
        
        print("[E2E-MANAGER] Session Manager inicializado")
    
    def _get_session_key(self, client_a: str, client_b: str) -> str:
        """Get standardized session key."""
        clients = sorted([client_a, client_b])
        return f"{clients[0]}_{clients[1]}"
    
    def create_session(self, local_client: str, remote_client: str, 
                      local_secret_key: bytes, remote_public_key: bytes) -> Optional[E2ESession]:
        """Create a new E2E session between two clients."""
        try:
            print(f"[E2E-MANAGER] 🤝 Criando sessão: {local_client} ↔ {remote_client}")
            
            ciphertext, shared_secret = self.pqc_exchange.encapsulate(remote_public_key)
            if not shared_secret:
                print(f"[E2E-MANAGER] ❌ Falha no encapsulamento ML-KEM")
                return None
            
            aes_key = self.pqc_exchange.pqc.derive_aes_key(shared_secret)
            
            print(f"[E2E-MANAGER] - ML-KEM E2E:")
            print(f"[E2E-MANAGER] - Shared Secret: {shared_secret[:8].hex()}...")
            print(f"[E2E-MANAGER] - AES Key E2E: {aes_key[:8].hex()}...")
            
            # Create session
            session = E2ESession(
                client_a=local_client,
                client_b=remote_client,
                aes_key=aes_key,
                crypto=PQCAESCrypto(aes_key),
                created_at=datetime.now()
            )
            
            # Store session
            session_key = self._get_session_key(local_client, remote_client)
            self.sessions[session_key] = session
            
            print(f"[E2E-MANAGER] Sessão E2E criada: {session}")
            
            return session
            
        except Exception as e:
            print(f"[E2E-MANAGER] Erro ao criar sessão: {e}")
            return None
    
    def get_session(self, client_a: str, client_b: str) -> Optional[E2ESession]:
        session_key = self._get_session_key(client_a, client_b)
        return self.sessions.get(session_key)
    
    def has_session(self, client_a: str, client_b: str) -> bool:
        session_key = self._get_session_key(client_a, client_b)
        return session_key in self.sessions
    
    def encrypt_message(self, sender: str, recipient: str, message: str) -> Optional[str]:
        session = self.get_session(sender, recipient)
        if session:
            try:
                encrypted = session.encrypt_message(message)
                print(f"[E2E-MANAGER] Mensagem criptografada: {sender} → {recipient}")
                return encrypted
            except Exception as e:
                print(f"[E2E-MANAGER] Erro ao criptografar: {e}")
                return None
        else:
            print(f"[E2E-MANAGER] Sessão não encontrada: {sender} ↔ {recipient}")
            return None
    
    def decrypt_message(self, sender: str, recipient: str, encrypted_message: str) -> Optional[str]:
        session = self.get_session(sender, recipient)
        if session:
            try:
                decrypted = session.decrypt_message(encrypted_message)
                print(f"[E2E-MANAGER] Mensagem descriptografada: {sender} → {recipient}")
                return decrypted
            except Exception as e:
                print(f"[E2E-MANAGER] Erro ao descriptografar: {e}")
                return None
        else:
            print(f"[E2E-MANAGER] Sessão não encontrada: {sender} ↔ {recipient}")
            return None
    
    def remove_session(self, client_a: str, client_b: str) -> bool:
        session_key = self._get_session_key(client_a, client_b)
        if session_key in self.sessions:
            del self.sessions[session_key]
            print(f"[E2E-MANAGER] Sessão removida: {client_a} ↔ {client_b}")
            return True
        return False
    
    def list_sessions(self) -> List[str]:
        return [str(session) for session in self.sessions.values()]
    
    def get_session_count(self) -> int:
        return len(self.sessions)
    
    def clear_all_sessions(self):
        self.sessions.clear()
        print(f"[E2E-MANAGER] 🧹 Todas as sessões removidas")

class E2EMessageWrapper:
    
    @staticmethod
    def create_public_key_request(from_client: str, to_client: str) -> dict:
        """Create a public key request message."""
        return {
            "type": "public_key_request",
            "from": from_client,
            "to": to_client,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def create_public_key_response(from_client: str, to_client: str, public_key: bytes) -> dict:
        """Create a public key response message."""
        return {
            "type": "public_key_response",
            "from": from_client,
            "to": to_client,
            "public_key": base64.b64encode(public_key).decode('utf-8'),
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def create_encrypted_message(from_client: str, to_client: str, encrypted_data: str) -> dict:
        """Create an E2E encrypted message."""
        return {
            "type": "e2e_encrypted_message",
            "from": from_client,
            "to": to_client,
            "encrypted_data": encrypted_data,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def create_key_exchange_request(from_client: str, to_client: str, ciphertext: bytes) -> dict:
        """Create a key exchange request message."""
        return {
            "type": "e2e_key_exchange",
            "from": from_client,
            "to": to_client,
            "ciphertext": base64.b64encode(ciphertext).decode('utf-8'),
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def create_routing_error(message: str) -> dict:
        """Create a routing error message."""
        return {
            "type": "routing_error",
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def create_key_error(message: str) -> dict:
        """Create a key error message."""
        return {
            "type": "key_error",
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def is_e2e_message(message_data: dict) -> bool:
        """Check if message is an E2E message type."""
        e2e_types = {
            "public_key_request",
            "public_key_response", 
            "e2e_encrypted_message",
            "e2e_key_exchange",
            "routing_error",
            "key_error"
        }
        return message_data.get("type") in e2e_types
    
    @staticmethod
    def validate_message(message_data: dict) -> bool:
        """Validate E2E message format."""
        required_fields = ["type", "timestamp"]
        
        # Check required fields
        for field in required_fields:
            if field not in message_data:
                return False
        
        # Validate based on message type
        msg_type = message_data.get("type")
        
        if msg_type in ["public_key_request", "public_key_response", "e2e_encrypted_message", "e2e_key_exchange"]:
            if "from" not in message_data or "to" not in message_data:
                return False
        
        if msg_type == "public_key_response" and "public_key" not in message_data:
            return False
        
        if msg_type == "e2e_encrypted_message" and "encrypted_data" not in message_data:
            return False
        
        if msg_type == "e2e_key_exchange" and "ciphertext" not in message_data:
            return False
        
        return True

class E2EKeyRotation:
    """Gerencia rotação de chaves E2E para segurança adicional."""
    
    def __init__(self, rotation_interval_hours: int = 24):
        """Initialize key rotation manager."""
        self.rotation_interval_hours = rotation_interval_hours
        self.rotation_history: Dict[str, List[datetime]] = {}
    
    def should_rotate_session(self, session: E2ESession) -> bool:
        """Check if session key should be rotated."""
        from datetime import timedelta
        
        age = datetime.now() - session.created_at
        return age > timedelta(hours=self.rotation_interval_hours)
    
    def rotate_session_key(self, session_manager: E2ESessionManager, 
                          client_a: str, client_b: str,
                          local_secret_key: bytes, remote_public_key: bytes) -> bool:
        """Rotate session key between two clients."""
        try:
            # Remove old session
            session_manager.remove_session(client_a, client_b)
            
            # Create new session
            new_session = session_manager.create_session(
                client_a, client_b, local_secret_key, remote_public_key
            )
            
            if new_session:
                # Record rotation
                session_id = new_session.get_session_id()
                if session_id not in self.rotation_history:
                    self.rotation_history[session_id] = []
                self.rotation_history[session_id].append(datetime.now())
                
                print(f"[E2E-ROTATION] Chave rotacionada: {client_a} ↔ {client_b}")
                return True
            
            return False
            
        except Exception as e:
            print(f"[E2E-ROTATION] Erro na rotação: {e}")
            return False

# Utility functions
def generate_session_id(client_a: str, client_b: str) -> str:
    """Generate unique session ID for two clients."""
    clients = sorted([client_a, client_b])
    combined = f"{clients[0]}_{clients[1]}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]

def format_e2e_stats(session_manager: E2ESessionManager) -> str:
    """Format E2E statistics as string."""
    stats = []
    stats.append(f" - Estatísticas E2E:")
    stats.append(f" - Sessões ativas: {session_manager.get_session_count()}")
    
    sessions = session_manager.list_sessions()
    if sessions:
        stats.append(f"📋 Sessões:")
        for session in sessions:
            stats.append(f"  • {session}")
    
    return "\n".join(stats)

# Testing utilities
def test_e2e_session():
    """Test E2E session functionality."""
    print("\n=== TESTE E2E SESSION ===")
    
    # Create session manager
    manager = E2ESessionManager()
    
    # Mock keys (in real usage, these come from ML-KEM key generation)
    from .key_generation.key_manager import KeyManager
    
    try:
        key_manager = KeyManager("keys/clients")
        
        # Generate test keys
        alice_public, alice_secret = key_manager.generate_client_keypair("alice_test")
        bob_public, bob_secret = key_manager.generate_client_keypair("bob_test")
        
        # Create session
        session = manager.create_session("alice_test", "bob_test", alice_secret, bob_public)
        
        if session:
            # Test encryption/decryption
            test_message = "Olá Bob! Esta é uma mensagem E2E real!"
            
            encrypted = manager.encrypt_message("alice_test", "bob_test", test_message)
            if encrypted:
                decrypted = manager.decrypt_message("alice_test", "bob_test", encrypted)
                
                print(f" - Mensagem original: {test_message}")
                print(f" - Mensagem criptografada: {encrypted[:50]}...")
                print(f" - Mensagem descriptografada: {decrypted}")
                
                if test_message == decrypted:
                    print("Teste E2E PASSOU!")
                else:
                    print("Teste E2E FALHOU!")
            else:
                print("Falha na criptografia")
        else:
            print("Falha ao criar sessão")
            
    except Exception as e:
        print(f"Erro no teste: {e}")
    
    print("========================\n")

if __name__ == "__main__":
    # Run tests if executed directly
    test_e2e_session() 