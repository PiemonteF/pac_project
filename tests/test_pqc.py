# test_pqc.py - Test suite for PQC Chat System
import os
import sys
import base64
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from shared.pqc_crypto_utils import PQCKeyExchange, PQCAESCrypto, get_fallback_crypto_instance, PQCProtocol
    from key_generation.key_manager import KeyManager
    PQC_AVAILABLE = True
except ImportError:
    PQC_AVAILABLE = False
    print("[WARNING] PQC library not available for testing")

def test_pqc_import():
    """Test that PQC modules can be imported."""
    print("[TEST] Testing PQC import...")
    try:
        if PQC_AVAILABLE:
            from shared.pqc_wrapper import get_pqc_instance
            pqc = get_pqc_instance()
            lengths = pqc.get_lengths()
            print(f"[OK] PQC imported successfully. Key lengths: {lengths}")
            return True
        else:
            print("[SKIP] PQC not available")
            return True
    except Exception as e:
        print(f"[FAIL] PQC import failed: {e}")
        return False

def test_pqc_functionality():
    """Test basic PQC key exchange functionality."""
    print("[TEST] Testing PQC key exchange...")
    try:
        if not PQC_AVAILABLE:
            print("[SKIP] PQC not available")
            return True
        
        # Initialize key exchange
        pqc_exchange = PQCKeyExchange()
        
        # Generate Alice's keypair
        alice_public, alice_secret = pqc_exchange.generate_keypair()
        if not alice_public or not alice_secret:
            print("[FAIL] Failed to generate Alice's keypair")
            return False
        
        print(f"[OK] Generated Alice's keypair (pub: {len(alice_public)} bytes, sec: {len(alice_secret)} bytes)")
        
        # Bob encapsulates using Alice's public key
        ciphertext, shared_secret1 = pqc_exchange.encapsulate(alice_public)
        if not ciphertext or not shared_secret1:
            print("[FAIL] Failed to encapsulate")
            return False
        
        print(f"[OK] Bob encapsulated (ct: {len(ciphertext)} bytes, ss: {len(shared_secret1)} bytes)")
        
        # Alice decapsulates using her secret key and the ciphertext
        shared_secret2 = pqc_exchange.decapsulate(alice_secret, ciphertext)
        if not shared_secret2:
            print("[FAIL] Failed to decapsulate")
            return False
        
        print(f"[OK] Alice decapsulated (ss: {len(shared_secret2)} bytes)")
        
        # Check if shared secrets match
        if shared_secret1 == shared_secret2:
            print("[OK] Shared secrets match!")
            
            # Test AES key derivation
            aes_key1 = pqc_exchange.pqc.derive_aes_key(shared_secret1)
            aes_key2 = pqc_exchange.pqc.derive_aes_key(shared_secret2)
            
            if aes_key1 == aes_key2 and len(aes_key1) == 32:
                print(f"[OK] AES key derivation successful ({len(aes_key1)} bytes)")
                return True
            else:
                print("[FAIL] AES key derivation failed")
                return False
        else:
            print("[FAIL] Shared secrets don't match!")
            return False
            
    except Exception as e:
        print(f"[FAIL] PQC functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_aes_encryption(aes_key):
    """Test AES encryption/decryption."""
    print("[TEST] Testing AES encryption...")
    try:
        crypto = PQCAESCrypto(aes_key)
        
        # Test messages
        test_messages = [
            "Hello, PQC World!",
            "This is a longer message with special characters: 🔐🚀",
            "Short",
            "A" * 1000,  # Long message
            ""  # Empty message
        ]
        
        for i, message in enumerate(test_messages):
            # Encrypt
            encrypted = crypto.encrypt(message)
            if not encrypted:
                print(f"[FAIL] Failed to encrypt message {i}")
                return False
            
            # Decrypt
            decrypted = crypto.decrypt(encrypted)
            if decrypted != message:
                print(f"[FAIL] Decryption mismatch for message {i}")
                print(f"  Original: {repr(message)}")
                print(f"  Decrypted: {repr(decrypted)}")
                return False
        
        print(f"[OK] All {len(test_messages)} AES encryption tests passed")
        return True
        
    except Exception as e:
        print(f"[FAIL] AES encryption test failed: {e}")
        return False

def test_key_manager():
    """Test the key manager functionality."""
    print("[TEST] Testing Key Manager...")
    try:
        if not PQC_AVAILABLE:
            print("[SKIP] PQC not available")
            return True
        
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            key_manager = KeyManager(temp_dir)
            
            # Test server key generation
            server_pub, server_sec = key_manager.generate_server_keypair("test_server")
            if not server_pub or not server_sec:
                print("[FAIL] Failed to generate server keypair")
                return False
            
            # Test server key loading
            loaded_pub, loaded_sec = key_manager.load_server_keypair("test_server")
            if loaded_pub != server_pub or loaded_sec != server_sec:
                print("[FAIL] Server key loading failed")
                return False
            
            # Test client key generation
            client_pub, client_sec = key_manager.generate_client_keypair("test_client")
            if not client_pub or not client_sec:
                print("[FAIL] Failed to generate client keypair")
                return False
            
            # Test client key loading
            loaded_pub, loaded_sec = key_manager.load_client_keypair("test_client")
            if loaded_pub != client_pub or loaded_sec != client_sec:
                print("[FAIL] Client key loading failed")
                return False
            
            # Test key verification
            if not key_manager.verify_keypair(server_pub, server_sec):
                print("[FAIL] Server keypair verification failed")
                return False
            
            if not key_manager.verify_keypair(client_pub, client_sec):
                print("[FAIL] Client keypair verification failed")
                return False
            
            # Test key listing
            servers = key_manager.list_server_keys()
            clients = key_manager.list_client_keys()
            
            if "test_server" not in servers:
                print("[FAIL] Server not found in list")
                return False
            
            if "test_client" not in clients:
                print("[FAIL] Client not found in list")
                return False
            
            # Test public key export
            exported_pub = key_manager.export_public_key("server", "test_server")
            if not exported_pub:
                print("[FAIL] Failed to export server public key")
                return False
            
            # Verify exported key
            decoded_pub = base64.b64decode(exported_pub)
            if decoded_pub != server_pub:
                print("[FAIL] Exported public key doesn't match")
                return False
        
        print("[OK] All Key Manager tests passed")
        return True
        
    except Exception as e:
        print(f"[FAIL] Key Manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_protocol_messages():
    """Test PQC protocol message handling."""
    print("[TEST] Testing PQC protocol messages...")
    try:
        # Test key exchange request
        public_key_b64 = base64.b64encode(b"fake_public_key").decode('utf-8')
        request = PQCProtocol.create_key_exchange_request(public_key_b64)
        
        parsed = PQCProtocol.parse_message(request)
        if not parsed or parsed.get('type') != 'pqc_key_exchange':
            print("[FAIL] Key exchange request parsing failed")
            return False
        
        if not PQCProtocol.is_pqc_message(request):
            print("[FAIL] PQC message detection failed")
            return False
        
        # Test key exchange response
        ciphertext_b64 = base64.b64encode(b"fake_ciphertext").decode('utf-8')
        response = PQCProtocol.create_key_exchange_response(ciphertext_b64)
        
        parsed = PQCProtocol.parse_message(response)
        if not parsed or parsed.get('type') != 'pqc_key_response':
            print("[FAIL] Key exchange response parsing failed")
            return False
        
        # Test non-PQC message
        normal_message = "Hello, world!"
        if PQCProtocol.is_pqc_message(normal_message):
            print("[FAIL] False positive PQC message detection")
            return False
        
        print("[OK] All protocol message tests passed")
        return True
        
    except Exception as e:
        print(f"[FAIL] Protocol message test failed: {e}")
        return False

def test_fallback_mode():
    """Test fallback encryption mode."""
    print("[TEST] Testing fallback encryption mode...")
    try:
        crypto = get_fallback_crypto_instance()
        
        test_message = "Hello from fallback mode!"
        encrypted = crypto.encrypt(test_message)
        decrypted = crypto.decrypt(encrypted)
        
        if decrypted != test_message:
            print("[FAIL] Fallback encryption/decryption failed")
            return False
        
        print("[OK] Fallback mode test passed")
        return True
        
    except Exception as e:
        print(f"[FAIL] Fallback mode test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("="*60)
    print("PQC CHAT SYSTEM TEST SUITE")
    print("="*60)
    
    tests = [
        test_pqc_import,
        test_pqc_functionality,
        test_fallback_mode,
        test_protocol_messages,
        test_key_manager,
    ]
    
    # Run AES test with derived key if PQC is available
    if PQC_AVAILABLE:
        try:
            pqc_exchange = PQCKeyExchange()
            alice_pub, alice_sec = pqc_exchange.generate_keypair()
            ciphertext, shared_secret = pqc_exchange.encapsulate(alice_pub)
            aes_key = pqc_exchange.pqc.derive_aes_key(shared_secret)
            tests.append(lambda: test_aes_encryption(aes_key))
        except:
            print("[WARNING] Could not set up AES test with PQC key")
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"[ERROR] Test {test.__name__} crashed: {e}")
            failed += 1
        print()
    
    print("="*60)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed == 0:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 