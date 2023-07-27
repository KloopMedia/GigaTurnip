import base64
import os
from base64 import b64encode, b64decode

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from Crypto.Cipher import AES


def generate_keys():
    key = RSA.generate(1024)
    private_key = key
    public_key = key.publickey()

    return public_key, private_key


def save_keys(path, public_key, private_key):
    with open(f'{path}/publicKey.pem', 'wb') as p:
        p.write(public_key.export_key('PEM'))
    with open(f'{path}/privateKey.pem', 'wb') as p:
        p.write(private_key.exportKey('PEM'))


def get_private_key(path=None):
    p = path
    if p is None:
        p = os.getenv("PRIVATE_KEY")

    private_key = RSA.importKey(p.decode())
    return private_key

def rsa_encrypt(public_key, message):
    rsa_cipher = PKCS1_OAEP.new(public_key)
    encrypted_text = rsa_cipher.encrypt(message)

    return encrypted_text



def rsa_decrypt(private_key, encrypted_text):
    rsa_private_key = PKCS1_OAEP.new(private_key)
    decrypted_text = rsa_private_key.decrypt(encrypted_text)

    return decrypted_text

def encrypt_large_text(large_text, public_key):
    # Generate a random symmetric key (AES)
    aes_key = get_random_bytes(32)  # 32 bytes = 256 bits

    # Encrypt the symmetric key using RSA public key
    encrypted_aes_key = rsa_encrypt(public_key, aes_key)

    # Encrypt the large text using the symmetric key (AES)
    aes_cipher = AES.new(aes_key, AES.MODE_ECB)
    ciphertext= aes_cipher.encrypt(pad(large_text.encode('utf-8'), 32))
    return encrypted_aes_key, ciphertext


def decrypt_large_text(encrypted_aes_key, ciphertext, private_key):
    # Decrypt the symmetric key (AES) using RSA private key
    aes_key = rsa_decrypt(private_key, encrypted_aes_key)

    # Decrypt the large text using the symmetric key (AES)
    if len(aes_key) != 32:
        aes_key = base64.b64decode(aes_key)
    aes_cipher = AES.new(aes_key, AES.MODE_ECB)
    decrypted_data = aes_cipher.decrypt(ciphertext)

    return decrypted_data.decode('utf-8')
