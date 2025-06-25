# Makefile for PQC KEM library
CC = g++
CFLAGS = -fPIC -O2 -Wall -std=c++11
LDFLAGS = -shared
LIBS = -loqs

# Detect OS and architecture for different library paths
UNAME_S := $(shell uname -s)
UNAME_M := $(shell uname -m)

# Default paths
INCLUDE_DIRS = 
LIB_DIRS = 

ifeq ($(UNAME_S),Linux)
    LIBEXT = .so
    LIBNAME = libpqc_kem.so
    # Common Linux paths
    INCLUDE_DIRS += -I/usr/include -I/usr/local/include
    LIB_DIRS += -L/usr/lib -L/usr/local/lib
endif

ifeq ($(UNAME_S),Darwin)
    LIBEXT = .dylib
    LIBNAME = libpqc_kem.dylib
    LDFLAGS += -undefined dynamic_lookup
    
    # Homebrew paths (Intel and Apple Silicon)
    ifeq ($(UNAME_M),arm64)
        # Apple Silicon (M1/M2) Homebrew paths
        HOMEBREW_PREFIX = /opt/homebrew
    else
        # Intel Mac Homebrew paths
        HOMEBREW_PREFIX = /usr/local
    endif
    
    INCLUDE_DIRS += -I$(HOMEBREW_PREFIX)/opt/liboqs/include
    INCLUDE_DIRS += -I$(HOMEBREW_PREFIX)/opt/openssl@3/include
    INCLUDE_DIRS += -I$(HOMEBREW_PREFIX)/include
    
    LIB_DIRS += -L$(HOMEBREW_PREFIX)/opt/liboqs/lib
    LIB_DIRS += -L$(HOMEBREW_PREFIX)/opt/openssl@3/lib
    LIB_DIRS += -L$(HOMEBREW_PREFIX)/lib
    
    # Add architecture flag for Apple Silicon
    ifeq ($(UNAME_M),arm64)
        CFLAGS += -arch arm64
    endif
    
    # Additional libs that might be needed on macOS
    LIBS += -lcrypto -lssl
endif

# Combine all flags
ALL_CFLAGS = $(CFLAGS) $(INCLUDE_DIRS)
ALL_LDFLAGS = $(LDFLAGS) $(LIB_DIRS)

# Default target
all: $(LIBNAME)

# Compile the shared library
$(LIBNAME): pqc_kem.cpp
	$(CC) $(ALL_CFLAGS) $(ALL_LDFLAGS) -o $(LIBNAME) pqc_kem.cpp $(LIBS)



# Clean build artifacts
clean:
	rm -f $(LIBNAME) alice_kem bob_kem alice2_kem
	rm -f *.bin

# Test the library (requires compilation first)
test: $(LIBNAME)
	python3 test_pqc.py

# Install dependencies (macOS with Homebrew)
install_deps_mac:
	brew install liboqs

# Install dependencies (Ubuntu/Debian)
install_deps_ubuntu:
	sudo apt-get update
	sudo apt-get install liboqs-dev

# Install dependencies (general)
install_deps:
	@echo "Please install liboqs for your system:"
	@echo "  macOS: make install_deps_mac"
	@echo "  Ubuntu/Debian: make install_deps_ubuntu"
	@echo "  Or build from source: https://github.com/open-quantum-safe/liboqs"

# Debug: Show detected paths
debug:
	@echo "Detected OS: $(UNAME_S)"
	@echo "Detected Architecture: $(UNAME_M)"
	@echo "Library name: $(LIBNAME)"
	@echo "Include dirs: $(INCLUDE_DIRS)"
	@echo "Library dirs: $(LIB_DIRS)"
	@echo "All CFLAGS: $(ALL_CFLAGS)"
	@echo "All LDFLAGS: $(ALL_LDFLAGS)"

.PHONY: all clean test install_deps install_deps_mac install_deps_ubuntu test_individual debug 