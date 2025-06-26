#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Demo do Processo PQC Chat - Demonstração Completa
Mostra passo a passo como funciona a troca de chaves ML-KEM e criptografia AES
"""

import sys
import os
import time
import json
import base64

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.pqc_crypto_utils import PQCKeyExchange, PQCAESCrypto

def print_separator(title):
    """Imprime um separador visual"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_step(step, description):
    """Imprime um passo numerado"""
    print(f"\n🔹 PASSO {step}: {description}")
    print("-" * 50)

def demo_key_generation():
    """Demonstra a geração de chaves"""
    print_separator("1. GERAÇÃO DE CHAVES ML-KEM-512")
    
    print("🔧 Inicializando sistema PQC...")
    pqc = PQCKeyExchange()
    
    print_step("1.1", "Servidor gera par de chaves")
    server_public_key, server_secret_key = pqc.generate_keypair()
    
    print_step("1.2", "Cliente gera par de chaves")
    client_public_key, client_secret_key = pqc.generate_keypair()
    
    return pqc, server_public_key, server_secret_key, client_public_key, client_secret_key

def demo_key_exchange(pqc, server_public_key, server_secret_key):
    """Demonstra a troca de chaves"""
    print_separator("2. TROCA DE CHAVES ML-KEM")
    
    print_step("2.1", "Servidor envia chave pública para cliente")
    key_message = {
        "type": "server_public_key",
        "server_id": "demo_server",
        "public_key": base64.b64encode(server_public_key).decode('utf-8')
    }
    
    print(f"📤 Mensagem enviada:")
    print(f"   Tipo: {key_message['type']}")
    print(f"   Server ID: {key_message['server_id']}")
    print(f"   Chave pública (base64): {key_message['public_key'][:50]}...")
    
    print_step("2.2", "Cliente recebe e decodifica chave pública")
    received_public_key = base64.b64decode(key_message["public_key"])
    print(f"✅ Chave pública decodificada: {len(received_public_key)} bytes")
    
    print_step("2.3", "Cliente executa ENCAPSULAMENTO")
    ciphertext, shared_secret_client = pqc.encapsulate(received_public_key)
    
    print_step("2.4", "Cliente envia ciphertext para servidor")
    client_message = {
        "type": "client_ciphertext",
        "client_name": "demo_alice",
        "ciphertext": base64.b64encode(ciphertext).decode('utf-8')
    }
    
    print(f"📤 Mensagem enviada:")
    print(f"   Tipo: {client_message['type']}")
    print(f"   Cliente: {client_message['client_name']}")
    print(f"   Ciphertext (base64): {client_message['ciphertext'][:50]}...")
    
    print_step("2.5", "Servidor executa DESENCAPSULAMENTO")
    received_ciphertext = base64.b64decode(client_message["ciphertext"])
    shared_secret_server = pqc.decapsulate(server_secret_key, received_ciphertext)
    
    print_step("2.6", "Verificação: segredos compartilhados são iguais?")
    if shared_secret_client == shared_secret_server:
        print("✅ SUCESSO! Segredos compartilhados são idênticos")
        print(f"   Cliente: {shared_secret_client.hex()}")
        print(f"   Servidor: {shared_secret_server.hex()}")
    else:
        print("❌ ERRO! Segredos compartilhados são diferentes")
        return None, None
    
    print_step("2.7", "Derivação das chaves AES")
    aes_key_client = pqc.pqc.derive_aes_key(shared_secret_client)
    aes_key_server = pqc.pqc.derive_aes_key(shared_secret_server)
    
    if aes_key_client == aes_key_server:
        print("✅ Chaves AES idênticas derivadas com sucesso!")
    else:
        print("❌ ERRO! Chaves AES diferentes")
        return None, None
    
    return aes_key_client, aes_key_server

