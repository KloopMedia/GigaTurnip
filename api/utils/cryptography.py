from base64 import b64encode, b64decode

from Crypto.Random import get_random_bytes
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES


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

def load_keys(path):
    with open(f'{path}/publicKey.pem', 'rb') as p:
        pub_key = RSA.importKey(p.read().decode())
    with open(f'{path}/privateKey.pem', 'rb') as p:
        priv_key = RSA.importKey(p.read().decode())
    return pub_key, priv_key


def rsa_encrypt(public_key, message):
    rsa_public_key = PKCS1_OAEP.new(public_key)
    encrypted_text = rsa_public_key.encrypt(message)

    return encrypted_text


def encrypt_large_text(plaintext, public_key):
    aes_key = AES.new(key=get_random_bytes(32), mode=AES.MODE_CBC)

    cipher_text = aes_key.encrypt(plaintext.encode())
    rsa_cipher = PKCS1_OAEP.new(public_key)
    encrypted_aes_key = rsa_cipher.encrypt(aes_key.key)

    # Return the encrypted AES key and the AES-encrypted large text
    return b64encode(encrypted_aes_key), b64encode(cipher_text)


def rsa_decrypt(private_key, encrypted_text):
    rsa_private_key = PKCS1_OAEP.new(private_key)
    decrypted_text = rsa_private_key.decrypt(encrypted_text)

    return decrypted_text

