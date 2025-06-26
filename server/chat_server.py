# chat_server.py - PQC Chat Server with ML-KEM Authentication
import socket
import threading
import json
import base64
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.pqc_crypto_utils import PQCKeyExchange, PQCAESCrypto, get_fallback_crypto_instance
from key_generation.key_manager import KeyManager

# Server configuration
HOST = '0.0.0.0'  # Listen on all available interfaces
PORT = 12345      # Port to listen on

class PQCChatServer:
    def __init__(self, server_id="main_server", keys_dir="keys"):
        """Initialize the PQC Chat Server."""
        self.server_id = server_id
        self.host = HOST
        self.port = PORT
        
        # Client management
        self.clients = []
        self.client_names = {}
        self.client_crypto = {}
        self.client_threads = {}
        
        # Key management
        self.key_manager = KeyManager(keys_dir)
        self.server_public_key = None
        self.server_secret_key = None
        
        # Load or generate server keypair
        self._initialize_server_keys()
        
        print(f"[SERVER] PQC Chat Server initialized with ID: {server_id}")
    
    def _initialize_server_keys(self):
        """Load or generate server keypair."""
        try:
            # Try to load existing server keypair
            public_key, secret_key = self.key_manager.load_server_keypair(self.server_id)
            
            if public_key and secret_key:
                # Verify the keypair
                if self.key_manager.verify_keypair(public_key, secret_key):
                    self.server_public_key = public_key
                    self.server_secret_key = secret_key
                    print(f"[SERVER] Loaded existing server keypair for '{self.server_id}'")
                else:
                    print(f"[SERVER] Existing keypair verification failed, generating new one...")
                    self._generate_server_keys()
            else:
                print(f"[SERVER] No existing keypair found, generating new one...")
                self._generate_server_keys()
                
        except Exception as e:
            print(f"[SERVER] Error initializing keys: {e}")
            raise
    
    def _generate_server_keys(self):
        """Generate new server keypair."""
        try:
            public_key, secret_key = self.key_manager.generate_server_keypair(self.server_id)
            
            if self.key_manager.verify_keypair(public_key, secret_key):
                self.server_public_key = public_key
                self.server_secret_key = secret_key
                print(f"[SERVER] Successfully generated and verified new server keypair")
            else:
                raise RuntimeError("Generated keypair failed verification")
                
        except Exception as e:
            print(f"[SERVER] Failed to generate server keys: {e}")
            raise
    
    def send_unencrypted(self, client_socket, message):
        """Send an unencrypted message to a client."""
        try:
            message_bytes = message.encode('utf-8')
            message_length = len(message_bytes)
            client_socket.send(f"{message_length:10}".encode('utf-8'))
            client_socket.send(message_bytes)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send unencrypted message: {e}")
            return False

    def receive_unencrypted(self, client_socket):
        """Receive an unencrypted message from a client."""
        try:
            # First, receive the length of the message
            length_data = client_socket.recv(10).decode('utf-8').strip()
            if not length_data:
                return None
            
            message_length = int(length_data)
            
            # Then receive the message
            message_bytes = b""
            while len(message_bytes) < message_length:
                chunk = client_socket.recv(message_length - len(message_bytes))
                if not chunk:
                    return None
                message_bytes += chunk
            
            return message_bytes.decode('utf-8')
        except Exception as e:
            print(f"[ERROR] Failed to receive unencrypted message: {e}")
            return None

    def send_encrypted(self, client_socket, message):
        """Encrypt and send a message to a client."""
        try:
            crypto = self.client_crypto.get(client_socket)
            if not crypto:
                print(f"[ERROR] No crypto instance for client")
                return False
            
            client_name = self.client_names.get(client_socket, "Cliente Desconhecido")
            print(f"\n[SERVIDOR] 📤 Enviando mensagem criptografada para '{client_name}': '{message}'")
                
            encrypted_message = crypto.encrypt(message)
            # Send the length first, then the encrypted message
            message_length = len(encrypted_message.encode('utf-8'))
            client_socket.send(f"{message_length:10}".encode('utf-8'))
            client_socket.send(encrypted_message.encode('utf-8'))
            
            print(f"[SERVIDOR] ✅ Mensagem enviada para '{client_name}'\n")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send encrypted message: {e}")
            return False

    def receive_encrypted(self, client_socket):
        """Receive and decrypt a message from a client."""
        try:
            # First, receive the length of the encrypted message
            length_data = client_socket.recv(10).decode('utf-8').strip()
            if not length_data:
                return None
            
            message_length = int(length_data)
            
            # Then receive the encrypted message
            encrypted_message = ""
            while len(encrypted_message) < message_length:
                chunk = client_socket.recv(message_length - len(encrypted_message)).decode('utf-8')
                if not chunk:
                    return None
                encrypted_message += chunk
            
            # Decrypt the message
            crypto = self.client_crypto.get(client_socket)
            if not crypto:
                print(f"[ERROR] No crypto instance for client")
                return None
            
            client_name = self.client_names.get(client_socket, "Cliente Desconhecido")
            print(f"\n[SERVIDOR] 📥 Recebendo mensagem criptografada de '{client_name}'")
                
            decrypted_message = crypto.decrypt(encrypted_message)
            
            print(f"[SERVIDOR] ✅ Mensagem descriptografada de '{client_name}': '{decrypted_message}'\n")
            
            return decrypted_message
        except Exception as e:
            print(f"[ERROR] Failed to receive encrypted message: {e}")
            return None

    def perform_key_exchange(self, client_socket, client_address):
        """Perform ML-KEM key exchange with the client."""
        try:
            print(f"\n[PQC] ═══ INICIANDO TROCA DE CHAVES ML-KEM com {client_address} ═══")
            
            # Initialize PQC key exchange
            pqc_exchange = PQCKeyExchange()
            
            print(f"[PQC] 📤 Enviando chave pública do servidor para {client_address}")
            print(f"[PQC] 🔑 Chave pública do servidor ({len(self.server_public_key)} bytes): {self.server_public_key.hex()[:32]}...{self.server_public_key.hex()[-8:]}")
            
            # Send server public key to client (base64 encoded for transmission)
            key_message = {
                "type": "server_public_key",
                "server_id": self.server_id,
                "public_key": base64.b64encode(self.server_public_key).decode('utf-8')
            }
            
            if not self.send_unencrypted(client_socket, json.dumps(key_message)):
                print(f"[PQC] ❌ Falha ao enviar chave pública para {client_address}")
                return None
            
            print(f"[PQC] ✅ Chave pública enviada para {client_address}")
            
            # Receive client's encapsulated secret
            print(f"[PQC] 📥 Aguardando ciphertext do cliente {client_address}...")
            response = self.receive_unencrypted(client_socket)
            if not response:
                print(f"[PQC] ❌ Falha ao receber resposta do cliente {client_address}")
                return None
            
            try:
                client_data = json.loads(response)
                if client_data.get("type") != "client_ciphertext":
                    print(f"[PQC] ❌ Tipo de resposta inválido de {client_address}")
                    return None
                
                client_ciphertext = base64.b64decode(client_data["ciphertext"])
                client_name = client_data.get("client_name", f"Cliente@{client_address[0]}")
                
                print(f"[PQC] 📦 Ciphertext recebido do cliente '{client_name}':")
                print(f"[PQC] 📦 Tamanho: {len(client_ciphertext)} bytes")
                print(f"[PQC] 📦 Dados: {client_ciphertext.hex()[:32]}...{client_ciphertext.hex()[-8:]}")
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"[PQC] ❌ Falha ao analisar resposta do cliente {client_address}: {e}")
                return None
            
            # Decapsulate the shared secret using server's secret key
            print(f"[PQC] 🔓 Executando DESENCAPSULAMENTO...")
            shared_secret = pqc_exchange.decapsulate(self.server_secret_key, client_ciphertext)
            if not shared_secret:
                print(f"[PQC] ❌ Falha no desencapsulamento com {client_address}")
                return None
            
            # Derive AES key from shared secret
            print(f"[PQC] 🔄 Derivando chave AES...")
            aes_key = pqc_exchange.pqc.derive_aes_key(shared_secret)
            
            print(f"[PQC] ✅ TROCA DE CHAVES CONCLUÍDA com '{client_name}' em {client_address}")
            print(f"[PQC] 🤝 Segredo compartilhado estabelecido com sucesso!")
            print(f"[PQC] ═══ FIM DA TROCA DE CHAVES ═══\n")
            
            # Create crypto instance with the derived AES key
            crypto = PQCAESCrypto(aes_key)
            return crypto, client_name
            
        except Exception as e:
            print(f"[PQC] ❌ Falha na troca de chaves com {client_address}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def broadcast(self, message, sender_socket=None):
        """Sends an encrypted message to all connected clients."""
        for client_socket in self.clients[:]:  # Use slice to avoid issues with list modification
            # Don't send the message back to the sender if a sender_socket is provided
            if client_socket != sender_socket:
                if not self.send_encrypted(client_socket, message):
                    # If sending fails, remove the client
                    self.remove_client(client_socket)

    def handle_client(self, client_socket, client_address):
        """Handles a single client connection."""
        print(f"[NEW CONNECTION] {client_address} connected.")
        
        try:
            # Add the new client to the list
            self.clients.append(client_socket)

            # Perform ML-KEM key exchange FIRST
            auth_result = self.perform_key_exchange(client_socket, client_address)
            
            if auth_result:
                crypto, client_name = auth_result
                print(f"[AUTH] Client authenticated as '{client_name}' using ML-KEM")
                self.client_crypto[client_socket] = crypto
                self.client_names[client_socket] = client_name
            else:
                print(f"[AUTH] ML-KEM authentication failed for {client_address}, using fallback")
                self.client_crypto[client_socket] = get_fallback_crypto_instance()
                self.client_names[client_socket] = f"User@{client_address[0]}:{client_address[1]}"

            name = self.client_names[client_socket]
            
            # Notify other clients
            self.broadcast(f"[SERVER] {name} has joined the chat!", client_socket)
            
            # Send welcome message to the new client
            encryption_type = "ML-KEM post-quantum" if auth_result else "AES-256 fallback"
            self.send_encrypted(client_socket, f"[SERVER] Welcome to the encrypted chat, {name}! Using {encryption_type} encryption.")
            
            # Handle client messages
            while True:
                try:
                    # Receive encrypted message
                    decrypted_message = self.receive_encrypted(client_socket)
                    if decrypted_message:
                        # Check for exit command
                        if decrypted_message.lower().strip() == 'exit':
                            print(f"[EXIT] {name} requested to exit.")
                            self.remove_client(client_socket)
                            break
                        
                        full_message = f"<{name}> {decrypted_message}"
                        print(f"[MESSAGE] {client_address} ({name}): {decrypted_message.strip()}")
                        self.broadcast(full_message, client_socket)
                    else:
                        # If no message, client has disconnected
                        self.remove_client(client_socket)
                        break
                except ConnectionResetError:
                    # Client disconnected abruptly
                    self.remove_client(client_socket)
                    break
                except Exception as e:
                    print(f"[ERROR] Error handling client {client_address}: {e}")
                    self.remove_client(client_socket)
                    break
                    
        except Exception as e:
            print(f"[ERROR] Failed to handle client {client_address}: {e}")
            self.remove_client(client_socket)

    def remove_client(self, client_socket):
        """Removes a client from the list and closes their socket."""
        if client_socket in self.clients:
            try:
                client_address = client_socket.getpeername()
            except:
                client_address = ("unknown", "unknown")
            
            name = self.client_names.get(client_socket, f"UnknownUser@{client_address[0]}:{client_address[1]}")
            self.clients.remove(client_socket)
            
            if client_socket in self.client_names:
                del self.client_names[client_socket]
            if client_socket in self.client_crypto:
                del self.client_crypto[client_socket]
            if client_socket in self.client_threads:
                del self.client_threads[client_socket]
                
            print(f"[DISCONNECTED] {client_address} ({name}) has left.")
            self.broadcast(f"[SERVER] {name} has left the chat.")
            
            try:
                client_socket.close()
            except:
                pass  # Socket might already be closed

    def start(self):
        """Starts the encrypted chat server."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allows reusing the address

        try:
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)  # Listen for up to 5 incoming connections
            print(f"[LISTENING] 🔐 PQC Chat Server is listening on {self.host}:{self.port}")
            print(f"[ENCRYPTION] Using ML-KEM-512 post-quantum cryptography with AES-256 fallback")
            print(f"[SERVER_ID] {self.server_id}")
            print(f"[INFO] Ready for authenticated connections! 🚀")

            while True:
                client_socket, client_address = server_socket.accept()
                # Start a new thread to handle each client
                thread = threading.Thread(target=self.handle_client, args=(client_socket, client_address))
                thread.daemon = True
                thread.start()
                
                # Store thread reference
                self.client_threads[client_socket] = thread
                
                print(f"[ACTIVE CONNECTIONS] {len(self.clients)}")

        except OSError as e:
            if e.errno == 98:  # Address already in use
                print(f"[ERROR] Port {self.port} is already in use. Please choose a different port or ensure no other server is running.")
            else:
                print(f"[ERROR] Server failed to start: {e}")
        except KeyboardInterrupt:
            print(f"\n[SHUTDOWN] Server shutdown requested.")
        except Exception as e:
            print(f"[ERROR] An unexpected error occurred: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Clean shutdown
            print(f"[CLEANUP] Closing all client connections...")
            for client_socket in self.clients[:]:
                self.remove_client(client_socket)
            
            server_socket.close()
            print("[SERVER] Server shut down gracefully.")

def main():
    """Main function to start the server."""
    import argparse
    
    # Declare global variables first
    global HOST, PORT
    
    parser = argparse.ArgumentParser(description="PQC Chat Server with ML-KEM Authentication")
    parser.add_argument("--server-id", default="main_server", help="Server identifier")
    parser.add_argument("--keys-dir", default="keys", help="Directory containing server keys")
    parser.add_argument("--host", default=HOST, help="Host address to bind to")
    parser.add_argument("--port", type=int, default=PORT, help="Port to listen on")
    
    args = parser.parse_args()
    
    try:
        # Override global settings
        HOST = args.host
        PORT = args.port
        
        # Create and start server
        server = PQCChatServer(args.server_id, args.keys_dir)
        server.host = args.host
        server.port = args.port
        server.start()
        
    except Exception as e:
        print(f"[ERROR] Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 