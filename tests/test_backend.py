import os
import tempfile
from pathlib import Path
from datetime import date, timedelta

from license_validator.core.crypto import CryptoService
from license_validator.database.db import Base, init_engine, sessionmaker
from license_validator.database.repository import LicenseRepository
from license_validator.database.models import License


def test_crypto_and_db_pipeline():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = tmp_path / "test_licenses.sqlite"

        # 1. Crypto Service Tests (In-Memory via SecretsManager)
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from license_validator.core.secrets import SecretsManager

        test_priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        test_priv_pem = test_priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")
        test_pub_pem = test_priv.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

        SecretsManager._cache["RSA_PRIVATE_KEY_PEM"] = test_priv_pem
        SecretsManager._cache["RSA_PUBLIC_KEY_PEM"] = test_pub_pem
        SecretsManager._cache["AUTH_SECRET_KEY"] = "unit_test_auth_pepper_2026!"
        SecretsManager._cache["SQLITE_ENCRYPTION_KEY"] = "unit_test_sqlite_key_2026!"

        crypto = CryptoService()
        assert crypto.has_private_key() is True
        assert crypto.has_public_key() is True

        # Check MQL5 Modulus N
        mql5_hex = crypto.get_public_key_hex_for_mql5()
        assert len(mql5_hex) == 512

        # Test that issuing a license without terminal_hash raises ValueError
        future_date = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
        try:
            crypto.issue_license(
                account=12345678,
                expires=future_date,
                terminal_hash="",
            )
            assert False, "Debe lanzar ValueError si terminal_hash está vacío"
        except ValueError as e:
            assert "terminal_hash" in str(e)

        # Issue license with mandatory terminal_hash
        token = crypto.issue_license(
            account=12345678,
            expires=future_date,
            terminal_hash="D0E8209F77C8CF37AD8BF550E51FF075",
        )
        assert token and "." in token

        # Verify license
        is_valid, payload, msg = crypto.verify_token(token)
        assert is_valid is True
        assert payload["account"] == 12345678
        assert payload["expires"] == future_date
        assert payload["terminal_hash"] == "D0E8209F77C8CF37AD8BF550E51FF075"
        assert "broker" not in payload
        assert "tier" not in payload

        # 2. Database & CRUD Tests (Test aislado en SQLite para pruebas unitarias)
        engine = init_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(bind=engine)
        test_session_factory = sessionmaker(bind=engine)
        repo = LicenseRepository(session_factory=test_session_factory)

        # Create
        created = repo.create(
            account=12345678,
            expires_at=future_date,
            token=token,
            client_name="Cliente Prueba",
            notes="Licencia de prueba unitaria",
            terminal_hash="D0E8209F77C8CF37AD8BF550E51FF075",
        )
        assert created.id is not None
        assert created.client_name == "Cliente Prueba"
        assert created.terminal_hash == "D0E8209F77C8CF37AD8BF550E51FF075"
        assert created.status == "Activa"

        # Read / Get
        fetched = repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.account == 12345678

        # Search
        results = repo.get_all(search_query="Cliente Prueba")
        assert len(results) == 1

        # Stats
        stats = repo.get_stats()
        assert stats["total"] == 1
        assert stats["active"] == 1

        # Update
        updated = repo.update(
            license_id=created.id,
            client_name="Cliente Actualizado",
            notes="Notas actualizadas",
        )
        assert updated.client_name == "Cliente Actualizado"
        assert updated.notes == "Notas actualizadas"

        # Delete
        deleted = repo.delete(created.id)
        assert deleted is True
        assert repo.get_by_id(created.id) is None
        assert len(repo.get_all()) == 0

        # 3. User Authentication & CRUD Tests
        from license_validator.core.auth import hash_password, verify_password
        from license_validator.database.user_repository import UserRepository

        # Bcrypt + Pepper Hashing
        pwd = "SecretPassword123!"
        hashed = hash_password(pwd)
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
        assert verify_password(pwd, hashed) is True
        assert verify_password("WrongPassword", hashed) is False

        # UserRepository CRUD
        user_repo = UserRepository(session_factory=test_session_factory)
        assert user_repo.count() == 0

        # Create first user (should automatically be admin)
        admin = user_repo.create(
            username="admin",
            name="Armando Tapia",
            password=pwd,
        )
        assert admin.id is not None
        assert admin.username == "admin"
        assert admin.name == "Armando Tapia"
        assert admin.role == "admin"
        assert admin.is_admin is True
        assert admin.is_manager is False
        assert user_repo.count() == 1

        # Create second user with role 'manager'
        manager = user_repo.create(
            username="operador",
            name="Operador Prueba",
            password="ManagerPass123!",
            role="manager",
        )
        assert manager.id is not None
        assert manager.role == "manager"
        assert manager.is_manager is True
        assert manager.is_admin is False
        assert user_repo.count() == 2

        # Authentication check
        auth_user = user_repo.authenticate("admin", pwd)
        assert auth_user is not None
        assert auth_user.id == admin.id
        assert auth_user.is_admin is True

        auth_mgr = user_repo.authenticate("operador", "ManagerPass123!")
        assert auth_mgr is not None
        assert auth_mgr.is_manager is True

        # Bad password
        assert user_repo.authenticate("admin", "invalid_password") is None
        # Non-existent user
        assert user_repo.authenticate("unknown_user", pwd) is None

        # Update user name, password and role
        user_repo.update(user_id=admin.id, name="Armando M. Tapia", password="NewPassword456!")
        updated_admin = user_repo.get_by_id(admin.id)
        assert updated_admin.name == "Armando M. Tapia"
        assert user_repo.authenticate("admin", "NewPassword456!") is not None
        assert user_repo.authenticate("admin", pwd) is None

        # Promote manager to admin
        user_repo.update(user_id=manager.id, role="admin")
        promoted = user_repo.get_by_id(manager.id)
        assert promoted.is_admin is True

        # Delete user
        assert user_repo.delete(manager.id) is True
        assert user_repo.count() == 1
        assert user_repo.get_by_id(manager.id) is None

        # 4. Single Session & Concurrency Tests (Option 1)
        # Login 1 on PC-OFICINA
        ok1, u1, token1, err1 = user_repo.authenticate_and_start_session(
            username="admin",
            password="NewPassword456!",
            device_name="PC-OFICINA",
            timeout_seconds=120,
        )
        assert ok1 is True
        assert token1 and len(token1) == 36
        assert err1 is None

        # Login 2 on PC-CASA (same user, active session) -> MUST BE REJECTED
        ok2, u2, token2, err2 = user_repo.authenticate_and_start_session(
            username="admin",
            password="NewPassword456!",
            device_name="PC-CASA",
            timeout_seconds=120,
        )
        assert ok2 is False
        assert token2 is None
        assert "sesión abierta" in err2.lower()
        assert "PC-OFICINA" in err2

        # Heartbeat test
        assert user_repo.heartbeat(u1.id, token1) is True
        assert user_repo.heartbeat(u1.id, "fake-invalid-token") is False

        # Clean Logout on PC-OFICINA
        assert user_repo.end_session(u1.id, token1) is True

        # Now Login on PC-CASA MUST SUCCEED
        ok3, u3, token3, err3 = user_repo.authenticate_and_start_session(
            username="admin",
            password="NewPassword456!",
            device_name="PC-CASA",
            timeout_seconds=120,
        )
        assert ok3 is True
        assert token3 is not None

        # Simulate PC Crash: set last_heartbeat to 3 minutes ago (> 120s timeout)
        from datetime import timedelta
        with test_session_factory() as sess:
            u_db = sess.query(User).filter(User.id == u3.id).first()
            u_db.last_heartbeat = datetime.utcnow() - timedelta(seconds=180)
            sess.commit()

        # Login on PC-LAPTOP should now take over the abandoned session
        ok4, u4, token4, err4 = user_repo.authenticate_and_start_session(
            username="admin",
            password="NewPassword456!",
            device_name="PC-LAPTOP",
            timeout_seconds=120,
        )
        assert ok4 is True
        assert token4 != token3

        # 4. SecretsManager & DB URL Normalization Test
        from license_validator.core.secrets import SecretsManager
        from license_validator.database.db import normalize_db_url, is_database_encrypted

        auth_secret = SecretsManager.get_auth_secret_key()
        assert auth_secret and len(auth_secret) > 0
        hash_algo = SecretsManager.get_hash_algorithm()
        assert hash_algo == "bcrypt"

        # Test PostgreSQL URL normalization and Infisical retrieval
        test_raw_url = "postgres://user:pass@host.aivencloud.com:27481/db?sslmode=require"
        SecretsManager._cache["DATABASE_URL"] = test_raw_url
        assert SecretsManager.get_database_url() == test_raw_url

        normalized = normalize_db_url(SecretsManager.get_database_url())
        assert normalized.startswith("postgresql+psycopg2://")
        assert "sslmode=require" in normalized
        assert is_database_encrypted() is True

        print("✅ Todas las pruebas de backend, criptografía, SecretsManager, bcrypt y base de datos pasaron con éxito.")


if __name__ == "__main__":
    test_crypto_and_db_pipeline()

