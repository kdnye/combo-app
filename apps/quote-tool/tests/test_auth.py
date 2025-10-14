from services.auth_utils import is_valid_password, is_valid_email
from werkzeug.security import generate_password_hash, check_password_hash


def test_is_valid_password_rules():
    assert is_valid_password("StrongPass!1234")
    assert is_valid_password("correct horse battery staple passphrase")
    assert is_valid_password("abcdefghijklmnopqrstuvwx")
    assert not is_valid_password("weakpass")
    assert not is_valid_password("short phrase")
    assert not is_valid_password("NoSpecialChars123")


def test_is_valid_email_rules():
    assert is_valid_email("user@example.com")
    assert not is_valid_email("bad-email")


def test_password_hash_roundtrip():
    password = 'StrongPass!1234'
    hashed = generate_password_hash(password)
    assert check_password_hash(hashed, password)
    assert not check_password_hash(hashed, 'wrongpassword')
