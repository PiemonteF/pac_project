# PQC E2E Chat - Post-Quantum End-to-End Encrypted Chat

Uma aplicação de chat com criptografia pós-quântica verdadeiramente **End-to-End (E2E)**, onde o servidor atua apenas como roteador e **não pode ler as mensagens** entre clientes.

## 🔐 Características

- **Criptografia Pós-Quântica**: ML-KEM-512 para troca de chaves
- **End-to-End Real**: Servidor não consegue ler mensagens entre clientes
- **AES-256-CBC**: Criptografia simétrica para mensagens E2E
- **Zero Knowledge Server**: Servidor atua apenas como roteador
- **Sessões Múltiplas**: Cada par de clientes tem sua própria chave E2E

## 🚀 Configuração Rápida

### 1. Instalar Dependências
```bash
# macOS
brew install liboqs
pip install cryptography

# Ubuntu/Linux
sudo apt-get install liboqs-dev
pip install cryptography
```

### 2. Configuração Automatizada (Recomendado)
Execute o script de configuração para construir tudo e gerar chaves:
```bash
python3 setup.py
```

Isso vai:
- Construir a biblioteca PQC
- Gerar chaves do servidor e clientes
- Executar testes para verificar funcionamento

### 3. Configuração Manual (Alternativa)
Se preferir configuração manual:
```bash
# Construir a biblioteca PQC
make

# Gerar chaves do servidor E2E
python3 key_generation/key_manager.py generate-server e2e_server

# Gerar chaves dos clientes
python3 key_generation/key_manager.py generate-client alice
python3 key_generation/key_manager.py generate-client bob
python3 key_generation/key_manager.py generate-client charlie
```

## 🎯 Executando o Chat E2E

### Descobrir seu IP
```bash
# Para descobrir o IP da sua máquina
ifconfig | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}' | head -1
```

### Iniciar o Servidor E2E
```bash
# Servidor local (para testes na mesma máquina)
python3 server/e2e_server.py --host 127.0.0.1 --port 12346

# Servidor na rede (para outros dispositivos se conectarem)
python3 server/e2e_server.py --host 0.0.0.0 --port 12346
```

### Conectar Clientes
Abra novos terminais e execute:

**Para servidor local:**
```bash
python3 client/e2e_client.py --name alice --server 127.0.0.1
python3 client/e2e_client.py --name bob --server 127.0.0.1
python3 client/e2e_client.py --name charlie --server 127.0.0.1
```

**Para servidor na rede:**
```bash
python3 client/e2e_client.py --name alice --server SEU_IP_AQUI
python3 client/e2e_client.py --name bob --server SEU_IP_AQUI
python3 client/e2e_client.py --name charlie --server SEU_IP_AQUI
```

### Exemplo Prático
```bash
# Terminal 1 - Servidor
python3 server/e2e_server.py --host 0.0.0.0 --port 12346

# Terminal 2 - Alice
python3 client/e2e_client.py --name alice --server 172.20.10.9

# Terminal 3 - Bob
python3 client/e2e_client.py --name bob --server 172.20.10.9
```

## 💬 Como Usar o Chat E2E

### Comandos Disponíveis
```bash
/help                    # Mostrar ajuda
/list                    # Listar clientes online
/sessions                # Mostrar sessões E2E ativas
/key <cliente>           # Solicitar chave pública e estabelecer sessão E2E
@<cliente> <mensagem>    # Enviar mensagem E2E criptografada
/exit                    # Sair do chat
```

### Fluxo de Uso
1. **Alice e Bob se conectam** ao servidor
2. **Alice estabelece sessão E2E com Bob:**
   ```
   /key bob
   ```
3. **Alice envia mensagem E2E para Bob:**
   ```
   @bob Olá! Esta mensagem é verdadeiramente E2E! 🔐
   ```
4. **Bob recebe e descriptografa** a mensagem automaticamente

