# pqc_crypto_utils.py
import os
import base64
import json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

try:
    from .pqc_wrapper import get_pqc_instance
    PQC_AVAILABLE = True
except ImportError:
    PQC_AVAILABLE = False
    print("[WARNING] PQC library not available. Falling back to password-based encryption.")

class PQCAESCrypto:
    def __init__(self, aes_key=None):
        """
        Initialize with either a derived AES key or use PQC key exchange.
        """
        self.backend = default_backend()
        self.aes_key = aes_key
        self.pqc = None
        
        if PQC_AVAILABLE and aes_key is None:
            try:
                self.pqc = get_pqc_instance()
            except Exception as e:
                print(f"[WARNING] Could not initialize PQC: {e}")
                self.pqc = None
    
    def set_aes_key(self, key):
        """Set the AES encryption key (32 bytes for AES-256)."""
        if len(key) != 32:
            raise ValueError("AES key must be 32 bytes for AES-256")
        self.aes_key = key
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string using AES-256-CBC.
        Returns base64 encoded result.
        """
        if not self.aes_key:
            raise RuntimeError("No AES key available for encryption")
        
        # Generate a random 16-byte IV for each message
        iv = os.urandom(16)
        
        # Create cipher
        cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(iv), backend=self.backend)
        encryptor = cipher.encryptor()
        
        # Apply PKCS7 padding
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext.encode('utf-8'))
        padded_data += padder.finalize()
        
        # Encrypt the data
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        
        # Combine IV and encrypted data, then base64 encode
        combined = iv + encrypted_data
        return base64.b64encode(combined).decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt a base64 encoded encrypted string.
        Expected format: IV + encrypted_data (base64 encoded)
        """
        if not self.aes_key:
            raise RuntimeError("No AES key available for decryption")
        
        try:
            # Decode from base64
            combined = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Extract IV (first 16 bytes) and encrypted data
            iv = combined[:16]
            encrypted_bytes = combined[16:]
            
            # Create cipher
            cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(iv), backend=self.backend)
            decryptor = cipher.decryptor()
            
            # Decrypt the data
            padded_data = decryptor.update(encrypted_bytes) + decryptor.finalize()
            
            # Remove PKCS7 padding
            unpadder = padding.PKCS7(128).unpadder()
            plaintext_bytes = unpadder.update(padded_data)
            plaintext_bytes += unpadder.finalize()
            
            return plaintext_bytes.decode('utf-8')
        
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")

class PQCKeyExchange:
    """Handle ML-KEM key exchange for establishing shared secrets."""
    
    def __init__(self):
        if not PQC_AVAILABLE:
            raise RuntimeError("PQC library not available")
        
        try:
            self.pqc = get_pqc_instance()
            self.lengths = self.pqc.get_lengths()
            print(f"[PQC] Initialized ML-KEM-512 successfully")
        except Exception as e:
            print(f"[PQC] Failed to initialize: {e}")
            raise
        
    def generate_keypair(self):
        """Generate a new ML-KEM key pair. Returns raw bytes."""
        try:
            public_key, secret_key = self.pqc.generate_keypair()
            print(f"[PQC] Generated new key pair")
            return public_key, secret_key
        except Exception as e:
            print(f"[PQC] Failed to generate keypair: {e}")
            return None, None
    
    def encapsulate(self, public_key):
        """
        Encapsulate a shared secret using the given public key (raw bytes).
        Returns ciphertext (raw bytes) and shared_secret (raw bytes).
        """
        try:
            ciphertext, shared_secret = self.pqc.encapsulate(public_key)
            return ciphertext, shared_secret
        except Exception as e:
            print(f"[PQC] Encapsulation failed: {e}")
            return None, None
    
    def decapsulate(self, secret_key, ciphertext):
        """
        Decapsulate the shared secret using secret key and ciphertext (both raw bytes).
        Returns shared_secret (raw bytes).
        """
        try:
            shared_secret = self.pqc.decapsulate(secret_key, ciphertext)
            return shared_secret
        except Exception as e:
            print(f"[PQC] Decapsulation failed: {e}")
            return None

# Protocol for key exchange messages
class PQCProtocol:
    """Protocol handler for PQC key exchange in the chat application."""
    
    @staticmethod
    def create_key_exchange_request(public_key_b64):
        """Create a key exchange request message."""
        return json.dumps({
            'type': 'pqc_key_exchange',
            'public_key': public_key_b64
        })
    
    @staticmethod
    def create_key_exchange_response(ciphertext_b64):
        """Create a key exchange response message."""
        return json.dumps({
            'type': 'pqc_key_response',
            'ciphertext': ciphertext_b64
        })
    
    @staticmethod
    def parse_message(message):
        """Parse a potential PQC protocol message."""
        try:
            data = json.loads(message)
            if 'type' in data and data['type'].startswith('pqc_'):
                return data
        except (json.JSONDecodeError, TypeError):
            pass
        return None
    
    @staticmethod
    def is_pqc_message(message):
        """Check if a message is a PQC protocol message."""
        return PQCProtocol.parse_message(message) is not None

# Fallback to password-based encryption if PQC is not available
def get_fallback_crypto_instance():
    """Get a fallback crypto instance using password-based encryption."""
    import hashlib
    fallback_password = "MySecureChatPassword2024!"
    aes_key = hashlib.sha256(fallback_password.encode('utf-8')).digest()
    return PQCAESCrypto(aes_key)

# Factory function
def create_crypto_instance(aes_key=None):
    """Create an appropriate crypto instance."""
    if PQC_AVAILABLE and aes_key is None:
        return PQCAESCrypto()
    else:
        return PQCAESCrypto(aes_key) if aes_key else get_fallback_crypto_instance() 