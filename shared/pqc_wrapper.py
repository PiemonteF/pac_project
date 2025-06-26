# pqc_wrapper.py
import ctypes
import os
import sys
from ctypes import Structure, POINTER, c_uint8, c_size_t, c_int, c_char_p
import hashlib

# Define C structures
class KeyPair(Structure):
    _fields_ = [
        ("public_key", POINTER(c_uint8)),
        ("secret_key", POINTER(c_uint8)),
        ("public_key_len", c_size_t),
        ("secret_key_len", c_size_t)
    ]

class EncapsResult(Structure):
    _fields_ = [
        ("ciphertext", POINTER(c_uint8)),
        ("shared_secret", POINTER(c_uint8)),
        ("ciphertext_len", c_size_t),
        ("shared_secret_len", c_size_t)
    ]

class PQCWrapper:
    def __init__(self, library_path=None):
        """Initialize the PQC wrapper with the compiled library."""
        self.lib = None
        self.is_initialized = False
        
        try:
            # Get the directory of this script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)  # Go up one level from shared/
            
            # Try different possible library names/paths
            possible_paths = [
                library_path,
                os.path.join(project_root, "libpqc_kem.so"),
                os.path.join(project_root, "libpqc_kem.dylib"),  # macOS
                os.path.join(project_root, "pqc_kem.dll"),       # Windows
                "./libpqc_kem.so",
                "./libpqc_kem.dylib",
                "./pqc_kem.dll",
                "libpqc_kem.so",
                "libpqc_kem.dylib",
                "pqc_kem.dll"
            ]
            
            for path in possible_paths:
                if path is None:
                    continue
                try:
                    self.lib = ctypes.CDLL(path)
                    print(f"[PQC] Loaded library from: {path}")
                    break
                except OSError:
                    continue
            
            if self.lib is None:
                raise OSError("Could not load PQC library. Please compile pqc_kem.cpp first using 'make'.")
            
            self._setup_function_signatures()
            
            # Initialize the library
            if self.lib.pqc_init() == 0:
                self.is_initialized = True
                print("[PQC] Post-quantum cryptography initialized successfully")
            else:
                raise RuntimeError("Failed to initialize PQC library")
                
        except Exception as e:
            print(f"[PQC] Error initializing: {e}")
            raise
    
    def _setup_function_signatures(self):
        """Set up function signatures for proper ctypes usage."""
        # pqc_init
        self.lib.pqc_init.restype = c_int
        
        # pqc_generate_keypair
        self.lib.pqc_generate_keypair.restype = POINTER(KeyPair)
        
        # pqc_encapsulate
        self.lib.pqc_encapsulate.argtypes = [POINTER(c_uint8), c_size_t]
        self.lib.pqc_encapsulate.restype = POINTER(EncapsResult)
        
        # pqc_decapsulate
        self.lib.pqc_decapsulate.argtypes = [
            POINTER(c_uint8), c_size_t,  # secret_key, secret_key_len
            POINTER(c_uint8), c_size_t,  # ciphertext, ciphertext_len
            POINTER(c_uint8)             # shared_secret (output)
        ]
        self.lib.pqc_decapsulate.restype = c_int
        
        # Length functions
        self.lib.pqc_get_public_key_length.restype = c_size_t
        self.lib.pqc_get_secret_key_length.restype = c_size_t
        self.lib.pqc_get_ciphertext_length.restype = c_size_t
        self.lib.pqc_get_shared_secret_length.restype = c_size_t
        
        # Free functions
        self.lib.pqc_free_keypair.argtypes = [POINTER(KeyPair)]
        self.lib.pqc_free_encaps_result.argtypes = [POINTER(EncapsResult)]
        
        # Cleanup
        self.lib.pqc_cleanup.restype = None
    
    def generate_keypair(self):
        """Generate a new ML-KEM key pair."""
        if not self.is_initialized:
            raise RuntimeError("PQC library not initialized")
        
        keypair_ptr = self.lib.pqc_generate_keypair()
        if not keypair_ptr:
            raise RuntimeError("Failed to generate key pair")
        
        keypair = keypair_ptr.contents
        
        # Copy data to Python bytes
        public_key = ctypes.string_at(keypair.public_key, keypair.public_key_len)
        secret_key = ctypes.string_at(keypair.secret_key, keypair.secret_key_len)
        
        # Free the C structure
        self.lib.pqc_free_keypair(keypair_ptr)
        
        return public_key, secret_key
    
    def encapsulate(self, public_key):
        """Encapsulate a shared secret using the given public key."""
        if not self.is_initialized:
            raise RuntimeError("PQC library not initialized")
        
        # Convert Python bytes to C array
        public_key_array = (c_uint8 * len(public_key)).from_buffer_copy(public_key)
        
        result_ptr = self.lib.pqc_encapsulate(public_key_array, len(public_key))
        if not result_ptr:
            raise RuntimeError("Failed to encapsulate")
        
        result = result_ptr.contents
        
        # Copy data to Python bytes
        ciphertext = ctypes.string_at(result.ciphertext, result.ciphertext_len)
        shared_secret = ctypes.string_at(result.shared_secret, result.shared_secret_len)
        
        # Free the C structure
        self.lib.pqc_free_encaps_result(result_ptr)
        
        return ciphertext, shared_secret
    
    def decapsulate(self, secret_key, ciphertext):
        """Decapsulate the shared secret using the secret key and ciphertext."""
        if not self.is_initialized:
            raise RuntimeError("PQC library not initialized")
        
        # Get shared secret length
        shared_secret_len = self.lib.pqc_get_shared_secret_length()
        shared_secret_array = (c_uint8 * shared_secret_len)()
        
        # Convert Python bytes to C arrays
        secret_key_array = (c_uint8 * len(secret_key)).from_buffer_copy(secret_key)
        ciphertext_array = (c_uint8 * len(ciphertext)).from_buffer_copy(ciphertext)
        
        result = self.lib.pqc_decapsulate(
            secret_key_array, len(secret_key),
            ciphertext_array, len(ciphertext),
            shared_secret_array
        )
        
        if result != 0:
            raise RuntimeError("Failed to decapsulate")
        
        # Convert C array back to Python bytes
        shared_secret = bytes(shared_secret_array)
        
        return shared_secret
    
    def get_lengths(self):
        """Get the lengths of various components."""
        return {
            'public_key': self.lib.pqc_get_public_key_length(),
            'secret_key': self.lib.pqc_get_secret_key_length(),
            'ciphertext': self.lib.pqc_get_ciphertext_length(),
            'shared_secret': self.lib.pqc_get_shared_secret_length()
        }
    
    def derive_aes_key(self, shared_secret):
        """Derive a 32-byte AES key from the shared secret using SHA-256."""
        print(f"[AES-DERIVE] 🔄 Derivando chave AES a partir do segredo compartilhado")
        print(f"[AES-DERIVE] 📊 Segredo compartilhado (32 bytes): {shared_secret.hex()}")
        
        aes_key = hashlib.sha256(shared_secret).digest()
        
        print(f"[AES-DERIVE] ✅ Chave AES-256 derivada com SHA-256 (32 bytes): {aes_key.hex()}")
        
        return aes_key
    
    def __del__(self):
        """Cleanup when the object is destroyed."""
        if hasattr(self, 'lib') and self.lib and self.is_initialized:
            self.lib.pqc_cleanup()

# Global instance
_pqc_instance = None

def get_pqc_instance():
    """Get a global PQC instance (singleton pattern)."""
    global _pqc_instance
    if _pqc_instance is None:
        _pqc_instance = PQCWrapper()
    return _pqc_instance 