#!/usr/bin/env python3
# setup.py - PQC Chat System Setup Script

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(cmd, description, check=True):
    """Run a command and handle errors."""
    print(f"[SETUP] {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(f"[INFO] {result.stdout.strip()}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {description} failed: {e}")
        if e.stderr:
            print(f"[ERROR] {e.stderr.strip()}")
        return False

def check_dependencies():
    """Check if required dependencies are installed."""
    print("[SETUP] Checking dependencies...")
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("[ERROR] Python 3.7 or higher is required")
        return False
    
    # Check for C++ compiler
    if not run_command("g++ --version", "Checking for g++ compiler", check=False):
        if not run_command("clang++ --version", "Checking for clang++ compiler", check=False):
            print("[ERROR] No C++ compiler found. Please install g++ or clang++")
            return False
    
    # Check for liboqs
    system = platform.system()
    if system == "Darwin":  # macOS
        if not run_command("brew list liboqs", "Checking for liboqs (Homebrew)", check=False):
            print("[ERROR] liboqs not found. Please run: brew install liboqs")
            return False
    elif system == "Linux":
        # Check for liboqs development files
        if not (Path("/usr/include/oqs").exists() or 
                Path("/usr/local/include/oqs").exists() or
                Path("/opt/homebrew/include/oqs").exists()):
            print("[ERROR] liboqs development files not found.")
            print("[ERROR] Please run: sudo apt-get install liboqs-dev (Ubuntu/Debian)")
            print("[ERROR] Or build from source: https://github.com/open-quantum-safe/liboqs")
            return False
    
    print("[OK] All dependencies check passed")
    return True

def install_python_dependencies():
    """Install Python dependencies."""
    print("[SETUP] Installing Python dependencies...")
    return run_command(f"{sys.executable} -m pip install -r requirements.txt", 
                      "Installing Python packages")

def build_pqc_library():
    """Build the PQC C++ library."""
    print("[SETUP] Building PQC library...")
    
    # Clean first
    run_command("make clean", "Cleaning previous build", check=False)
    
    # Build
    if not run_command("make", "Building PQC library"):
        print("[ERROR] Failed to build PQC library")
        print("[INFO] Try running 'make debug' to see detected paths")
        return False
    
    # Verify library was created
    system = platform.system()
    if system == "Darwin":
        lib_file = "libpqc_kem.dylib"
    elif system == "Linux":
        lib_file = "libpqc_kem.so"
    else:
        lib_file = "pqc_kem.dll"
    
    if not Path(lib_file).exists():
        print(f"[ERROR] Library file {lib_file} was not created")
        return False
    
    print(f"[OK] PQC library built successfully: {lib_file}")
    return True

def generate_initial_keys():
    """Generate initial server and sample client keys."""
    print("[SETUP] Generating initial cryptographic keys...")
    
    # Generate server keypair
    if not run_command(f"{sys.executable} key_generation/key_manager.py generate-server", 
                      "Generating server keypair"):
        return False
    
    # Generate sample client keypairs
    sample_clients = ["alice", "bob", "charlie"]
    for client in sample_clients:
        if not run_command(f"{sys.executable} key_generation/key_manager.py generate-client {client}", 
                          f"Generating keypair for client '{client}'"):
            print(f"[WARNING] Failed to generate keys for client '{client}'")
    
    return True

def run_tests():
    """Run the test suite to verify everything works."""
    print("[SETUP] Running test suite...")
    return run_command(f"{sys.executable} tests/test_pqc.py", "Running PQC tests")

def show_usage_info():
    """Show information on how to use the system."""
    python_cmd = "python3" if sys.executable.endswith("python3") else "python"
    print("\n" + "="*60)
    print("🎉 PQC CHAT SYSTEM SETUP COMPLETE!")
    print("="*60)
    print("\n📖 Quick Start:")
    print("1. Start the server:")
    print(f"   {python_cmd} server/chat_server.py")
    print("\n2. Connect clients (in separate terminals):")
    print(f"   {python_cmd} client/chat_client.py alice")
    print(f"   {python_cmd} client/chat_client.py bob")
    print("\n🔧 Key Management:")
    print("   # List all keys")
    print(f"   {python_cmd} key_generation/key_manager.py list all")
    print("\n   # Generate new client")
    print(f"   {python_cmd} key_generation/key_manager.py generate-client newuser")
    print("\n📚 For more information, see README.md")
    print("="*60)

def main():
    """Main setup function."""
    print("="*60)
    print("PQC CHAT SYSTEM SETUP")
    print("="*60)
    print("This script will set up the Post-Quantum Cryptography Chat System")
    print("by installing dependencies, building libraries, and generating keys.\n")
    
    # Check if we're in the right directory
    if not Path("pqc_kem.cpp").exists():
        print("[ERROR] Please run this script from the project root directory")
        sys.exit(1)
    
    steps = [
        ("Checking dependencies", check_dependencies),
        ("Installing Python dependencies", install_python_dependencies),
        ("Building PQC library", build_pqc_library),
        ("Generating initial keys", generate_initial_keys),
        ("Running tests", run_tests),
    ]
    
    for step_name, step_func in steps:
        print(f"\n[STEP] {step_name}")
        if not step_func():
            print(f"[FATAL] Setup failed at step: {step_name}")
            print("Please check the error messages above and try again.")
            sys.exit(1)
    
    show_usage_info()

if __name__ == "__main__":
    main() 