def demo_message_encryption(aes_key):
    """Demonstra a criptografia de mensagens"""
    print_separator("3. CRIPTOGRAFIA DE MENSAGENS AES-256-CBC")
    
    print_step("3.1", "Cliente prepara mensagem")
    original_message = "Olá pessoal! Esta é uma mensagem secreta usando PQC! 🔒"
    print(f"📝 Mensagem original: '{original_message}'")
    
    print_step("3.2", "Cliente criptografa mensagem")
    crypto_client = PQCAESCrypto(aes_key)
    encrypted_message = crypto_client.encrypt(original_message)
    
    print_step("3.3", "Servidor recebe e descriptografa")
    crypto_server = PQCAESCrypto(aes_key)
    decrypted_message = crypto_server.decrypt(encrypted_message)
    
    print_step("3.4", "Verificação final")
    if original_message == decrypted_message:
        print("✅ SUCESSO! Mensagem descriptografada corretamente")
        print(f"   Original: '{original_message}'")
        print(f"   Descriptografada: '{decrypted_message}'")
    else:
        print("❌ ERRO! Mensagem descriptografada incorretamente")

def demo_server_broadcast(aes_key):
    """Demonstra como o servidor retransmite mensagens"""
    print_separator("4. RETRANSMISSÃO DO SERVIDOR (Não E2E)")
    
    print("⚠️  IMPORTANTE: Este exemplo mostra por que NÃO é criptografia ponta a ponta")
    print("   O servidor pode ler e modificar todas as mensagens!")
    
    print_step("4.1", "Simulando múltiplos clientes")
    # Simular diferentes chaves AES para diferentes clientes
    alice_key = aes_key
    bob_key = os.urandom(32)  # Chave diferente para Bob
    
    crypto_alice = PQCAESCrypto(alice_key)
    crypto_bob = PQCAESCrypto(bob_key)
    crypto_server = PQCAESCrypto(alice_key)  # Servidor tem chave da Alice
    
    print_step("4.2", "Alice envia mensagem para servidor")
    alice_message = "Oi Bob! Como você está?"
    encrypted_from_alice = crypto_alice.encrypt(alice_message)
    print(f"📤 Alice → Servidor (criptografado)")
    
    print_step("4.3", "Servidor descriptografa mensagem de Alice")
    decrypted_at_server = crypto_server.decrypt(encrypted_from_alice)
    print(f"🔓 Servidor lê: '{decrypted_at_server}'")
    print("   ⚠️  SERVIDOR TEM ACESSO AO TEXTO CLARO!")
    
    print_step("4.4", "Servidor reformata e re-criptografa para Bob")
    formatted_message = f"<alice> {decrypted_at_server}"
    
    # Servidor criptografa com a chave do Bob (que seria diferente na prática)
    crypto_server_to_bob = PQCAESCrypto(bob_key)
    encrypted_to_bob = crypto_server_to_bob.encrypt(formatted_message)
    print(f"📤 Servidor → Bob (criptografado)")
    
    print_step("4.5", "Bob recebe e descriptografa")
    decrypted_by_bob = crypto_bob.decrypt(encrypted_to_bob)
    print(f"📥 Bob recebe: '{decrypted_by_bob}'")

def main():
    """Função principal da demonstração"""
    print("🔒 DEMONSTRAÇÃO COMPLETA DO PROCESSO PQC CHAT")
    print("=" * 60)
    print("⚠️  ESTE SISTEMA NÃO É CRIPTOGRAFIA PONTA A PONTA!")
    print("   O servidor pode ler todas as mensagens.")
    print("=" * 60)
    
    try:
        # 1. Geração de chaves
        pqc, server_pub, server_sec, client_pub, client_sec = demo_key_generation()
        time.sleep(1)
        
        # 2. Troca de chaves
        aes_key_client, aes_key_server = demo_key_exchange(pqc, server_pub, server_sec)
        if not aes_key_client:
            print("❌ Falha na troca de chaves. Encerrando demonstração.")
            return
        time.sleep(1)
        
        # 3. Criptografia de mensagens
        demo_message_encryption(aes_key_client)
        time.sleep(1)
        
        # 4. Demonstração de não-E2E
        demo_server_broadcast(aes_key_client)
        
        print_separator("DEMONSTRAÇÃO CONCLUÍDA")
        print("✅ Todos os processos foram demonstrados com sucesso!")
        print("\n📚 Para mais detalhes, consulte:")
        print("   - EXPLICACAO_PROCESSO.md")
        print("   - TECHNICAL_DETAILS.md")
        print("\n🚀 Para testar o chat completo:")
        print("   Terminal 1: python3 server/chat_server.py")
        print("   Terminal 2: python3 client/chat_client.py alice")
        print("   Terminal 3: python3 client/chat_client.py bob")
        
    except Exception as e:
        print(f"\n❌ Erro durante a demonstração: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 