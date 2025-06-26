#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para verificar como as chaves AES são estabelecidas
Mostra que no sistema atual, cada cliente tem chave AES diferente com o servidor
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.pqc_crypto_utils import PQCKeyExchange
import hashlib

def simular_conexao_cliente(client_name, server_public_key, server_secret_key):
    """Simula conexão de um cliente com o servidor"""
    print(f"\n{'='*50}")
    print(f"🔐 SIMULANDO CONEXÃO: {client_name}")
    print(f"{'='*50}")
    
    pqc = PQCKeyExchange()
    
    # Cliente encapsula segredo usando chave pública do servidor
    print(f"[{client_name}] 📤 Encapsulando segredo...")
    ciphertext, shared_secret_client = pqc.encapsulate(server_public_key)
    
    # Servidor desencapsula usando sua chave secreta
    print(f"[SERVIDOR] 📥 Desencapsulando segredo de {client_name}...")
    shared_secret_server = pqc.decapsulate(server_secret_key, ciphertext)
    
    # Verificar se segredos são iguais
    if shared_secret_client == shared_secret_server:
        print(f"[✅] Segredos compartilhados são iguais!")
    else:
        print(f"[❌] ERRO: Segredos diferentes!")
        return None
    
    # Derivar chave AES
    aes_key = hashlib.sha256(shared_secret_client).digest()
    
    print(f"[{client_name}] 🔑 Segredo compartilhado: {shared_secret_client.hex()}")
    print(f"[{client_name}] 🔑 Chave AES derivada: {aes_key.hex()}")
    
    return aes_key

def main():
    """Demonstra que cada cliente tem chave AES diferente"""
    print("🔍 VERIFICAÇÃO: Chaves AES no Sistema Client-Server")
    print("=" * 60)
    print("⚠️  Objetivo: Mostrar que cada cliente tem chave AES DIFERENTE")
    print("   (No sistema atual, NÃO há chave compartilhada entre clientes)")
    
    try:
        # Gerar chaves do servidor (uma vez)
        print(f"\n🏗️  GERANDO CHAVES DO SERVIDOR...")
        pqc = PQCKeyExchange()
        server_public_key, server_secret_key = pqc.generate_keypair()
        
        print(f"[SERVIDOR] 🔑 Chave pública: {server_public_key.hex()[:32]}...")
        
        # Simular conexões de diferentes clientes
        clientes = ["Alice", "Bob", "Charlie"]
        chaves_aes = {}
        
        for cliente in clientes:
            chave = simular_conexao_cliente(cliente, server_public_key, server_secret_key)
            if chave:
                chaves_aes[cliente] = chave
        
        # Comparar chaves AES
        print(f"\n🔍 ANÁLISE DAS CHAVES AES:")
        print("=" * 50)
        
        for i, (cliente1, chave1) in enumerate(chaves_aes.items()):
            for cliente2, chave2 in list(chaves_aes.items())[i+1:]:
                if chave1 == chave2:
                    print(f"[❌] {cliente1} e {cliente2}: CHAVES IGUAIS (isso seria um erro!)")
                else:
                    print(f"[✅] {cliente1} e {cliente2}: CHAVES DIFERENTES (correto!)")
        
        print(f"\n🎯 CONCLUSÃO:")
        print("=" * 30)
        print("✅ Cada cliente tem chave AES ÚNICA com o servidor")
        print("✅ Alice não pode descriptografar mensagens diretas de Bob")
        print("✅ Servidor precisa re-criptografar para cada cliente")
        print("❌ NÃO é End-to-End (servidor lê tudo)")
        
        print(f"\n💡 PARA E2E REAL:")
        print("- Alice e Bob precisariam trocar chaves DIRETAMENTE")
        print("- Ambos teriam a MESMA chave AES Alice-Bob")
        print("- Servidor seria apenas roteador (não leria mensagens)")
        
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 