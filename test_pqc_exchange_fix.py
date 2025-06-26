#!/usr/bin/env python3
"""
Teste rápido para verificar se o erro 'pqc_exchange' foi corrigido.
"""

import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_e2e_client_initialization():
    """Testa se o cliente E2E inicializa corretamente com pqc_exchange."""
    
    try:
        from client.e2e_client import E2EChatClient
        
        print("🧪 TESTE: Inicialização do E2EChatClient")
        print("=" * 50)
        
        # Tentar criar cliente E2E
        client = E2EChatClient("test_alice")
        
        # Verificar se pqc_exchange existe
        if hasattr(client, 'pqc_exchange'):
            print("✅ client.pqc_exchange existe")
            
            # Verificar se é uma instância válida
            if client.pqc_exchange:
                print("✅ client.pqc_exchange é uma instância válida")
                
                # Verificar se tem os métodos necessários
                if hasattr(client.pqc_exchange, 'encapsulate'):
                    print("✅ client.pqc_exchange.encapsulate() existe")
                    
                if hasattr(client.pqc_exchange, 'decapsulate'):
                    print("✅ client.pqc_exchange.decapsulate() existe")
                    
                print("✅ SUCESSO: Problema do pqc_exchange foi RESOLVIDO!")
                return True
            else:
                print("❌ client.pqc_exchange é None ou inválido")
                return False
        else:
            print("❌ client.pqc_exchange não existe")
            return False
            
    except Exception as e:
        print(f"❌ ERRO ao inicializar cliente: {e}")
        return False

def test_establish_e2e_session_method():
    """Testa se o método establish_e2e_session() pode ser chamado sem erro de atributo."""
    
    try:
        from client.e2e_client import E2EChatClient
        from key_generation.key_manager import KeyManager
        
        print("\n🧪 TESTE: Método establish_e2e_session()")
        print("=" * 50)
        
        # Criar cliente
        client = E2EChatClient("test_alice")
        
        # Carregar chave pública de bob para teste
        key_manager = KeyManager()
        bob_keys = key_manager.load_client_keypair("bob")
        
        if not bob_keys:
            print("⚠️  Chaves de Bob não encontradas, pulando teste")
            return True
            
        bob_public, _ = bob_keys
        
        # Tentar executar establish_e2e_session (deve falhar em algum ponto, mas não por falta de pqc_exchange)
        try:
            client.establish_e2e_session("bob", bob_public)
            print("✅ establish_e2e_session() executou sem erro de atributo pqc_exchange")
            return True
        except AttributeError as e:
            if 'pqc_exchange' in str(e):
                print(f"❌ Ainda há erro de pqc_exchange: {e}")
                return False
            else:
                print(f"✅ Outro erro (não pqc_exchange): {e}")
                return True
        except Exception as e:
            print(f"✅ Outro erro (não pqc_exchange): {e}")
            return True
            
    except Exception as e:
        print(f"❌ ERRO no teste: {e}")
        return False

def main():
    """Executa os testes."""
    
    print("🔧 TESTANDO CORREÇÃO DO ERRO pqc_exchange")
    
    test1 = test_e2e_client_initialization()
    test2 = test_establish_e2e_session_method()
    
    print("\n" + "=" * 50)
    if test1 and test2:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Erro 'pqc_exchange' foi CORRIGIDO!")
    else:
        print("❌ ALGUNS TESTES FALHARAM!")
        print("🔧 Ainda há problemas com pqc_exchange...")
    print("=" * 50)

if __name__ == "__main__":
    main() 