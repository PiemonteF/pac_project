#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Demo E2E Real - Demonstração da Criptografia End-to-End Verdadeira
Mostra como Alice e Bob se comunicam de forma segura com o servidor apenas roteando mensagens.
"""

import time
import threading
import subprocess
import sys
import os
import signal
from pathlib import Path

def print_header(title):
    """Print formatted header."""
    print("\n" + "=" * 60)
    print(f"🔐 {title}")
    print("=" * 60)

def print_step(step_num, description):
    """Print formatted step."""
    print(f"\n📋 PASSO {step_num}: {description}")
    print("-" * 50)

def wait_for_input(message="Pressione ENTER para continuar..."):
    """Wait for user input."""
    input(f"\n⏸️  {message}")

def start_e2e_server():
    """Start the E2E server."""
    print_step(1, "Iniciando Servidor E2E (apenas roteador)")
    
    print("🚀 Iniciando servidor que NÃO consegue ler mensagens E2E...")
    
    # Start server in background
    server_process = subprocess.Popen([
        sys.executable, "server/e2e_server.py",
        "--host", "0.0.0.0",
        "--port", "12346"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Give server time to start
    time.sleep(2)
    
    if server_process.poll() is None:
        print("✅ Servidor E2E iniciado!")
        print("🛡️  IMPORTANTE: Servidor atua apenas como roteador")
        print("📡 Ele NÃO consegue ler mensagens entre clientes")
        return server_process
    else:
        print("❌ Falha ao iniciar servidor E2E")
        return None

def demonstrate_e2e_process():
    """Demonstrate the complete E2E process."""
    print_header("DEMONSTRAÇÃO E2E REAL")
    
    print("🔐 Este demo mostra comunicação End-to-End VERDADEIRA:")
    print("• Alice e Bob trocam chaves diretamente usando ML-KEM")
    print("• Mensagens são criptografadas com chave compartilhada") 
    print("• Servidor apenas roteia dados SEM conseguir ler")
    print("• Criptografia ponta a ponta REAL!")
    
    wait_for_input()
    
    # Start server
    server_process = start_e2e_server()
    if not server_process:
        print("❌ Não foi possível iniciar o servidor E2E")
        return
    
    try:
        print_step(2, "Instruções para Teste Manual")
        
        print("📋 Para testar o sistema E2E, abra 3 terminais:")
        print("\n🔥 Terminal 1 (Alice):")
        print("   python client/e2e_client.py --name alice --server localhost")
        
        print("\n🔥 Terminal 2 (Bob):")
        print("   python client/e2e_client.py --name bob --server localhost")
        
        print("\n🔥 Terminal 3 (Charlie - opcional):")
        print("   python client/e2e_client.py --name charlie --server localhost")
        
        print_step(3, "Fluxo de Comunicação E2E")
        
        print("🔄 Processo de comunicação E2E:")
        print("1️⃣  Alice conecta e registra chave pública")
        print("2️⃣  Bob conecta e registra chave pública")
        print("3️⃣  Alice: '/key bob' (solicita chave pública)")
        print("4️⃣  Sistema estabelece sessão E2E Alice-Bob")
        print("5️⃣  Alice: '@bob Olá Bob! 🔐' (mensagem E2E)")
        print("6️⃣  Servidor roteia SEM ler conteúdo")
        print("7️⃣  Bob recebe e descriptografa mensagem")
        
        print("\n💬 Comandos disponíveis nos clientes:")
        print("• @cliente mensagem  - Enviar mensagem E2E")
        print("• /list             - Ver clientes online")
        print("• /key cliente      - Solicitar chave pública")
        print("• /sessions         - Ver sessões E2E ativas")
        print("• /help             - Ajuda completa")
        print("• /exit             - Sair")
        
        print_step(4, "Verificação de Segurança")
        
        print("🛡️  Pontos importantes sobre segurança E2E:")
        print("• Cada par de clientes tem chave AES única")
        print("• Chaves derivadas de ML-KEM shared secrets")
        print("• Servidor não consegue descriptografar mensagens")
        print("• Comunicação verdadeiramente ponta a ponta")
        
        print("\n🔍 Para verificar que o servidor não lê:")
        print("• Observe logs do servidor - apenas roteia dados")
        print("• Mensagens aparecem criptografadas nos logs")
        print("• Servidor só vê metadados (remetente/destinatário)")
        
        wait_for_input("Pressione ENTER quando terminar os testes...")
        
        print_step(5, "Comparação: E2E vs Cliente-Servidor")
        
        print("📊 Diferenças fundamentais:")
        print("\n🔴 Sistema Cliente-Servidor (chat_server.py):")
        print("   • Servidor descriptografa TODAS as mensagens")
        print("   • Alice → [AES-A] → Servidor → [AES-B] → Bob")
        print("   • Servidor é ponto de descriptografia")
        print("   • Chaves AES diferentes mas servidor lê tudo")
        
        print("\n🟢 Sistema E2E Real (e2e_server.py):")
        print("   • Alice e Bob compartilham chave direta")
        print("   • Alice → [AES-AB] → Servidor → [AES-AB] → Bob")
        print("   • Servidor apenas roteia dados criptografados")
        print("   • SERVIDOR NÃO CONSEGUE LER MENSAGENS!")
        
        print_step(6, "Teste de Segurança Avançado")
        
        print("🧪 Para comprovar a segurança E2E:")
        print("\n1️⃣  Execute: python verificar_chaves.py")
        print("   • Mostra que clientes têm chaves AES diferentes para servidor")
        print("   • Mas estas são apenas para autenticação")
        
        print("\n2️⃣  Envie mensagens E2E e observe:")
        print("   • Logs do servidor mostram dados criptografados")
        print("   • Mensagem só é legível no cliente destinatário")
        
        print("\n3️⃣  Teste de interceptação:")
        print("   • Se servidor tentasse ler, veria apenas gibberish")
        print("   • Apenas clientes com chave E2E conseguem ler")
        
        print_header("DEMONSTRAÇÃO COMPLETA")
        print("✅ Sistema E2E real implementado com sucesso!")
        print("🔐 Criptografia verdadeiramente ponta a ponta")
        print("🛡️  Servidor atua apenas como roteador seguro")
        print("📡 Zero-knowledge do servidor sobre conteúdo")
        
    except KeyboardInterrupt:
        print("\n🛑 Demo interrompido")
    finally:
        print("\n🧹 Encerrando servidor E2E...")
        try:
            server_process.terminate()
            server_process.wait(timeout=5)
            print("✅ Servidor E2E encerrado")
        except:
            print("⚠️  Servidor pode ainda estar rodando")

def main():
    """Main function."""
    try:
        demonstrate_e2e_process()
    except Exception as e:
        print(f"\n❌ Erro na demonstração: {e}")
    finally:
        print("\n👋 Demonstração E2E finalizada")

if __name__ == "__main__":
    main() 