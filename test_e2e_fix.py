#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Teste E2E Fix - Verifica se a correção da criptografia dupla funcionou
"""

import subprocess
import time
import sys
import signal

def start_server():
    """Start E2E server."""
    print("🚀 Iniciando servidor E2E...")
    server_process = subprocess.Popen([
        sys.executable, "server/e2e_server.py",
        "--host", "0.0.0.0",
        "--port", "12346"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    time.sleep(2)
    
    if server_process.poll() is None:
        print("✅ Servidor E2E iniciado com sucesso!")
        return server_process
    else:
        print("❌ Falha ao iniciar servidor E2E")
        return None

def test_instructions():
    """Print test instructions."""
    print("\n" + "="*60)
    print("🧪 TESTE DA CORREÇÃO E2E")
    print("="*60)
    
    print("\n📋 INSTRUÇÕES PARA TESTE:")
    
    print("\n🔥 Terminal 2 (Alice):")
    print("   python3 client/e2e_client.py --name alice --server 10.150.0.70")
    
    print("\n🔥 Terminal 3 (Bob):")
    print("   python3 client/e2e_client.py --name bob --server 10.150.0.70")
    
    print("\n💬 FLUXO DE TESTE:")
    print("1️⃣  Alice: /key bob")
    print("2️⃣  Alice: @bob Olá Bob! Teste da correção E2E! 🔐")
    print("3️⃣  Bob: @alice Oi Alice! Funcionou perfeitamente! ✅")
    
    print("\n🔍 VERIFICAÇÕES:")
    print("• Mensagens devem aparecer descriptografadas corretamente")
    print("• Sem erros de 'Invalid padding bytes'")
    print("• Servidor apenas roteia sem ler conteúdo")
    
    print("\n⚠️  SE DER ERRO:")
    print("• Verifique se os dois clientes conectaram")
    print("• Certifique-se de fazer /key antes de enviar mensagens")
    print("• Use Ctrl+C para encerrar este teste")

def main():
    """Main test function."""
    try:
        server_process = start_server()
        if not server_process:
            return
        
        test_instructions()
        
        print("\n⏸️  Pressione Ctrl+C quando terminar o teste...")
        
        # Wait for user to finish testing
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Teste interrompido")
    finally:
        if 'server_process' in locals() and server_process:
            print("\n🧹 Encerrando servidor...")
            try:
                server_process.terminate()
                server_process.wait(timeout=5)
                print("✅ Servidor encerrado")
            except:
                print("⚠️  Servidor pode ainda estar rodando")

if __name__ == "__main__":
    main() 