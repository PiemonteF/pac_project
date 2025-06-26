#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
E2E Chat Client - Cliente End-to-End Real
Estabelece criptografia verdadeiramente ponta a ponta com outros clientes.
O servidor atua apenas como roteador.
"""

import socket
import threading
import json
import base64
import sys
import os
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.pqc_crypto_utils import PQCKeyExchange, PQCAESCrypto, get_fallback_crypto_instance
from shared.e2e_crypto_utils import E2EMessageWrapper, E2ESessionManager
from key_generation.key_manager import KeyManager

class E2EChatClient:
    def __init__(self, client_name, keys_dir="keys/clients"):
        """Initialize the E2E Chat Client."""
        self.client_name = client_name
        self.keys_dir = keys_dir
        self.socket = None
        self.connected = False
        self.running = False
        
        # Server communication crypto (for authentication)
        self.server_crypto = None
        self.server_public_key = None
        
        # E2E cryptography
        self.pqc_exchange = PQCKeyExchange()
        
        # E2E session management
        self.session_manager = E2ESessionManager()
        self.online_clients = []
        
        # Key management
        self.key_manager = KeyManager(keys_dir)
        self.public_key = None
        self.secret_key = None
        
        # Load or generate client keypair
        self._initialize_client_keys()
        
        print("=" * 50)
        print(f"🔐 Cliente E2E inicializado: '{client_name}'")
        print("=" * 50)
    
    def _initialize_client_keys(self):
        """Load or generate client keypair."""
        try:
            # Try to load existing client keypair
            public_key, secret_key = self.key_manager.load_client_keypair(self.client_name)
            
            if public_key and secret_key:
                if self.key_manager.verify_keypair(public_key, secret_key):
                    self.public_key = public_key
                    self.secret_key = secret_key
                    print(f"✅ Chaves ML-KEM carregadas")
                else:
                    self._generate_client_keys()
            else:
                self._generate_client_keys()
                
        except Exception as e:
            print(f"[E2E-CLIENT] ❌ Erro ao inicializar chaves: {e}")
            raise
    
    def _generate_client_keys(self):
        """Generate new client keypair."""
        try:
            public_key, secret_key = self.key_manager.generate_client_keypair(self.client_name)
            
            if self.key_manager.verify_keypair(public_key, secret_key):
                self.public_key = public_key
                self.secret_key = secret_key
                print(f"[E2E-CLIENT] ✅ Novas chaves geradas para '{self.client_name}'")
            else:
                raise RuntimeError("Generated keypair failed verification")
                
        except Exception as e:
            print(f"[E2E-CLIENT] ❌ Falha ao gerar chaves: {e}")
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
            length_data = self.socket.recv(10).decode('utf-8').strip()
            if not length_data:
                return None
            
            message_length = int(length_data)
            
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
            if not self.server_crypto:
                print(f"[ERROR] No server crypto instance")
                return False
                
            encrypted_message = self.server_crypto.encrypt(message)
            message_length = len(encrypted_message.encode('utf-8'))
            self.socket.send(f"{message_length:10}".encode('utf-8'))
            self.socket.send(encrypted_message.encode('utf-8'))
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send encrypted message: {e}")
            return False

    def receive_encrypted(self):
        """Receive and decrypt a message from the server."""
        try:
            length_data = self.socket.recv(10).decode('utf-8').strip()
            if not length_data:
                return None
            
            message_length = int(length_data)
            
            encrypted_message = ""
            while len(encrypted_message) < message_length:
                chunk = self.socket.recv(message_length - len(encrypted_message)).decode('utf-8')
                if not chunk:
                    return None
                encrypted_message += chunk
            
            if not self.server_crypto:
                print(f"[ERROR] No server crypto instance")
                return None
                
            decrypted_message = self.server_crypto.decrypt(encrypted_message)
            return decrypted_message
        except Exception as e:
            print(f"[ERROR] Failed to receive encrypted message: {e}")
            return None

    def perform_key_exchange(self):
        """Perform ML-KEM key exchange with server for authentication."""
        try:
            print("\n" + "=" * 40)
            print(f"🔐 Conectando ao servidor...")
            print("=" * 40)
            
            # Receive server public key
            key_message = self.receive_unencrypted()
            if not key_message:
                return False
            
            try:
                server_data = json.loads(key_message)
                if server_data.get("type") != "server_public_key":
                    return False
                
                self.server_public_key = base64.b64decode(server_data["public_key"])
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"[E2E-CLIENT] ❌ Erro ao analisar chave do servidor: {e}")
                return False
            
            # Generate shared secret and ciphertext
            ciphertext, shared_secret = self.pqc_exchange.encapsulate(self.server_public_key)
            if not shared_secret or not ciphertext:
                return False
            
            print(f"✅ ML-KEM estabelecido com servidor")
            print("-" * 40)
            
            # Derive AES key for server communication
            aes_key = self.pqc_exchange.pqc.derive_aes_key(shared_secret)
            
            # Send ciphertext and client info to server
            client_data = {
                "type": "client_ciphertext",
                "client_name": self.client_name,
                "ciphertext": base64.b64encode(ciphertext).decode('utf-8'),
                "client_public_key": base64.b64encode(self.public_key).decode('utf-8')
            }
            
            if not self.send_unencrypted(json.dumps(client_data)):
                return False
            
            # Create crypto instance for server communication
            self.server_crypto = PQCAESCrypto(aes_key)
            
            print(f"[E2E-CLIENT] - Autenticação com servidor completa")
            print(f"[E2E-CLIENT] - Chave AES servidor: {aes_key[:8].hex()}...")
            
            return True
            
        except Exception as e:
            print(f"[E2E-CLIENT] - Falha na autenticação: {e}")
            return False

    def request_public_key(self, target_client):
        """Request another client's public key from the server."""
        try:
            request = {
                "type": "public_key_request",
                "from": self.client_name,
                "to": target_client
            }
            
            self.send_encrypted(json.dumps(request))
            print("\n" + "=" * 45)
            print(f"🔑 Iniciando sessão E2E com '{target_client}'...")
            print("=" * 45)
            return True
            
        except Exception as e:
            print(f"[E2E-CLIENT] - Erro ao solicitar chave pública: {e}")
            return False

    def establish_e2e_session(self, target_client, target_public_key):
        """Establish E2E session with another client."""
        try:
            # Perform ML-KEM encapsulation to generate shared secret
            ciphertext, shared_secret = self.pqc_exchange.encapsulate(target_public_key)
            if not shared_secret:
                print(f"[E2E-CLIENT] - Falha no encapsulamento ML-KEM")
                return False
            
            # Derive AES key from shared secret
            aes_key = self.pqc_exchange.pqc.derive_aes_key(shared_secret)
            
            # Create local session
            from shared.e2e_crypto_utils import E2ESession
            from shared.pqc_crypto_utils import PQCAESCrypto
            from datetime import datetime
            
            session = E2ESession(
                client_a=self.client_name,
                client_b=target_client,
                aes_key=aes_key,
                crypto=PQCAESCrypto(aes_key),
                created_at=datetime.now()
            )
            
            # Store session locally
            session_key = self.session_manager._get_session_key(self.client_name, target_client)
            self.session_manager.sessions[session_key] = session
            
            print(f"✅ SESSÃO E2E ESTABELECIDA: {self.client_name} ↔ {target_client}")
            print("-" * 45)
            
            # Send key exchange to target client so they can create their session
            key_exchange_msg = E2EMessageWrapper.create_key_exchange_request(
                self.client_name,
                target_client,
                ciphertext
            )
            
            self.send_encrypted(json.dumps(key_exchange_msg))
            print(f"[E2E-CLIENT] - Enviando ciphertext para '{target_client}' estabelecer sessão")
            
            return True
                
        except Exception as e:
            print(f"[E2E-CLIENT] - Erro ao estabelecer sessão E2E: {e}")
            return False

    def send_e2e_message(self, target_client, message):
        """Send an E2E encrypted message to another client."""
        try:
            # Check if we have a session with the target
            if not self.session_manager.has_session(self.client_name, target_client):
                print(f"[E2E-CLIENT] -  Sem sessão E2E com '{target_client}'")
                print(f"[E2E-CLIENT] - Solicitando chave pública...")
                
                # Request target's public key first
                self.request_public_key(target_client)
                return False
            
            # Encrypt message for E2E
            encrypted_data = self.session_manager.encrypt_message(
                self.client_name, 
                target_client, 
                message
            )
            
            if encrypted_data:
                # Wrap in E2E message format
                e2e_message = E2EMessageWrapper.create_encrypted_message(
                    self.client_name,
                    target_client,
                    encrypted_data
                )
                
                # Send E2E message via encrypted server channel
                self.send_encrypted(json.dumps(e2e_message))
                
                timestamp = datetime.now().strftime("%H:%M:%S")
                print("\n" + "-" * 50)
                print(f"[{timestamp}] 📤 {self.client_name} → {target_client}: {message}")
                print("-" * 50)
                return True
            else:
                print(f"[E2E-CLIENT] - Falha ao criptografar mensagem")
                return False
                
        except Exception as e:
            print(f"[E2E-CLIENT] - Erro ao enviar mensagem E2E: {e}")
            return False

    def handle_e2e_message(self, message_data):
        """Handle incoming E2E message."""
        try:
            if message_data.get("type") == "public_key_response":
                # Received someone's public key
                target_client = message_data.get("from")
                target_public_key = base64.b64decode(message_data["public_key"])
                
                print(f"[E2E-CLIENT] - Chave pública recebida de '{target_client}'")
                
                # Establish E2E session
                self.establish_e2e_session(target_client, target_public_key)
                
            elif message_data.get("type") == "e2e_key_exchange":
                # Received key exchange from another client
                sender = message_data.get("from")
                ciphertext = base64.b64decode(message_data["ciphertext"])
                
                print(f"[E2E-CLIENT] - Recebido key exchange de '{sender}'")
                
                # Decapsulate to get shared secret
                shared_secret = self.pqc_exchange.decapsulate(self.secret_key, ciphertext)
                if shared_secret:
                    # Derive AES key from shared secret
                    aes_key = self.pqc_exchange.pqc.derive_aes_key(shared_secret)
                    
                    # Create local session
                    from shared.e2e_crypto_utils import E2ESession
                    from shared.pqc_crypto_utils import PQCAESCrypto
                    
                    session = E2ESession(
                        client_a=self.client_name,
                        client_b=sender,
                        aes_key=aes_key,
                        crypto=PQCAESCrypto(aes_key),
                        created_at=datetime.now()
                    )
                    
                    # Store session locally
                    session_key = self.session_manager._get_session_key(self.client_name, sender)
                    self.session_manager.sessions[session_key] = session
                    
                    print(f"✅ SESSÃO E2E ESTABELECIDA: {self.client_name} ↔ {sender}")
                    print("-" * 45)
                else:
                    print(f"[E2E-CLIENT] - Falha ao desencapsular chave de '{sender}'")
                
            elif message_data.get("type") == "e2e_encrypted_message":
                # Received encrypted E2E message
                sender = message_data.get("from")
                encrypted_data = message_data.get("encrypted_data")
                
                # Decrypt the message
                decrypted_message = self.session_manager.decrypt_message(
                    sender,
                    self.client_name,
                    encrypted_data
                )
                
                if decrypted_message:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print("\n" + "-" * 50)
                    print(f"[{timestamp}] 📥 {sender} → {self.client_name}: {decrypted_message}")
                    print("-" * 50)
                else:
                    print(f"❌ Falha ao descriptografar mensagem de '{sender}'")
                    
            elif message_data.get("type") == "key_error":
                print(f"[E2E-CLIENT] - {message_data.get('message', 'Erro de chave')}")
                
            elif message_data.get("type") == "routing_error":
                print(f"[E2E-CLIENT] - {message_data.get('message', 'Erro de roteamento')}")
                
        except Exception as e:
            print(f"[E2E-CLIENT] - Erro ao processar mensagem E2E: {e}")

    def handle_server_message(self, message_data):
        """Handle server-specific messages."""
        try:
            message_type = message_data.get("type", "")
            
            if message_type == "server_message":
                print(f"[SERVIDOR] 📢 {message_data.get('message', '')}")
                
            elif message_type == "client_list":
                self.online_clients = message_data.get("clients", [])
                print("\n" + "=" * 30)
                print(f"📋 Clientes online: {', '.join(self.online_clients)}")
                print("=" * 30)
                
        except Exception as e:
            print(f"[E2E-CLIENT] - Erro ao processar mensagem do servidor: {e}")

    def handle_incoming_messages(self):
        """Handle incoming messages from server."""
        while self.running:
            try:
                decrypted_message = self.receive_encrypted()
                if decrypted_message:
                    try:
                        message_data = json.loads(decrypted_message)
                        
                        if E2EMessageWrapper.is_e2e_message(message_data):
                            self.handle_e2e_message(message_data)
                        else:
                            self.handle_server_message(message_data)
                            
                    except json.JSONDecodeError:
                        print(f"[E2E-CLIENT] - Mensagem JSON inválida recebida")
                else:
                    print(f"🔌 Conexão perdida")
                    self.connected = False
                    break
                    
            except Exception as e:
                print(f"[E2E-CLIENT] - Erro ao receber mensagem: {e}")
                self.connected = False
                break

    def connect(self, host='localhost', port=12346):
        """Connect to the E2E chat server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.connected = True
            
            print(f"[E2E-CLIENT] 🔌 Conectado ao servidor {host}:{port}")
            
            # Perform key exchange with server
            if self.perform_key_exchange():
                self.running = True
                
                # Start message handling thread
                receive_thread = threading.Thread(target=self.handle_incoming_messages)
                receive_thread.daemon = True
                receive_thread.start()
                
                return True
            else:
                print(f"[E2E-CLIENT] - Falha na autenticação")
                self.disconnect()
                return False
                
        except Exception as e:
            print(f"[E2E-CLIENT] - Falha na conexão: {e}")
            return False

    def disconnect(self):
        """Disconnect from the server."""
        self.running = False
        self.connected = False
        
        if self.socket:
            try:
                # Send exit message
                exit_msg = {"type": "exit"}
                self.send_encrypted(json.dumps(exit_msg))
                
                time.sleep(0.1)  # Give time for message to be sent
                self.socket.close()
            except:
                pass
        
        print(f"[E2E-CLIENT] - Desconectado do servidor")

    def start_chat(self):
        """Start the interactive chat interface."""
        if not self.connected:
            print(f"[E2E-CLIENT] - Não conectado ao servidor")
            return
        
        print(f"\n=== - CHAT E2E - {self.client_name} ===")
        print(f" -  Criptografia verdadeiramente ponta a ponta")
        print(f" - Servidor atua apenas como roteador")
        print(f" - Digite '/help' para comandos")
        print(f"=" * 50)
        
        try:
            while self.running and self.connected:
                user_input = input().strip()
                
                if not user_input:
                    continue
                
                if user_input.startswith('/'):
                    self.handle_command(user_input)
                else:
                    # Parse message format: @target message
                    if user_input.startswith('@'):
                        try:
                            parts = user_input[1:].split(' ', 1)
                            if len(parts) >= 2:
                                target_client = parts[0]
                                message = parts[1]
                                self.send_e2e_message(target_client, message)
                            else:
                                print("Formato Correto: @cliente mensagem")
                        except Exception as e:
                            print(f"Erro: {e}")
                    else:
                        print("💡 Para enviar mensagem: @cliente sua_mensagem")
                        print("💡 Digite '/help' para mais comandos")
                        
        except KeyboardInterrupt:
            print(f"\n[E2E-CLIENT] - Chat interrompido")
        except EOFError:
            print(f"\n[E2E-CLIENT] - EOF recebido")
        finally:
            self.disconnect()

    def handle_command(self, command):
        """Handle chat commands."""
        cmd_parts = command[1:].split()
        if not cmd_parts:
            return
        
        cmd = cmd_parts[0].lower()
        
        if cmd == 'help':
            print("\n=== COMANDOS E2E ===")
            print("@cliente mensagem  - Enviar mensagem E2E")
            print("/list             - Listar clientes online")
            print("/sessions         - Mostrar sessões E2E ativas")
            print("/key cliente      - Solicitar chave pública")
            print("/exit             - Sair do chat")
            print("==================")
            
        elif cmd == 'list':
            if self.online_clients:
                print(f"- Clientes online: {', '.join(self.online_clients)}")
            else:
                print("- Nenhum cliente online")
                
        elif cmd == 'sessions':
            sessions = self.session_manager.list_sessions()
            if sessions:
                print("- Sessões E2E ativas:")
                for session in sessions:
                    print(f"  • {session}")
            else:
                print("- Nenhuma sessão E2E ativa")
                
        elif cmd == 'key' and len(cmd_parts) > 1:
            target_client = cmd_parts[1]
            self.request_public_key(target_client)
            
        elif cmd == 'exit':
            print("- Saindo do chat E2E...")
            self.running = False
            
        else:
            print(f"❌ Comando desconhecido: {command}")

def main():
    """Main function to start the E2E client."""
    import argparse
    
    parser = argparse.ArgumentParser(description="E2E Chat Client - End-to-End Encryption")
    parser.add_argument("--name", default="alice", help="Client name")
    parser.add_argument("--server", default="localhost", help="Server address")
    parser.add_argument("--port", type=int, default=12346, help="Server port")
    parser.add_argument("--keys-dir", default="keys/clients", help="Directory for client keys")
    
    args = parser.parse_args()
    
    try:
        client = E2EChatClient(args.name, args.keys_dir)
        
        if client.connect(args.server, args.port):
            client.start_chat()
        else:
            print(f"[ERROR] Falha ao conectar ao servidor")
            
    except Exception as e:
        print(f"[ERROR] Falha ao iniciar cliente E2E: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 