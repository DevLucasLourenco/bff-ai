from cryptography.fernet import Fernet
from app.core.security import SecretCipher


def test_cipher_round_trip():
    cipher = SecretCipher(Fernet.generate_key().decode())
    encrypted = cipher.encrypt("secret")
    assert encrypted != "secret"
    assert cipher.decrypt(encrypted) == "secret"
