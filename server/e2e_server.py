#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
E2E Chat Server - Servidor End-to-End Real
Atua apenas como roteador de mensagens, SEM descriptografar o conteúdo.
Permite criptografia verdadeiramente ponta a ponta entre clientes.
"""

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
from shared.e2e_crypto_utils import E2EMessageWrapper
from key_generation.key_manager import KeyManager

# Server configuration
HOST = '0.0.0.0'
PORT = 12346  # Porta diferente para E2E server

class E2EChatServer:
    def __init__(self, server_id="e2e_server", keys_dir="keys"):
        """Initialize the E2E Chat Server (Router only)."""
        self.server_id = server_id
        self.host = HOST
        self.port = PORT
        
        # Client management
        self.clients = []
        self.client_names = {}
        self.client_crypto = {}  # Para comunicação servidor-cliente
        self.client_public_keys = {}  # Chaves públicas dos clientes para E2E
        self.client_threads = {}
        
        # Key management (para autenticação servidor-cliente)
        self.key_manager = KeyManager(keys_dir)
        self.server_public_key = None
        self.server_secret_key = None
        
        # Load or generate server keypair
        self._initialize_server_keys()
        
        print("=" * 50)
        print(f"🔐 E2E Chat Server iniciado - ID: {server_id}")
        print(f"🛡️  SERVIDOR = ROTEADOR (não lê mensagens E2E)")
        print("=" * 50)
    
    def _initialize_server_keys(self):
        """Load or generate server keypair for client authentication."""
        try:
            # Try to load existing server keypair
            public_key, secret_key = self.key_manager.load_server_keypair(self.server_id)
            
            if public_key and secret_key:
                if self.key_manager.verify_keypair(public_key, secret_key):
                    self.server_public_key = public_key
                    self.server_secret_key = secret_key
                    print(f"✅ Chaves ML-KEM do servidor carregadas")
                else:
                    self._generate_server_keys()
            else:
                self._generate_server_keys()
                
        except Exception as e:
            print(f"[E2E-SERVER] ❌ Erro ao inicializar chaves: {e}")
            raise
    
    def _generate_server_keys(self):
        """Generate new server keypair."""
        try:
            public_key, secret_key = self.key_manager.generate_server_keypair(self.server_id)
            
            if self.key_manager.verify_keypair(public_key, secret_key):
                self.server_public_key = public_key
                self.server_secret_key = secret_key
                print(f"[E2E-SERVER] ✅ Novas chaves do servidor geradas")
            else:
                raise RuntimeError("Generated keypair failed verification")
                
        except Exception as e:
            print(f"[E2E-SERVER] ❌ Falha ao gerar chaves: {e}")
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
            length_data = client_socket.recv(10).decode('utf-8').strip()
            if not length_data:
                return None
            
            message_length = int(length_data)
            
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
        """Encrypt and send a message to a client (for server-client communication)."""
        try:
            crypto = self.client_crypto.get(client_socket)
            if not crypto:
                print(f"[ERROR] No crypto instance for client")
                return False
                
            encrypted_message = crypto.encrypt(message)
            message_length = len(encrypted_message.encode('utf-8'))
            client_socket.send(f"{message_length:10}".encode('utf-8'))
            client_socket.send(encrypted_message.encode('utf-8'))
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send encrypted message: {e}")
            return False

    def receive_encrypted(self, client_socket):
        """Receive and decrypt a message from a client (for server-client communication)."""
        try:
            length_data = client_socket.recv(10).decode('utf-8').strip()
            if not length_data:
                return None
            
            message_length = int(length_data)
            
            encrypted_message = ""
            while len(encrypted_message) < message_length:
                chunk = client_socket.recv(message_length - len(encrypted_message)).decode('utf-8')
                if not chunk:
                    return None
                encrypted_message += chunk
            
            crypto = self.client_crypto.get(client_socket)
            if not crypto:
                print(f"[ERROR] No crypto instance for client")
                return None
                
            decrypted_message = crypto.decrypt(encrypted_message)
            return decrypted_message
        except Exception as e:
            print(f"[ERROR] Failed to receive encrypted message: {e}")
            return None

    def perform_key_exchange(self, client_socket, client_address):
        """Perform ML-KEM key exchange with client for server-client communication."""
        try:
            print("\n" + "=" * 40)
            print(f"🔐 NOVA CONEXÃO: {client_address[0]}")
            print("=" * 40)
            
            pqc_exchange = PQCKeyExchange()
            
            # Send server public key
            key_message = {
                "type": "server_public_key",
                "server_id": self.server_id,
                "public_key": base64.b64encode(self.server_public_key).decode('utf-8')
            }
            
            if not self.send_unencrypted(client_socket, json.dumps(key_message)):
                return None
            
            # Receive client's ciphertext
            response = self.receive_unencrypted(client_socket)
            if not response:
                return None
            
            try:
                client_data = json.loads(response)
                if client_data.get("type") != "client_ciphertext":
                    return None
                
                client_ciphertext = base64.b64decode(client_data["ciphertext"])
                client_name = client_data.get("client_name", f"Cliente@{client_address[0]}")
                
                # Também recebe chave pública do cliente para E2E
                if "client_public_key" in client_data:
                    client_public_key = base64.b64decode(client_data["client_public_key"])
                    self.client_public_keys[client_name] = client_public_key
                    print(f"📋 Chave pública E2E registrada: '{client_name}'")
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"[E2E-SERVER] ❌ Erro ao analisar resposta: {e}")
                return None
            
            # Decapsulate shared secret
            shared_secret = pqc_exchange.decapsulate(self.server_secret_key, client_ciphertext)
            if not shared_secret:
                return None
            
            # Derive AES key for server-client communication
            aes_key = pqc_exchange.pqc.derive_aes_key(shared_secret)
            
            print(f"✅ ML-KEM ESTABELECIDO: '{client_name}' autenticado")
            print("-" * 40)
            
            crypto = PQCAESCrypto(aes_key)
            return crypto, client_name
            
        except Exception as e:
            print(f"[E2E-SERVER] ❌ Falha na autenticação: {e}")
            return None

    def route_e2e_message(self, message_data, sender_socket):
        """Route E2E message to target client without decrypting."""
        try:
            target_client = message_data.get("to")
            sender_client = message_data.get("from")
            message_type = message_data.get("type")
            
            if message_type == "e2e_encrypted_message":
                encrypted_data = message_data.get("encrypted_data", "")
                print("\n" + "-" * 50)
                print(f"📮 MENSAGEM E2E: {sender_client} → {target_client}")
                print(f"🔒 Dados criptografados: {encrypted_data[:32]}...")
                print("🛡️  SERVIDOR NÃO PODE LER O CONTEÚDO!")
                print("-" * 50)
            else:
                print(f"\n📮 ROTEANDO: {sender_client} → {target_client} ({message_type})")
            
            # Find target client socket
            target_socket = None
            for client_socket in self.clients:
                if self.client_names.get(client_socket) == target_client:
                    target_socket = client_socket
                    break
            
            if target_socket:
                # Forward the E2E message via encrypted server channel
                if self.send_encrypted(target_socket, json.dumps(message_data)):
                    print(f"✅ Mensagem roteada para '{target_client}'")
                    return True
                else:
                    print(f"❌ Falha ao rotear para '{target_client}'")
                    return False
            else:
                print(f"❌ Cliente '{target_client}' não encontrado")
                # Send error back to sender
                error_msg = {
                    "type": "routing_error",
                    "message": f"Cliente '{target_client}' não está online"
                }
                self.send_encrypted(sender_socket, json.dumps(error_msg))
                return False
                
        except Exception as e:
            print(f"[E2E-ROUTER] ❌ Erro no roteamento: {e}")
            return False

    def broadcast_client_list(self):
        """Broadcast list of online clients to all clients."""
        client_list = {
            "type": "client_list",
            "clients": list(self.client_names.values())
        }
        
        for client_socket in self.clients[:]:
            self.send_encrypted(client_socket, json.dumps(client_list))

    def handle_public_key_request(self, request_data, requester_socket):
        """Handle request for another client's public key."""
        target_client = request_data.get("to")
        requester_client = request_data.get("from")
        
        print("\n" + "=" * 45)
        print(f"🔑 SESSÃO E2E INICIADA: '{requester_client}' ↔ '{target_client}'")
        print("=" * 45)
        
        if target_client in self.client_public_keys:
            # Send public key to requester
            response = {
                "type": "public_key_response",
                "from": target_client,
                "to": requester_client,
                "public_key": base64.b64encode(self.client_public_keys[target_client]).decode('utf-8')
            }
            
            self.send_encrypted(requester_socket, json.dumps(response))
            print(f"✅ Chave pública enviada: '{target_client}' → '{requester_client}'")
        else:
            error_msg = {
                "type": "key_error",
                "message": f"Chave pública de '{target_client}' não disponível"
            }
            self.send_encrypted(requester_socket, json.dumps(error_msg))
            print(f"❌ Chave pública de '{target_client}' não encontrada")

    def handle_client(self, client_socket, client_address):
        """Handle a single client connection."""
        print(f"🔌 Nova conexão: {client_address[0]}")
        
        try:
            self.clients.append(client_socket)

            # Perform authentication
            auth_result = self.perform_key_exchange(client_socket, client_address)
            
            if auth_result:
                crypto, client_name = auth_result
                self.client_crypto[client_socket] = crypto
                self.client_names[client_socket] = client_name
                
                print(f"✅ '{client_name}' conectado e autenticado")
                
                # Send welcome message
                welcome_msg = {
                    "type": "server_message",
                    "message": f"Bem-vindo ao chat E2E, {client_name}! Suas mensagens são criptografadas ponta a ponta."
                }
                self.send_encrypted(client_socket, json.dumps(welcome_msg))
                
                # Broadcast updated client list
                self.broadcast_client_list()
                
            else:
                print(f"[E2E-SERVER] ❌ Falha na autenticação de {client_address}")
                self.remove_client(client_socket)
                return

            # Handle client messages
            while True:
                try:
                    decrypted_message = self.receive_encrypted(client_socket)
                    if decrypted_message:
                        try:
                            message_data = json.loads(decrypted_message)
                            message_type = message_data.get("type", "")
                            
                            if message_type == "exit":
                                print(f"👋 '{client_name}' desconectou")
                                self.remove_client(client_socket)
                                break
                            elif E2EMessageWrapper.is_e2e_message(message_data):
                                # Route E2E message (content is E2E encrypted)
                                if message_type == "public_key_request":
                                    self.handle_public_key_request(message_data, client_socket)
                                else:
                                    self.route_e2e_message(message_data, client_socket)
                            else:
                                print(f"[E2E-SERVER] ⚠️  Tipo de mensagem desconhecido: {message_type}")
                                
                        except json.JSONDecodeError:
                            print(f"[E2E-SERVER] ❌ Mensagem JSON inválida de '{client_name}'")
                    else:
                        self.remove_client(client_socket)
                        break
                        
                except ConnectionResetError:
                    self.remove_client(client_socket)
                    break
                except Exception as e:
                    print(f"[E2E-SERVER] ❌ Erro com cliente {client_address}: {e}")
                    self.remove_client(client_socket)
                    break
                    
        except Exception as e:
            print(f"[E2E-SERVER] ❌ Falha ao lidar com cliente {client_address}: {e}")
            self.remove_client(client_socket)

    def remove_client(self, client_socket):
        """Remove a client from the server."""
        if client_socket in self.clients:
            try:
                client_address = client_socket.getpeername()
            except:
                client_address = ("unknown", "unknown")
            
            name = self.client_names.get(client_socket, f"Cliente@{client_address[0]}")
            self.clients.remove(client_socket)
            
            # Clean up client data
            if client_socket in self.client_names:
                del self.client_names[client_socket]
            if client_socket in self.client_crypto:
                del self.client_crypto[client_socket]
            if client_socket in self.client_threads:
                del self.client_threads[client_socket]
            if name in self.client_public_keys:
                del self.client_public_keys[name]
                
            print(f"[E2E-SERVER] '{name}' desconectou")
            
            # Broadcast updated client list
            self.broadcast_client_list()
            
            try:
                client_socket.close()
            except:
                pass

    def start(self):
        """Start the E2E chat server."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            
            print(f"\n🚀 Servidor E2E rodando em {self.host}:{self.port}")
            print(f"✅ Pronto para conexões!")
            print("=" * 50)
            print("")

            while True:
                client_socket, client_address = server_socket.accept()
                thread = threading.Thread(target=self.handle_client, args=(client_socket, client_address))
                thread.daemon = True
                thread.start()
                
                self.client_threads[client_socket] = thread
                print(f"[E2E-SERVER] - Conexões ativas: {len(self.clients)}")

        except OSError as e:
            if e.errno == 98:
                print(f"[ERROR] Porta {self.port} já está em uso.")
            else:
                print(f"[ERROR] Falha ao iniciar servidor: {e}")
        except KeyboardInterrupt:
            print(f"\n[E2E-SERVER] - Shutdown solicitado")
        except Exception as e:
            print(f"[ERROR] Erro inesperado: {e}")
        finally:
            print(f"[E2E-SERVER] 🧹 Limpando conexões...")
            for client_socket in self.clients[:]:
                self.remove_client(client_socket)
            
            server_socket.close()
            print("[E2E-SERVER] - Servidor encerrado")

def main():
    """Main function to start the E2E server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="E2E Chat Server - End-to-End Encryption")
    parser.add_argument("--server-id", default="e2e_server", help="Server identifier")
    parser.add_argument("--keys-dir", default="keys", help="Directory containing server keys")
    parser.add_argument("--host", default=HOST, help="Host address to bind to")
    parser.add_argument("--port", type=int, default=PORT, help="Port to listen on")
    
    args = parser.parse_args()
    
    try:
        server = E2EChatServer(args.server_id, args.keys_dir)
        server.host = args.host
        server.port = args.port
        server.start()
        
    except Exception as e:
        print(f"[ERROR] Falha ao iniciar servidor E2E: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 