from app.core.security import get_password_hash, verify_password


def test_password_hash_and_verify_roundtrip() -> None:
    hashed = get_password_hash("candidate-portal-password")
    assert verify_password("candidate-portal-password", hashed)
    assert not verify_password("wrong-password", hashed)
