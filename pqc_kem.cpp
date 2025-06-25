#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "oqs/oqs.h"

// Export functions for Python integration
extern "C" {

// Structure to hold key pair
typedef struct {
    uint8_t *public_key;
    uint8_t *secret_key;
    size_t public_key_len;
    size_t secret_key_len;
} KeyPair;

// Structure to hold encapsulation result
typedef struct {
    uint8_t *ciphertext;
    uint8_t *shared_secret;
    size_t ciphertext_len;
    size_t shared_secret_len;
} EncapsResult;

// Global KEM instance
static OQS_KEM *g_kem = NULL;
static const char *KEM_ALGORITHM = OQS_KEM_alg_ml_kem_512;

/**
 * Initialize the ML-KEM algorithm
 * Returns: 0 on success, -1 on failure
 */
int pqc_init() {
    if (g_kem != NULL) {
        OQS_KEM_free(g_kem);
    }
    
    g_kem = OQS_KEM_new(KEM_ALGORITHM);
    if (g_kem == NULL) {
        fprintf(stderr, "[PQC] Error: Failed to initialize ML-KEM-512\n");
        return -1;
    }
    
    printf("[PQC] Initialized ML-KEM-512 successfully\n");
    return 0;
}

/**
 * Generate a new key pair
 * Returns: KeyPair structure (caller must free memory)
 */
KeyPair* pqc_generate_keypair() {
    if (g_kem == NULL) {
        fprintf(stderr, "[PQC] Error: KEM not initialized\n");
        return NULL;
    }
    
    KeyPair *keypair = (KeyPair*)malloc(sizeof(KeyPair));
    if (!keypair) return NULL;
    
    keypair->public_key_len = g_kem->length_public_key;
    keypair->secret_key_len = g_kem->length_secret_key;
    
    keypair->public_key = (uint8_t*)malloc(keypair->public_key_len);
    keypair->secret_key = (uint8_t*)malloc(keypair->secret_key_len);
    
    if (!keypair->public_key || !keypair->secret_key) {
        free(keypair->public_key);
        free(keypair->secret_key);
        free(keypair);
        return NULL;
    }
    
    if (OQS_KEM_keypair(g_kem, keypair->public_key, keypair->secret_key) != OQS_SUCCESS) {
        free(keypair->public_key);
        free(keypair->secret_key);
        free(keypair);
        return NULL;
    }
    
    printf("[PQC] Generated new key pair\n");
    return keypair;
}

/**
 * Encapsulate a shared secret using a public key
 * public_key: The public key to use for encapsulation
 * public_key_len: Length of the public key
 * Returns: EncapsResult structure (caller must free memory)
 */
EncapsResult* pqc_encapsulate(const uint8_t *public_key, size_t public_key_len) {
    if (g_kem == NULL) {
        fprintf(stderr, "[PQC] Error: KEM not initialized\n");
        return NULL;
    }
    
    if (public_key_len != g_kem->length_public_key) {
        fprintf(stderr, "[PQC] Error: Invalid public key length\n");
        return NULL;
    }
    
    EncapsResult *result = (EncapsResult*)malloc(sizeof(EncapsResult));
    if (!result) return NULL;
    
    result->ciphertext_len = g_kem->length_ciphertext;
    result->shared_secret_len = g_kem->length_shared_secret;
    
    result->ciphertext = (uint8_t*)malloc(result->ciphertext_len);
    result->shared_secret = (uint8_t*)malloc(result->shared_secret_len);
    
    if (!result->ciphertext || !result->shared_secret) {
        free(result->ciphertext);
        free(result->shared_secret);
        free(result);
        return NULL;
    }
    
    if (OQS_KEM_encaps(g_kem, result->ciphertext, result->shared_secret, public_key) != OQS_SUCCESS) {
        free(result->ciphertext);
        free(result->shared_secret);
        free(result);
        return NULL;
    }
    
    printf("[PQC] Encapsulated shared secret\n");
    return result;
}

/**
 * Decapsulate a shared secret using a secret key and ciphertext
 * secret_key: The secret key to use for decapsulation
 * secret_key_len: Length of the secret key
 * ciphertext: The ciphertext to decapsulate
 * ciphertext_len: Length of the ciphertext
 * shared_secret: Buffer to store the shared secret (must be pre-allocated)
 * Returns: 0 on success, -1 on failure
 */
int pqc_decapsulate(const uint8_t *secret_key, size_t secret_key_len,
                   const uint8_t *ciphertext, size_t ciphertext_len,
                   uint8_t *shared_secret) {
    if (g_kem == NULL) {
        fprintf(stderr, "[PQC] Error: KEM not initialized\n");
        return -1;
    }
    
    if (secret_key_len != g_kem->length_secret_key) {
        fprintf(stderr, "[PQC] Error: Invalid secret key length\n");
        return -1;
    }
    
    if (ciphertext_len != g_kem->length_ciphertext) {
        fprintf(stderr, "[PQC] Error: Invalid ciphertext length\n");
        return -1;
    }
    
    if (OQS_KEM_decaps(g_kem, shared_secret, ciphertext, secret_key) != OQS_SUCCESS) {
        fprintf(stderr, "[PQC] Error: Failed to decapsulate\n");
        return -1;
    }
    
    printf("[PQC] Decapsulated shared secret\n");
    return 0;
}

/**
 * Get the length of various components
 */
size_t pqc_get_public_key_length() {
    return g_kem ? g_kem->length_public_key : 0;
}

size_t pqc_get_secret_key_length() {
    return g_kem ? g_kem->length_secret_key : 0;
}

size_t pqc_get_ciphertext_length() {
    return g_kem ? g_kem->length_ciphertext : 0;
}

size_t pqc_get_shared_secret_length() {
    return g_kem ? g_kem->length_shared_secret : 0;
}

/**
 * Free memory allocated for KeyPair
 */
void pqc_free_keypair(KeyPair *keypair) {
    if (keypair) {
        free(keypair->public_key);
        free(keypair->secret_key);
        free(keypair);
    }
}

/**
 * Free memory allocated for EncapsResult
 */
void pqc_free_encaps_result(EncapsResult *result) {
    if (result) {
        free(result->ciphertext);
        free(result->shared_secret);
        free(result);
    }
}

/**
 * Cleanup and free resources
 */
void pqc_cleanup() {
    if (g_kem) {
        OQS_KEM_free(g_kem);
        g_kem = NULL;
    }
    printf("[PQC] Cleanup completed\n");
}

/**
 * Utility function to print hex data (for debugging)
 */
void pqc_print_hex(const char *label, const uint8_t *data, size_t length) {
    printf("[PQC] %s (%zu bytes): ", label, length);
    for (size_t i = 0; i < length && i < 32; i++) { // Limit to first 32 bytes
        printf("%02X", data[i]);
    }
    if (length > 32) printf("...");
    printf("\n");
}

} // extern "C" 