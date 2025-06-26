# chat_client.py - PQC Chat Client with ML-KEM Authentication
import socket
import threading
import sys
import json
import base64
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.pqc_crypto_utils import PQCKeyExchange, PQCAESCrypto, get_fallback_crypto_instance
from key_generation.key_manager import KeyManager

# Client configuration
SERVER_HOST = 'localhost'  # Change this to your server's IP
SERVER_PORT = 12345        # Must match the server's port

class PQCChatClient:
    def __init__(self, client_name, keys_dir="keys", server_host=SERVER_HOST, server_port=SERVER_PORT):
        """Initialize the PQC Chat Client."""
        self.client_name = client_name
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.crypto = None
        self.is_connected = False
        self.receive_thread = None
        
        # Key management
        self.key_manager = KeyManager(keys_dir)
        self.client_public_key = None
        self.client_secret_key = None
        
        # Load or generate client keypair
        self._initialize_client_keys()
        
        print(f"[CLIENT] PQC Chat Client initialized for '{client_name}'")
    
    def _initialize_client_keys(self):
        """Load or generate client keypair."""
        try:
            # Try to load existing client keypair
            public_key, secret_key = self.key_manager.load_client_keypair(self.client_name)
            
            if public_key and secret_key:
                # Verify the keypair
                if self.key_manager.verify_keypair(public_key, secret_key):
                    self.client_public_key = public_key
                    self.client_secret_key = secret_key
                    print(f"[CLIENT] Loaded existing keypair for '{self.client_name}'")
                else:
                    print(f"[CLIENT] Existing keypair verification failed, generating new one...")
                    self._generate_client_keys()
            else:
                print(f"[CLIENT] No existing keypair found, generating new one...")
                self._generate_client_keys()
                
        except Exception as e:
            print(f"[CLIENT] Error initializing keys: {e}")
            raise
    
    def _generate_client_keys(self):
        """Generate new client keypair."""
        try:
            public_key, secret_key = self.key_manager.generate_client_keypair(self.client_name)
            
            if self.key_manager.verify_keypair(public_key, secret_key):
                self.client_public_key = public_key
                self.client_secret_key = secret_key
                print(f"[CLIENT] Successfully generated and verified new keypair")
            else:
                raise RuntimeError("Generated keypair failed verification")
                
        except Exception as e:
            print(f"[CLIENT] Failed to generate client keys: {e}")
            raise
    
    def send_unencrypted(self, message):
        """Send an unencrypted message to the server."""
        try:
            message_bytes = message.encode('utf-8')
            message_length = len(message_bytes)
            self.socket.send(f"{message_length:10}".encode('utf-8'))
            self.socket.send(message_bytes)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send unencrypted message: {e}")
            return False

    def receive_unencrypted(self):
        """Receive an unencrypted message from the server."""
        try:
            # First, receive the length of the message
            length_data = self.socket.recv(10).decode('utf-8').strip()
            if not length_data:
                return None
            
            message_length = int(length_data)
            
            # Then receive the message
            message_bytes = b""
            while len(message_bytes) < message_length:
                chunk = self.socket.recv(message_length - len(message_bytes))
                if not chunk:
                    return None
                message_bytes += chunk
            
            return message_bytes.decode('utf-8')
        except Exception as e:
            print(f"[ERROR] Failed to receive unencrypted message: {e}")
            return None

    def send_encrypted(self, message):
        """Encrypt and send a message to the server."""
        try:
            if not self.crypto:
                print("[ERROR] No crypto instance available for encryption")
                return False
            
            print(f"\n[CLIENTE] 📤 Enviando mensagem criptografada para servidor: '{message}'")
                
            encrypted_message = self.crypto.encrypt(message)
            # Send the length first, then the encrypted message
            message_length = len(encrypted_message.encode('utf-8'))
            self.socket.send(f"{message_length:10}".encode('utf-8'))
            self.socket.send(encrypted_message.encode('utf-8'))
            
            print(f"[CLIENTE] ✅ Mensagem enviada para servidor\n")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send encrypted message: {e}")
            return False

    def receive_encrypted(self):
        """Receive and decrypt a message from the server."""
        try:
            if not self.crypto:
                print("[ERROR] No crypto instance available for decryption")
                return None
                
            # First, receive the length of the encrypted message
            length_data = self.socket.recv(10).decode('utf-8').strip()
            if not length_data:
                return None
            
            message_length = int(length_data)
            
            # Then receive the encrypted message
            encrypted_message = ""
            while len(encrypted_message) < message_length:
                chunk = self.socket.recv(message_length - len(encrypted_message)).decode('utf-8')
                if not chunk:
                    return None
                encrypted_message += chunk
            
            print(f"\n[CLIENTE] 📥 Recebendo mensagem criptografada do servidor")
            
            # Decrypt the message
            decrypted_message = self.crypto.decrypt(encrypted_message)
            
            print(f"[CLIENTE] ✅ Mensagem descriptografada: '{decrypted_message}'\n")
            
            return decrypted_message
        except Exception as e:
            print(f"[ERROR] Failed to receive encrypted message: {e}")
            return None

    def perform_authentication(self):
        """Perform ML-KEM authentication with the server."""
        try:
            print(f"\n[PQC] ═══ INICIANDO AUTENTICAÇÃO ML-KEM COM SERVIDOR ═══")
            
            # Initialize PQC key exchange
            pqc_exchange = PQCKeyExchange()
            
            # Receive server's public key
            print(f"[PQC] 📥 Aguardando chave pública do servidor...")
            response = self.receive_unencrypted()
            if not response:
                print("[PQC] ❌ Falha ao receber chave pública do servidor")
                return None
            
            try:
                server_data = json.loads(response)
                if server_data.get("type") != "server_public_key":
                    print("[PQC] ❌ Tipo de resposta inválido do servidor")
                    return None
                
                server_public_key = base64.b64decode(server_data["public_key"])
                server_id = server_data.get("server_id", "unknown")
                
                print(f"[PQC] ✅ Chave pública recebida do servidor '{server_id}'")
                print(f"[PQC] 🔑 Tamanho: {len(server_public_key)} bytes")
                print(f"[PQC] 🔑 Dados: {server_public_key.hex()[:32]}...{server_public_key.hex()[-8:]}")
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"[PQC] ❌ Falha ao analisar chave pública do servidor: {e}")
                return None
            
            # Encapsulate a shared secret using server's public key
            print(f"[PQC] 🔐 Executando ENCAPSULAMENTO...")
            ciphertext, shared_secret = pqc_exchange.encapsulate(server_public_key)
            if not ciphertext or not shared_secret:
                print("[PQC] ❌ Falha no encapsulamento do segredo compartilhado")
                return None
            
            print("[PQC] ✅ Segredo compartilhado e ciphertext gerados")
            
            # Send ciphertext and client name to server
            print(f"[PQC] 📤 Enviando ciphertext para o servidor...")
            client_message = {
                "type": "client_ciphertext",
                "client_name": self.client_name,
                "ciphertext": base64.b64encode(ciphertext).decode('utf-8')
            }
            
            if not self.send_unencrypted(json.dumps(client_message)):
                print("[PQC] ❌ Falha ao enviar ciphertext para o servidor")
                return None
            
            print("[PQC] ✅ Ciphertext enviado com sucesso")
            
            # Derive AES key from shared secret
            print(f"[PQC] 🔄 Derivando chave AES...")
            aes_key = pqc_exchange.pqc.derive_aes_key(shared_secret)
            
            print(f"[PQC] ✅ AUTENTICAÇÃO CONCLUÍDA COM SUCESSO!")
            print(f"[PQC] 🤝 Segredo compartilhado estabelecido!")
            print(f"[PQC] ═══ FIM DA AUTENTICAÇÃO ═══\n")
            
            # Create crypto instance with the derived AES key
            crypto = PQCAESCrypto(aes_key)
            return crypto
            
        except Exception as e:
            print(f"[PQC] ❌ Falha na autenticação: {e}")
            import traceback
            traceback.print_exc()
            return None

    def receive_messages(self):
        """Receives and prints messages from the server."""
        while self.is_connected:
            try:
                message = self.receive_encrypted()
                if message:
                    print(f"\n{message}")
                    sys.stdout.write("> ") 
                    sys.stdout.flush()
                else:
                    print("[DISCONNECTED] Server disconnected.")
                    self.is_connected = False
                    break
                    
            except OSError:
                # Socket closed, likely by main thread on exit
                break
            except Exception as e:
                print(f"[ERROR] Error receiving message: {e}")
                break

    def send_messages(self):
        """Sends messages typed by the user to the server."""
        while self.is_connected:
            try:
                message = input("> ")
                
                # Send exit command
                if message.lower() == 'exit':
                    if self.send_encrypted(message):
                        self.disconnect()
                    break
                
                # Send encrypted message
                if not self.send_encrypted(message):
                    print("[ERROR] Failed to send message.")
                    break
                    
            except EOFError:
                print("\n[INFO] Exiting chat.")
                self.disconnect()
                break
            except Exception as e:
                print(f"[ERROR] Error sending message: {e}")
                break

    def connect(self):
        """Connect to the server and perform authentication."""
        try:
            print(f"[CONNECTING] Attempting to connect to {self.server_host}:{self.server_port}...")
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            self.is_connected = True
            
            print(f"[CONNECTED] 🔐 Connected to PQC chat server at {self.server_host}:{self.server_port}")
            
            # Perform ML-KEM authentication
            self.crypto = self.perform_authentication()
            
            if self.crypto:
                print("[PQC] Using ML-KEM post-quantum encryption")
            else:
                print("[FALLBACK] ML-KEM failed, using password-based encryption")
                self.crypto = get_fallback_crypto_instance()

            # Start receive thread
            self.receive_thread = threading.Thread(target=self.receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()

            # Show encryption info
            encryption_type = "ML-KEM post-quantum" if isinstance(self.crypto, PQCAESCrypto) else "AES-256 fallback"
            print(f"[INFO] Connected to encrypted chat as '{self.client_name}'. Using {encryption_type} encryption.")
            print("[INFO] Type 'exit' to leave the chat.")

            # Handle sending messages (main thread)
            self.send_messages()

        except ConnectionRefusedError:
            print(f"[ERROR] Connection refused. Is the server running at {self.server_host}:{self.server_port}?")
        except socket.gaierror:
            print(f"[ERROR] Hostname '{self.server_host}' could not be resolved.")
        except Exception as e:
            print(f"[ERROR] An unexpected error occurred: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.disconnect()

    def disconnect(self):
        """Disconnect from the server."""
        self.is_connected = False
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=1)
        
        print("[CLIENT] Disconnected from server.")

def main():
    """Main function to start the client."""
    import argparse
    
    parser = argparse.ArgumentParser(description="PQC Chat Client with ML-KEM Authentication")
    parser.add_argument("client_name", help="Your client name for the chat")
    parser.add_argument("--keys-dir", default="keys", help="Directory containing client keys")
    parser.add_argument("--server", default=SERVER_HOST, help="Server hostname or IP")
    parser.add_argument("--port", type=int, default=SERVER_PORT, help="Server port")
    
    args = parser.parse_args()
    
    # Validate client name
    if not args.client_name.replace('_', '').replace('-', '').isalnum():
        print("[ERROR] Client name must contain only alphanumeric characters, hyphens, and underscores.")
        sys.exit(1)
    
    try:
        # Create and start client
        client = PQCChatClient(args.client_name, args.keys_dir, args.server, args.port)
        client.connect()
        
    except KeyboardInterrupt:
        print("\n[INFO] Chat interrupted by user.")
    except Exception as e:
        print(f"[ERROR] Failed to start client: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 