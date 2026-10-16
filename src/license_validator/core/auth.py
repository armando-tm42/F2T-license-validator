import os
import hmac
import hashlib
import bcrypt
from dotenv import load_dotenv

from license_validator.core.secrets import SecretsManager

# Cargar variables de entorno desde .env si existe
load_dotenv()


def get_auth_secret() -> str:
    """Obtiene el secret (pepper) desde Infisical o variable de entorno."""
    return SecretsManager.get_auth_secret_key()


def get_hash_algorithm() -> str:
    """Obtiene el nombre del algoritmo configurado desde Infisical o variable de entorno."""
    return SecretsManager.get_hash_algorithm()


def _prepare_password_bytes(password: str) -> bytes:
    """
    Prepara la contraseña combinándola con la variable de ambiente secreta (pepper)
    y el algoritmo especificado. Esto previene el límite de 72 bytes de bcrypt y
    garantiza que sin la AUTH_SECRET_KEY los hashes no puedan ser rotos por fuerza bruta.
    """
    secret = get_auth_secret().encode("utf-8")
    pwd_bytes = password.encode("utf-8")
    
    # HMAC con SHA256 usando el secret de la variable de ambiente
    return hmac.new(secret, pwd_bytes, hashlib.sha256).digest()


def hash_password(plain_password: str) -> str:
    """
    Genera un hash seguro utilizando bcrypt + salt aleatorio + secret de entorno.
    """
    if not plain_password:
        raise ValueError("La contraseña no puede estar vacía.")

    prepared = _prepare_password_bytes(plain_password)
    # Genera salt con 12 rondas de costo
    salt = bcrypt.gensalt(rounds=12)
    hashed_bytes = bcrypt.hashpw(prepared, salt)
    return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con el hash bcrypt almacenado,
    utilizando el secret de entorno.
    """
    if not plain_password or not hashed_password:
        return False

    try:
        prepared = _prepare_password_bytes(plain_password)
        return bcrypt.checkpw(prepared, hashed_password.encode("utf-8"))
    except Exception:
        return False
