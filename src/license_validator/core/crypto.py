import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey

from license_validator.core.secrets import SecretsManager

DEFAULT_PUBLIC_KEY_PATH = "public.pem"


class CryptoService:
    """Service to handle RSA key operations and license token signing/verification."""

    def __init__(
        self,
        public_key_path: str = DEFAULT_PUBLIC_KEY_PATH,
    ) -> None:
        self.public_key_path = Path(public_key_path)

    def has_private_key(self) -> bool:
        """Returns True if private key is available in Infisical (strictly in RAM)."""
        pem = SecretsManager.get_rsa_private_key_pem()
        return pem is not None and "PRIVATE KEY" in pem

    def has_public_key(self) -> bool:
        """Returns True if public key is available in Infisical or local file."""
        pem = SecretsManager.get_rsa_public_key_pem(str(self.public_key_path))
        if pem is not None and "PUBLIC KEY" in pem:
            return True
        return self.has_private_key()

    def has_keypair(self) -> bool:
        return self.has_private_key() and self.has_public_key()

    def load_private_key(self) -> RSAPrivateKey:
        """Loads RSA private key strictly from Infisical into RAM."""
        pem_content = SecretsManager.get_rsa_private_key_pem()
        if pem_content:
            return serialization.load_pem_private_key(pem_content.encode("utf-8"), password=None)
        raise ConnectionError(
            "La clave privada no se encuentra en Infisical. "
            "Asegúrate de haber configurado el secreto 'RSA_PRIVATE_KEY_PEM' en Infisical "
            "y de que 'INFISICAL_CLIENT_SECRET' esté configurado en tu archivo .env con acceso a internet."
        )

    def load_public_key(self) -> RSAPublicKey:
        pem_content = SecretsManager.get_rsa_public_key_pem(str(self.public_key_path))
        if pem_content:
            return serialization.load_pem_public_key(pem_content.encode("utf-8"))
        if self.has_private_key():
            return self.load_private_key().public_key()
        raise FileNotFoundError(
            f"Clave pública no encontrada en el archivo local '{self.public_key_path}' ni en Infisical."
        )

    def get_public_key_hex_for_mql5(self) -> str:
        """Export RSA public modulus N as a 512-character uppercase HEX string for MQL5."""
        pub_key = self.load_public_key()
        return f"{pub_key.public_numbers().n:0512X}"

    def issue_license(
        self,
        account: int,
        expires: str,
        terminal_hash: str,
        broker: Optional[str] = None,
        tier: Optional[str] = None,
    ) -> str:
        """
        Sign and issue a license token with mandatory account, expires, and terminal_hash.
        Token format: <base64_payload>.<base64_signature>
        """
        priv_key = self.load_private_key()

        clean_terminal = str(terminal_hash).strip().upper() if terminal_hash else ""
        if not clean_terminal:
            raise ValueError("El 'terminal_hash' es obligatorio para emitir la licencia.")

        payload: Dict[str, Any] = {
            "account": int(account),
            "expires": str(expires).strip(),  # Format: YYYY-MM-DD
            "terminal_hash": clean_terminal,
        }
        if broker and broker.strip():
            payload["broker"] = str(broker).strip()
        if tier and tier.strip():
            payload["tier"] = str(tier).strip()

        # Canonical JSON: without whitespace and deterministic key sorting
        payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

        # Digital signature SHA256 + PKCS#1 v1.5
        signature = priv_key.sign(
            payload_bytes,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )

        b64_data = base64.b64encode(payload_bytes).decode("ascii")
        b64_sig = base64.b64encode(signature).decode("ascii")
        return f"{b64_data}.{b64_sig}"

    @staticmethod
    def decode_token_payload(token: str) -> Optional[Dict[str, Any]]:
        """Decode and parse the payload portion of a token without verifying signature."""
        try:
            parts = token.strip().split(".")
            if len(parts) != 2:
                return None
            payload_bytes = base64.b64decode(parts[0])
            return json.loads(payload_bytes.decode("utf-8"))
        except Exception:
            return None

    def verify_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Verify digital signature and structure of a license token.
        Returns (is_valid, payload_dict_or_none, message).
        """
        if not self.has_public_key():
            return False, None, "No se encontró la clave pública ('public.pem') para verificar."

        parts = token.strip().split(".")
        if len(parts) != 2:
            return False, None, "Formato de token inválido. Debe tener la estructura <datos>.<firma>."

        try:
            payload_bytes = base64.b64decode(parts[0])
            sig_bytes = base64.b64decode(parts[1])
            payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception as e:
            return False, None, f"Error al decodificar Base64/JSON: {e}"

        pub_key = self.load_public_key()
        try:
            pub_key.verify(
                sig_bytes,
                payload_bytes,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except InvalidSignature:
            return False, payload, "Firma digital inválida: La licencia ha sido manipulada o firmada con otra clave."
        except Exception as e:
            return False, payload, f"Error durante la verificación: {e}"

        # Check expiration date
        expires_str = payload.get("expires")
        if expires_str:
            try:
                exp_date = datetime.strptime(expires_str, "%Y-%m-%d").date()
                today = datetime.now().date()
                if exp_date < today:
                    return True, payload, f"Firma válida, pero la licencia EXPIRÓ el {expires_str}."
            except ValueError:
                return True, payload, "Firma válida, pero el formato de fecha no es YYYY-MM-DD."

        # Check terminal_hash presence
        if not payload.get("terminal_hash"):
            return True, payload, "Firma válida, pero el token no incluye el campo obligatorio 'terminal_hash'."

        return True, payload, "Licencia auténtica y válida."


# Standalone utility functions for backwards compatibility
_default_crypto_service = CryptoService()


def get_public_key_hex_for_mql5(public_path: str = DEFAULT_PUBLIC_KEY_PATH) -> str:
    service = CryptoService(public_key_path=public_path)
    return service.get_public_key_hex_for_mql5()


def issue_license(
    account: int,
    expires: str,
    terminal_hash: str,
    broker: Optional[str] = None,
    tier: Optional[str] = None,
) -> str:
    service = CryptoService()
    return service.issue_license(
        account=account,
        expires=expires,
        terminal_hash=terminal_hash,
        broker=broker,
        tier=tier,
    )


def verify_license_token(
    token: str,
    public_path: str = DEFAULT_PUBLIC_KEY_PATH,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    service = CryptoService(public_key_path=public_path)
    return service.verify_token(token)