### Exemplo de Conversa
```
Alice:
/key bob
- Sessão E2E local criada com 'bob'

@bob Olá Bob! Como você está?
[14:25] - Você → bob: Olá Bob! Como você está?

Bob:
- Sessão E2E criada com 'alice'
[14:25] - alice → Você: Olá Bob! Como você está?

@alice Oi Alice! Estou bem, obrigado! 😊
[14:26] - Você → alice: Oi Alice! Estou bem, obrigado! 😊
```

## 🏗️ Arquitetura do Sistema

### Chat Tradicional vs E2E
```
TRADICIONAL:
Alice → [Criptografia A-Server] → Servidor (lê tudo) → [Criptografia Server-B] → Bob

E2E IMPLEMENTADO:
Alice → [Criptografia A-B direta] → Servidor (apenas roteia) → [Criptografia A-B direta] → Bob
```

### Camadas de Segurança
1. **Autenticação Server-Cliente**: ML-KEM-512 + AES-256
2. **Criptografia E2E**: ML-KEM-512 + AES-256 (chave única por par de clientes)
3. **Zero Knowledge**: Servidor não consegue descriptografar mensagens E2E

## 📁 Estrutura do Projeto
```
├── server/
│   ├── e2e_server.py          # Servidor E2E (apenas roteador)
│   └── chat_server.py         # Servidor tradicional (legado)
├── client/
│   ├── e2e_client.py          # Cliente E2E
│   └── chat_client.py         # Cliente tradicional (legado)
├── shared/
│   ├── e2e_crypto_utils.py    # Gerenciador de sessões E2E
│   ├── pqc_crypto_utils.py    # Criptografia PQC + AES
│   └── pqc_wrapper.py         # Interface ML-KEM
├── key_generation/
│   └── key_manager.py         # Gerenciamento de chaves
├── keys/                      # Chaves geradas (auto-criado)
│   ├── server/e2e_server/     # Chaves do servidor E2E
│   └── clients/               # Chaves dos clientes
└── tests/                     # Suíte de testes
```

## 🛠️ Opções Avançadas

### Servidor
```bash
# Host e porta customizados
python3 server/e2e_server.py --host 0.0.0.0 --port 8080

# ID do servidor customizado
python3 server/e2e_server.py --server-id meu_servidor_e2e

# Diretório de chaves customizado
python3 server/e2e_server.py --keys-dir /caminho/para/chaves
```

### Cliente
```bash
# Conectar a servidor remoto
python3 client/e2e_client.py --name alice --server 192.168.1.100 --port 8080

# Diretório de chaves customizado
python3 client/e2e_client.py --name alice --keys-dir /caminho/para/chaves
```

## 🔧 Solução de Problemas

**Biblioteca não encontrada?**
```bash
make clean && make
```

**Erro de permissão?**
```bash
chmod 755 keys/
```

**Problemas de conexão?**
```bash
# Certifique-se que o servidor está rodando primeiro
python3 server/e2e_server.py --host 0.0.0.0 --port 12346
```

**Connection refused?**
```bash
# Verifique se está usando o IP correto
ifconfig | grep "inet " | grep -v "127.0.0.1"
```

**Testar se tudo funciona:**
```bash
python3 tests/test_pqc.py
```

## 🧪 Teste Rápido

Execute este comando para testar a funcionalidade E2E:
```bash
# Terminal 1
python3 server/e2e_server.py --host 127.0.0.1 --port 12346

# Terminal 2
python3 client/e2e_client.py --name alice --server 127.0.0.1
# Digite: /key bob

# Terminal 3
python3 client/e2e_client.py --name bob --server 127.0.0.1
# Digite: @alice Olá Alice! Esta é uma mensagem E2E!
```

## 📋 Requisitos

- Python 3.7+
- Biblioteca liboqs
- Compilador C++
- Sistema operacional: macOS, Linux

## 🔐 Segurança

Este sistema implementa criptografia **verdadeiramente End-to-End** onde:

- ✅ Apenas os clientes que se comunicam podem ler as mensagens
- ✅ O servidor **nunca** tem acesso às chaves E2E
- ✅ Cada par de clientes tem uma chave única
- ✅ Resistente a ataques de computadores quânticos (ML-KEM-512)
- ✅ Zero knowledge: servidor atua apenas como roteador

**Isso é E2E real!** 🛡️🔐
