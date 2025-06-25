# PQC Chat - How to Run

A post-quantum cryptography chat application using ML-KEM-512 for secure authentication and AES-256 encryption.

## Quick Setup

### 1. Install Dependencies
```bash
# macOS
brew install liboqs
pip install cryptography

# Ubuntu/Linux
sudo apt-get install liboqs-dev
pip install cryptography
```

### 2. Automated Setup (Recommended)
Run the setup script to build everything and generate keys:
```bash
python3 setup.py
```

This will:
- Build the PQC library
- Generate server and client keys
- Run tests to verify everything works

### 3. Manual Setup (Alternative)
If you prefer manual setup:
```bash
# Build the PQC library
make

# Generate server keys
python3 key_generation/key_manager.py generate-server

# Generate client keys for users
python3 key_generation/key_manager.py generate-client alice
python3 key_generation/key_manager.py generate-client bob
python3 key_generation/key_manager.py generate-client charlie
```

## Running the Chat

### Start the Server
```bash
python3 server/chat_server.py
```
The server will listen on `localhost:12345` by default.

### Connect Clients
Open new terminals and run:
```bash
python3 client/chat_client.py alice
python3 client/chat_client.py bob
python3 client/chat_client.py charlie
```

### Server Options
```bash
# Custom host and port
python3 server/chat_server.py --host 0.0.0.0 --port 8080

# Custom server ID
python3 server/chat_server.py --server-id my_server

# Custom keys directory
python3 server/chat_server.py --keys-dir /path/to/keys
```

### Client Options
```bash
# Connect to remote server
python3 client/chat_client.py alice --server 192.168.1.100 --port 8080

# Custom keys directory
python3 client/chat_client.py alice --keys-dir /path/to/keys
```

## How It Works

1. **Authentication**: Each client authenticates with the server using ML-KEM-512 post-quantum cryptography
2. **Encryption**: All messages are encrypted with AES-256-CBC
3. **Security**: Quantum-resistant key exchange protects against future quantum computers

## Project Structure
```
├── server/chat_server.py     # Start the chat server
├── client/chat_client.py     # Connect as a client
├── key_generation/           # Key management tools
├── shared/                   # Crypto utilities
├── keys/                     # Generated keypairs (auto-created)
└── tests/                    # Test suite
```

## Commands in Chat
- Type messages normally to chat
- Type `exit` to disconnect

## Troubleshooting

**Library not found?**
```bash
make clean && make
```

**Permission errors?**
```bash
chmod 755 keys/
```

**Connection issues?**
```bash
# Make sure server is running first
python3 server/chat_server.py
```

**Test everything works:**
```bash
python3 tests/test_pqc.py
```

## Requirements
- Python 3.7+
- liboqs library
- C++ compiler

That's it! The chat uses post-quantum cryptography to keep your messages secure. 🔐 # pac_project
