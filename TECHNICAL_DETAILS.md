# PQC Chat - Technical Deep Dive

This document provides a comprehensive technical explanation of the post-quantum cryptography implementation in the PQC Chat application, including detailed step-by-step breakdowns of the authentication and encryption processes.

## Table of Contents
1. [Overview](#overview)
2. [Cryptographic Algorithms](#cryptographic-algorithms)
3. [Key Generation Process](#key-generation-process)
4. [Authentication Flow](#authentication-flow)
5. [Message Encryption Process](#message-encryption-process)
6. [Security Analysis](#security-analysis)
7. [Implementation Details](#implementation-details)
8. [Fallback Mechanisms](#fallback-mechanisms)

## Overview

The PQC Chat application implements a hybrid cryptographic system that combines:
- **ML-KEM-512** (Machine Learning Key Encapsulation Mechanism) for post-quantum key exchange
- **AES-256-CBC** (Advanced Encryption Standard in Cipher Block Chaining mode) for message encryption
- **PBKDF2** for key derivation in fallback scenarios

This approach provides quantum-resistant authentication while maintaining high-performance message encryption.

## Cryptographic Algorithms

### ML-KEM-512 (Post-Quantum Key Encapsulation)

**Algorithm**: ML-KEM-512 (formerly known as Kyber-512)
**Security Level**: NIST Level 1 (equivalent to AES-128)
**Key Sizes**:
- Public Key: 800 bytes
- Secret Key: 1632 bytes
- Ciphertext: 768 bytes
- Shared Secret: 32 bytes

**Mathematical Foundation**:
- Based on the Module Learning With Errors (M-LWE) problem
- Uses polynomial arithmetic in quotient rings
- Security relies on the hardness of finding short vectors in lattices

**Why ML-KEM-512?**:
- Resistant to both classical and quantum computer attacks
- Standardized by NIST as part of the post-quantum cryptography standards
- Balanced performance vs. security trade-off
- Suitable for real-time communication applications

### AES-256-CBC (Symmetric Encryption)

**Algorithm**: Advanced Encryption Standard with 256-bit keys
**Mode**: Cipher Block Chaining (CBC)
**Block Size**: 128 bits (16 bytes)
**Key Size**: 256 bits (32 bytes)
**IV Size**: 128 bits (16 bytes)

**Security Properties**:
- Each message uses a randomly generated Initialization Vector (IV)
- Provides semantic security (identical plaintexts produce different ciphertexts)
- Authenticated through the ML-KEM key exchange process

## Key Generation Process

### Server Key Generation

**Step 1: ML-KEM Keypair Generation**
```
1. Initialize ML-KEM-512 algorithm
2. Generate random seed (32 bytes)
3. Expand seed using SHAKE-128 XOF (Extensible Output Function)
4. Generate polynomial matrix A from expanded seed
5. Sample secret vector s from centered binomial distribution
6. Sample error vector e from centered binomial distribution
7. Compute public key: pk = (A × s + e, seed)
8. Compute secret key: sk = s
9. Verify keypair through encapsulation/decapsulation test
```

**Step 2: Key Storage**
```
Server keys stored in: keys/server/{server_id}/
├── public_key.bin     # 800-byte ML-KEM public key
├── secret_key.bin     # 1632-byte ML-KEM secret key
└── metadata.json      # Algorithm info, timestamps, verification
```

### Client Key Generation

**Process**: Identical to server key generation
**Storage Location**: `keys/clients/{client_name}/`
**Verification**: Each keypair is tested immediately after generation

### Key Verification Process

**Verification Algorithm**:
```python
def verify_keypair(public_key, secret_key):
    1. Generate random message (32 bytes)
    2. Encapsulate message using public_key → (ciphertext, shared_secret_1)
    3. Decapsulate ciphertext using secret_key → shared_secret_2
    4. Compare shared_secret_1 == shared_secret_2
    5. Return True if equal, False otherwise
```

## Authentication Flow

### Phase 1: Connection Establishment

**Step 1: Client Connection**
```
Client → Server: TCP connection to port 12345
Server: Accept connection, add to client list
```

**Step 2: Server Public Key Transmission**
```
Server → Client: {
    "type": "server_public_key",
    "server_id": "main_server",
    "public_key": "<base64_encoded_800_byte_public_key>"
}
```

### Phase 2: ML-KEM Key Exchange

**Step 3: Client Key Encapsulation**
```
Client Process:
1. Decode server's public key from base64
2. Generate random message m (32 bytes)
3. Call ML-KEM Encapsulate(public_key, m)
   → Returns (ciphertext, shared_secret)
4. Store shared_secret for later key derivation
```

**ML-KEM Encapsulation Details**:
```
Encapsulate(pk, m):
1. Parse pk = (A, ρ)
2. Sample r from centered binomial distribution
3. Sample e1, e2 from centered binomial distribution  
4. Compute u = A^T × r + e1
5. Compute v = pk^T × r + e2 + Decode(m)
6. Return ciphertext = (u, v)
```

**Step 4: Ciphertext Transmission**
```
Client → Server: {
    "type": "client_ciphertext",
    "client_name": "alice",
    "ciphertext": "<base64_encoded_768_byte_ciphertext>"
}
```

**Step 5: Server Key Decapsulation**
```
Server Process:
1. Decode ciphertext from base64
2. Call ML-KEM Decapsulate(secret_key, ciphertext)
   → Returns shared_secret
3. Verify shared_secret is valid (32 bytes)
```

**ML-KEM Decapsulation Details**:
```
Decapsulate(sk, ct):
1. Parse ct = (u, v)
2. Compute m' = Encode(v - sk^T × u)
3. Re-encapsulate using m' to verify
4. Return m' if verification succeeds
```

### Phase 3: AES Key Derivation

**Step 6: Shared Secret to AES Key**
```python
def derive_aes_key(shared_secret):
    """Derive AES-256 key from 32-byte ML-KEM shared secret"""
    1. Use HKDF (HMAC-based Key Derivation Function)
    2. Input: shared_secret (32 bytes)
    3. Salt: b"PQC_CHAT_AES_DERIVE" 
    4. Info: b"AES-256-KEY"
    5. Output: 32-byte AES key
    
    return HKDF(
        algorithm=SHA256(),
        length=32,
        salt=salt,
        info=info,
    ).derive(shared_secret)
```

**Step 7: Crypto Instance Creation**
Both client and server create `PQCAESCrypto` instances with the derived AES key.

## Message Encryption Process

### Encryption (Client/Server → Network)

**Step 1: Message Preparation**
```python
def encrypt(self, plaintext):
    1. Convert plaintext to UTF-8 bytes
    2. Generate random 16-byte IV
    3. Create AES-256-CBC cipher with key and IV
    4. Apply PKCS7 padding to plaintext
    5. Encrypt padded plaintext
    6. Combine IV + ciphertext
    7. Encode as base64 for transmission
```

**Detailed Encryption Process**:
```
Input: "Hello, this is a secret message!"
│
├─ 1. UTF-8 Encoding
│   └─ b"Hello, this is a secret message!"
│
├─ 2. Random IV Generation
│   └─ 16 random bytes: [0x1a, 0x2b, 0x3c, ...]
│
├─ 3. PKCS7 Padding
│   └─ Pad to 16-byte boundary: b"Hello, this is a secret message!\x0f\x0f...\x0f"
│
├─ 4. AES-256-CBC Encryption
│   ├─ Key: 32-byte key derived from ML-KEM
│   ├─ IV: 16-byte random IV
│   └─ Ciphertext: encrypted padded message
│
├─ 5. Combine IV + Ciphertext
│   └─ [IV (16 bytes)][Ciphertext (variable)]
│
└─ 6. Base64 Encoding
    └─ "GisjPB4...encoded_result..."
```

### Decryption (Network → Client/Server)

**Step 1: Message Decryption**
```python
def decrypt(self, encrypted_data):
    1. Decode base64 to binary
    2. Extract first 16 bytes as IV
    3. Extract remaining bytes as ciphertext
    4. Create AES-256-CBC cipher with key and IV
    5. Decrypt ciphertext
    6. Remove PKCS7 padding
    7. Convert to UTF-8 string
```

**Detailed Decryption Process**:
```
Input: "GisjPB4...encoded_result..."
│
├─ 1. Base64 Decoding
│   └─ Binary data: [IV (16 bytes)][Ciphertext]
│
├─ 2. IV Extraction
│   └─ IV: first 16 bytes [0x1a, 0x2b, 0x3c, ...]
│
├─ 3. Ciphertext Extraction
│   └─ Ciphertext: remaining bytes
│
├─ 4. AES-256-CBC Decryption
│   ├─ Key: same 32-byte key from ML-KEM
│   ├─ IV: extracted 16-byte IV
│   └─ Padded plaintext
│
├─ 5. PKCS7 Unpadding
│   └─ b"Hello, this is a secret message!"
│
└─ 6. UTF-8 Decoding
    └─ "Hello, this is a secret message!"
```

### Message Transmission Protocol

**Length-Prefixed Protocol**:
```
Network Transmission Format:
[10-byte length][encrypted message]

Example:
"0000000075" + "GisjPB4...encoded_result..."
│              │
│              └─ 75-character base64 encrypted message
└─ Message length (75) padded to 10 digits
```

**Transmission Steps**:
1. Calculate encrypted message length
2. Send 10-byte length prefix (ASCII, zero-padded)
3. Send encrypted message bytes
4. Receiver reads length first, then exact message bytes

## Security Analysis

### Quantum Resistance

**ML-KEM Security**:
- **Classical Security**: Based on Module-LWE, believed secure against classical computers
- **Quantum Security**: No known quantum algorithms provide significant speedup against lattice problems
- **Concrete Security**: ML-KEM-512 provides ~140 bits of quantum security
- **Future-Proof**: Standardized by NIST specifically for post-quantum era

### Forward Secrecy

**Session-Based Security**:
- Each client connection establishes a new shared secret
- Compromise of one session doesn't affect other sessions
- Server restarts generate new keypairs (optional)

**Limitations**:
- Long-term server keys could be compromised
- Perfect Forward Secrecy requires ephemeral keys (future enhancement)

### Authentication Properties

**Mutual Authentication**:
- Server proves possession of secret key through successful decapsulation
- Client proves knowledge of server's public key through correct encapsulation
- No replay attacks due to random shared secrets

### Message Security

**Confidentiality**:
- AES-256-CBC with random IVs prevents pattern analysis
- Each message encrypted with same key but different IV
- Base64 encoding prevents binary transmission issues

**Integrity**:
- Decryption failures indicate message tampering
- PKCS7 padding provides basic integrity checking
- Future enhancement: add HMAC for explicit authentication

## Implementation Details

### C++ PQC Library Interface

**Core Functions**:
```cpp
// pqc_kem.cpp
extern "C" {
    int generate_keypair(unsigned char* public_key, 
                        unsigned char* secret_key);
    
    int encapsulate(const unsigned char* public_key,
                   unsigned char* ciphertext,
                   unsigned char* shared_secret);
    
    int decapsulate(const unsigned char* secret_key,
                   const unsigned char* ciphertext,
                   unsigned char* shared_secret);
}
```

**Library Integration**:
- Uses liboqs (Open Quantum Safe) for ML-KEM implementation
- Compiled as shared library (.dylib on macOS, .so on Linux)
- Python ctypes interface for seamless integration

### Python Crypto Wrapper

**PQCWrapper Class**:
```python
class PQCWrapper:
    def __init__(self):
        # Load compiled C++ library
        # Set up function prototypes
        # Configure argument and return types
    
    def generate_keypair(self):
        # Call C++ generate_keypair
        # Return (public_key, secret_key) tuple
    
    def encapsulate(self, public_key):
        # Call C++ encapsulate
        # Return (ciphertext, shared_secret) tuple
    
    def decapsulate(self, secret_key, ciphertext):
        # Call C++ decapsulate
        # Return shared_secret
```

### Error Handling

**Robust Error Management**:
- All cryptographic operations wrapped in try-catch blocks
- Invalid keys detected through verification tests
- Network errors handled gracefully with client cleanup
- Fallback to password-based encryption on PQC failure

## Fallback Mechanisms

### Password-Based Fallback

**When Activated**:
- ML-KEM library initialization fails
- Keypair generation/loading fails
- Key exchange process fails
- Any PQC-related exception

**Fallback Crypto Process**:
```python
def get_fallback_crypto_instance():
    1. Use fixed password: "fallback_secure_password_2024"
    2. Derive AES key using PBKDF2:
       - Password: fixed string
       - Salt: b"PQC_CHAT_FALLBACK_SALT"
       - Iterations: 100,000
       - Key length: 32 bytes
    3. Return PQCAESCrypto instance with derived key
```

**Fallback Security**:
- Still uses AES-256-CBC encryption
- All clients use same key (less secure)
- Provides basic protection when PQC unavailable
- Clearly identified in logs and user messages

### Graceful Degradation

**User Experience**:
- Transparent fallback - chat continues working
- Users notified of encryption type being used
- Server logs indicate which clients use which encryption
- No functionality lost, only security level changes

## Performance Considerations

### Computational Costs

**ML-KEM Operations**:
- Key generation: ~0.1-1ms (one-time cost)
- Encapsulation: ~0.1ms per authentication
- Decapsulation: ~0.1ms per authentication

**AES Operations**:
- Encryption: ~0.01ms per message (depends on length)
- Decryption: ~0.01ms per message

**Network Overhead**:
- Key exchange: ~1.5KB total (one-time per connection)
- Message overhead: ~33% increase due to base64 encoding + IV

### Scalability

**Server Capacity**:
- Each client requires ~2KB memory for crypto state
- Threaded architecture supports multiple simultaneous clients
- Key exchange done once per connection (not per message)

**Optimization Opportunities**:
- Connection pooling for frequent reconnections
- Batch message processing
- Ephemeral key caching

## Future Enhancements

### Security Improvements

1. **Perfect Forward Secrecy**: Implement ephemeral ML-KEM keys
2. **Message Authentication**: Add HMAC to each message
3. **Key Rotation**: Periodic re-key establishment
4. **Certificate System**: PKI for server key verification

### Performance Optimizations

1. **Connection Reuse**: Persistent client connections
2. **Batch Processing**: Multiple message encryption
3. **Hardware Acceleration**: Use ML-KEM hardware when available
4. **Compression**: Message compression before encryption

### Protocol Extensions

1. **Group Chat**: Multi-party key agreement
2. **File Transfer**: Encrypted file sharing
3. **Voice Chat**: Real-time encrypted audio
4. **Mobile Support**: Optimized mobile implementations

---

This technical documentation provides a comprehensive understanding of the cryptographic processes, security properties, and implementation details of the PQC Chat application. The system demonstrates practical post-quantum cryptography while maintaining usability and performance. 