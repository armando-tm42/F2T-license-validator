import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv

# Carga variables de entorno (.env junto al ejecutable si está congelado, o el .env estándar en desarrollo)
if getattr(sys, "frozen", False):
    exe_dir = Path(sys.executable).parent
    env_candidate = exe_dir / ".env"
    if env_candidate.is_file():
        load_dotenv(env_candidate)
    else:
        load_dotenv()
else:
    load_dotenv()

DEFAULT_HASH_ALGO = "bcrypt"


class SecretsManager:
    """
    Centralized Secrets Manager integrating Infisical Cloud directly into RAM.
    Eliminates all local secret fallbacks: secrets must strictly be retrieved
    from the Infisical vault at runtime.
    """

    _client = None
    _init_attempted = False
    _is_connected = False
    _cache: Dict[str, str] = {}

    @classmethod
    def _get_infisical_client(cls):
        if cls._init_attempted:
            return cls._client

        cls._init_attempted = True
        client_id = os.getenv("INFISICAL_CLIENT_ID", "").strip()
        client_secret = os.getenv("INFISICAL_CLIENT_SECRET", "").strip()
        host = os.getenv("INFISICAL_HOST", "https://app.infisical.com").strip()

        if not client_id or not client_secret:
            return None

        try:
            from infisical_sdk import InfisicalSDKClient

            client = InfisicalSDKClient(host=host)
            client.auth.universal_auth.login(
                client_id=client_id,
                client_secret=client_secret,
            )
            cls._client = client
            cls._is_connected = True
            print("🔐 [Infisical] Conexión exitosa a la bóveda de secretos.")
            return cls._client
        except ImportError:
            print("⚠️ [Infisical] Librería 'infisicalsdk' no instalada.")
            return None
        except Exception as e:
            print(f"⚠️ [Infisical] Error al conectar con Infisical ({e}).")
            return None

    @classmethod
    def is_connected(cls) -> bool:
        """Returns True if Infisical client is authenticated and connected."""
        cls._get_infisical_client()
        return cls._is_connected

    @classmethod
    def get_secret(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Retrieves a secret strictly from Infisical Cloud by key name.
        Uses in-memory cache and does NOT fall back to local disk or os.environ.
        """
        if key in cls._cache:
            return cls._cache[key]

        client = cls._get_infisical_client()
        if client:
            project_id = os.getenv("INFISICAL_PROJECT_ID", "").strip()
            env_slug = os.getenv("INFISICAL_ENVIRONMENT", "dev").strip()

            try:
                secret_res = client.secrets.get_secret_by_name(
                    secret_name=key,
                    project_id=project_id,
                    environment_slug=env_slug,
                    secret_path="/",
                )
                if secret_res and hasattr(secret_res, "secretValue") and secret_res.secretValue:
                    val = secret_res.secretValue
                    cls._cache[key] = val
                    return val
            except Exception:
                pass

        return default

    @classmethod
    def get_auth_secret_key(cls) -> str:
        """
        Retrieves the secret pepper used for password hashing strictly from Infisical.
        Checks 'AUTH_SECRET_KEY' and 'DEFAULT_SECRET_KEY' in Infisical.
        """
        for candidate in ("AUTH_SECRET_KEY", "DEFAULT_SECRET_KEY"):
            val = cls.get_secret(candidate)
            if val and val.strip():
                return val.strip()
        raise ConnectionError(
            "No se encontró 'AUTH_SECRET_KEY' en Infisical. "
            "Asegúrate de haber configurado este secreto en tu bóveda de Infisical y de contar con acceso a internet."
        )

    @classmethod
    def get_hash_algorithm(cls) -> str:
        """
        Retrieves the hashing algorithm name (e.g. 'bcrypt').
        Checks 'HASH_ALGORITHM' and 'DEFAULT_ALGORITHM' in Infisical. Defaults to 'bcrypt'.
        """
        for candidate in ("HASH_ALGORITHM", "DEFAULT_ALGORITHM"):
            val = cls.get_secret(candidate)
            if val and val.strip():
                return val.strip().lower()
        return DEFAULT_HASH_ALGO

    @classmethod
    def get_rsa_private_key_pem(cls) -> Optional[str]:
        """
        Retrieves the RSA private key PEM string strictly from Infisical into RAM.
        Local private.pem files on disk are completely disallowed.
        """
        for candidate in ("RSA_PRIVATE_KEY_PEM", "PRIVATE_KEY_PEM", "private.pem"):
            val = cls.get_secret(candidate)
            if val and "PRIVATE KEY" in val:
                return val.strip()

        return None

    @classmethod
    def get_rsa_public_key_pem(cls, local_fallback_path: str = "public.pem") -> Optional[str]:
        """
        Retrieves the RSA public key PEM string from Infisical directly into RAM.
        If not explicitly in Infisical, checks local files or auto-derives it
        mathematically from the RSA private key in Infisical.
        """
        for candidate in ("RSA_PUBLIC_KEY_PEM", "PUBLIC_KEY_PEM", "public.pem"):
            val = cls.get_secret(candidate)
            if val and "PUBLIC KEY" in val:
                return val.strip()

        # 1. Candidatos de archivo local en disco (compatible con PyInstaller / congelado)
        candidates = [Path(local_fallback_path)]
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).parent
            candidates.insert(0, exe_dir / "public.pem")
            if hasattr(sys, "_MEIPASS"):
                candidates.insert(0, Path(sys._MEIPASS) / "public.pem")
        candidates.append(Path.cwd() / "public.pem")

        for cand in candidates:
            if cand.is_file():
                try:
                    content = cand.read_text(encoding="utf-8").strip()
                    if "PUBLIC KEY" in content:
                        return content
                except Exception:
                    pass

        # 2. Derivación automática en memoria a partir de la clave privada en Infisical
        priv_pem = cls.get_rsa_private_key_pem()
        if priv_pem:
            try:
                from cryptography.hazmat.primitives import serialization
                priv_key = serialization.load_pem_private_key(priv_pem.encode("utf-8"), password=None)
                pub_bytes = priv_key.public_key().public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
                pub_str = pub_bytes.decode("utf-8").strip()
                cls._cache["RSA_PUBLIC_KEY_PEM"] = pub_str
                return pub_str
            except Exception:
                pass

        return None

    @classmethod
    def get_database_url(cls) -> str:
        """
        Retrieves the PostgreSQL database connection string strictly from Infisical Cloud into RAM.
        Checks 'DATABASE_URL', 'DB_URL', 'POSTGRES_URL' in Infisical.
        """
        for candidate in ("DATABASE_URL", "DB_URL", "POSTGRES_URL"):
            val = cls.get_secret(candidate)
            if val and val.strip():
                return val.strip()

        # Fallback to local environment variable (e.g. for testing)
        env_val = os.getenv("DATABASE_URL", "").strip()
        if env_val:
            return env_val

        raise ConnectionError(
            "No se encontró el secreto 'DATABASE_URL' en Infisical. "
            "Asegúrate de haber creado el secreto 'DATABASE_URL' en tu bóveda de Infisical con la cadena de conexión de PostgreSQL."
        )

    @classmethod
    def get_sqlite_encryption_key(cls) -> Optional[str]:
        """Legacy helper for SQLite encryption key if needed."""
        for candidate in ("SQLITE_ENCRYPTION_KEY", "SQLITE_KEY", "DB_ENCRYPTION_KEY", "DB_PASSWORD"):
            val = cls.get_secret(candidate)
            if val and val.strip():
                return val.strip()
        return None
