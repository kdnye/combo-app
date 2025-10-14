import hashlib

import pytest
from app import create_app, limiter
from app.models import db, User, PasswordResetToken
from services import auth_utils as auth_service


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        limiter.reset()
        db.create_all()
        user = User(name="Reset", email="reset@example.com", is_active=True)
        user.set_password("OldPass!1234")
        db.session.add(user)
        db.session.commit()
    yield app
    with app.app_context():
        db.drop_all()
        limiter.reset()


@pytest.fixture
def app_context(app):
    with app.app_context():
        yield


def test_token_reset_flow(app_context):
    token, error = auth_service.create_reset_token("reset@example.com")
    assert error is None and token
    user = User.query.filter_by(email="reset@example.com").first()
    assert user is not None
    stored = PasswordResetToken.query.filter_by(user_id=user.id).first()
    assert stored is not None
    expected_digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    assert stored.token == expected_digest
    assert stored.token != token
    err = auth_service.reset_password_with_token(token, "NewStrongPass!1234")
    assert err is None
    user = User.query.filter_by(email="reset@example.com").first()
    assert user is not None and user.check_password("NewStrongPass!1234")
    err2 = auth_service.reset_password_with_token(token, "AnotherStrongPass!1234")
    assert err2 is not None


def test_compromised_database_token_is_rejected(app_context):
    token, error = auth_service.create_reset_token("reset@example.com")
    assert error is None and token
    user = User.query.filter_by(email="reset@example.com").first()
    assert user is not None
    stored = PasswordResetToken.query.filter_by(user_id=user.id).first()
    assert stored is not None
    compromised_value = stored.token
    assert compromised_value != token
    error_message = auth_service.reset_password_with_token(
        compromised_value, "AnotherStrongPass!1234"
    )
    assert error_message == "Invalid or expired token."
