# 🔒 Explicação Completa do Processo PQC Chat

## ⚠️ **IMPORTANTE: NÃO É CRIPTOGRAFIA PONTA A PONTA**

**Este sistema NÃO implementa criptografia ponta a ponta (End-to-End Encryption).** 

### Por que não é E2E?
- O **servidor tem acesso a todas as mensagens** descriptografadas
- O servidor é um **intermediário que pode ler** o conteúdo das mensagens
- A criptografia protege apenas a **comunicação entre cliente e servidor**
- **Cada cliente estabelece uma chave AES separada com o servidor**

### Modelo de Segurança:
```
Cliente A ←→ [Chave AES-A] ←→ Servidor ←→ [Chave AES-B] ←→ Cliente B
             Criptografado              Texto Claro              Criptografado
```

O servidor descriptografa mensagens de A, lê o conteúdo, e re-criptografa para enviar a B.

---

## 📋 **Processo Completo - Passo a Passo**

### 1️⃣ **Fase de Inicialização**

#### **Servidor:**
1. Gera par de chaves ML-KEM-512 (chave pública + chave secreta)
2. Armazena as chaves em `keys/server/main_server/`
3. Inicia servidor TCP na porta 12345

#### **Cliente:**
1. Gera par de chaves ML-KEM-512 (se não existir)
2. Armazena as chaves em `keys/clients/{nome_cliente}/`
3. Conecta ao servidor via TCP

### 2️⃣ **Fase de Troca de Chaves (Handshake PQC)**

#### **Passo 2.1: Servidor Envia Chave Pública**
```
Servidor → Cliente: {
    "type": "server_public_key",
    "server_id": "main_server", 
    "public_key": "<chave_publica_800_bytes_base64>"
}
```

#### **Passo 2.2: Cliente Encapsula Segredo**
1. Cliente recebe chave pública do servidor (800 bytes)
2. **ML-KEM ENCAPSULAMENTO:**
   - Gera segredo aleatório (32 bytes)
   - Encapsula usando chave pública do servidor
   - Produz: ciphertext (768 bytes) + shared_secret (32 bytes)

#### **Passo 2.3: Cliente Envia Ciphertext**
```
Cliente → Servidor: {
    "type": "client_ciphertext",
    "client_name": "alice",
    "ciphertext": "<ciphertext_768_bytes_base64>"
}
```

#### **Passo 2.4: Servidor Desencapsula**
1. Servidor recebe ciphertext (768 bytes)
2. **ML-KEM DESENCAPSULAMENTO:**
   - Usa sua chave secreta para desencapsular
   - Recupera o mesmo shared_secret (32 bytes)

#### **Passo 2.5: Derivação da Chave AES**
```python
# Tanto cliente quanto servidor fazem:
aes_key = SHA256(shared_secret)  # 32 bytes → 32 bytes
```

### 3️⃣ **Fase de Comunicação Criptografada**

#### **Envio de Mensagem (Cliente → Servidor):**
1. Cliente digita: `"Olá mundo!"`
2. **Criptografia AES-256-CBC:**
   - Gera IV aleatório (16 bytes)
   - Aplica padding PKCS7
   - Criptografa: `IV + AES_encrypt(mensagem_padded)`
   - Codifica em base64

3. Cliente envia para servidor
4. **Servidor descriptografa:**
   - Decodifica base64
   - Extrai IV (primeiros 16 bytes)
   - Descriptografa com AES-256-CBC
   - Remove padding PKCS7
   - Obtém: `"Olá mundo!"`

#### **Retransmissão (Servidor → Outros Clientes):**
1. Servidor formata: `"<alice> Olá mundo!"`
2. **Para cada cliente conectado:**
   - Criptografa usando a chave AES específica daquele cliente
   - Envia mensagem criptografada

3. **Cada cliente descriptografa:**
   - Usa sua própria chave AES
   - Recupera: `"<alice> Olá mundo!"`
   - Exibe na tela

---

## 🔐 **Detalhes Técnicos**

### **ML-KEM-512 (Kyber-512)**
- **Algoritmo:** Module Learning With Errors
- **Nível de Segurança:** NIST Nível 1 (equivalente a AES-128)
- **Tamanhos:**
  - Chave Pública: 800 bytes
  - Chave Secreta: 1632 bytes  
  - Ciphertext: 768 bytes
  - Segredo Compartilhado: 32 bytes

### **AES-256-CBC**
- **Chave:** 256 bits (32 bytes) derivada do segredo ML-KEM
- **Modo:** Cipher Block Chaining
- **IV:** 128 bits (16 bytes) aleatório por mensagem
- **Padding:** PKCS7

### **Fluxo de Dados:**
```
Mensagem Original → UTF-8 → PKCS7 Padding → AES-256-CBC → Base64 → Rede
Rede → Base64 → AES-256-CBC → Remove Padding → UTF-8 → Mensagem Original
```

---

## 🛡️ **Vantagens da Abordagem**

### **Resistência Quântica:**
- ML-KEM é resistente a ataques de computadores quânticos
- Protege contra futuras ameaças criptográficas

### **Performance:**
- Troca de chaves usa PQC (mais seguro)
- Mensagens usam AES (mais rápido)
- Híbrido oferece melhor performance que PQC puro

### **Escalabilidade:**
- Servidor gerencia múltiplos clientes
- Cada cliente tem chave AES única
- Adição/remoção de clientes não afeta outros

---

## ⚠️ **Limitações de Segurança**

### **Servidor como Ponto de Falha:**
- Servidor pode ler todas as mensagens
- Comprometimento do servidor expõe conversas
- Não há forward secrecy entre clientes

### **Não é E2E porque:**
- Mensagens não são criptografadas diretamente entre clientes
- Servidor atua como intermediário que descriptografa
- Cada cliente só tem chave compartilhada com servidor

### **Modelo de Confiança:**
- Clientes devem confiar no servidor
- Servidor deve ser mantido seguro
- Logs do servidor podem conter mensagens em texto claro

---

## 🔍 **Logs e Debugging**

Com os prints adicionados, você verá:

### **No Servidor:**
```
[PQC] ═══ INICIANDO TROCA DE CHAVES ML-KEM com ('127.0.0.1', 54321) ═══
[PQC] 📤 Enviando chave pública do servidor...
[ML-KEM] 🔓 DESENCAPSULAMENTO iniciado
[AES-DERIVE] 🔄 Derivando chave AES a partir do segredo compartilhado
[SERVIDOR] 📥 Recebendo mensagem criptografada de 'alice'
[CRYPTO] 🔓 Descriptografando: dGVzdGUgZGUgbWVuc2FnZW0=...
```

### **No Cliente:**
```
[PQC] ═══ INICIANDO AUTENTICAÇÃO ML-KEM COM SERVIDOR ═══  
[ML-KEM] 🔐 ENCAPSULAMENTO iniciado
[AES-DERIVE] ✅ Chave AES-256 derivada com SHA-256
[CLIENTE] 📤 Enviando mensagem criptografada para servidor
[CRYPTO] 📝 Texto original: 'Olá pessoal!'
```

---

## 📝 **Conclusão**

Este é um sistema de **chat com criptografia servidor-cliente** usando criptografia pós-quântica para troca de chaves e AES para performance. **NÃO é criptografia ponta a ponta**, mas oferece proteção contra interceptação na rede e resistência quântica para a troca de chaves inicial. 