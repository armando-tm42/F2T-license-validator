"""
License Validator & Manager.
Preserves backwards compatibility with legacy CLI functions while integrating
with the new PyQt6 GUI and SQLite database.
"""
import sys
from license_validator.core.crypto import (
    CryptoService,
    get_public_key_hex_for_mql5 as _core_get_hex,
    issue_license as _core_issue_license,
    verify_license_token as _core_verify,
)
from license_validator.database.db import init_db
from license_validator.database.repository import LicenseRepository


# 1. Generar llaves (deshabilitado: llaves fijadas)
def generate_keys():
    print("ℹ️ La generación de nuevas llaves está deshabilitada. Las llaves actuales son definitivas y la clave privada se custodia exclusivamente en Infisical.")



# 2. Exportar la clave pública para MQL5 (Módulo N en HEX)
def print_public_key_for_mql5():
    n_hex = _core_get_hex()
    print("\n--- COPIA ESTE VALOR EN LA LÍNEA 9 DE LicenseValidator.mqh ---")
    print(n_hex)
    print("-----------------------------------------------------------------\n")
    return n_hex


# 3. Emitir token de licencia como cadena de texto
def issue_license(
    account: int,
    expires: str,
    broker: str = "",
    tier: str = "",
) -> str:
    return _core_issue_license(account=account, expires=expires, broker=broker or None, tier=tier or None)


# 4. Guardar licencia directamente en archivo 'license.key' y registrar en base de datos SQLite
def save_license_file(
    account: int,
    expires: str,
    broker: str = "",
    tier: str = "",
    filename: str = "license.key",
    client_name: str = "",
):
    token = issue_license(account=account, expires=expires, broker=broker, tier=tier)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(token)
    print(f"\n✅ Licencia guardada en el archivo '{filename}'.")
    print(f"👉 Pega este archivo en la carpeta 'MQL5/Files' de tu MetaTrader 5.")

    # Guardar también en la base de datos PostgreSQL
    try:
        init_db()
        repo = LicenseRepository()
        repo.create(
            account=account,
            expires_at=expires,
            token=token,
            broker=broker,
            tier=tier,
            client_name=client_name or f"Cuenta {account}",
            notes=f"Generado mediante save_license_file ({filename})",
        )
        print("✅ Licencia registrada en la base de datos PostgreSQL.")
    except Exception as e:
        print(f"⚠️ Nota: No se pudo registrar en la base de datos: {e}")

    return token


if __name__ == "__main__":
    # Si se pasa el argumento --cli, ejecuta el script en modo consola tradicional
    if "--cli" in sys.argv:
        print_public_key_for_mql5()
        save_license_file(
            account=36105369,
            expires="2026-10-15",
        )
    else:
        # Por defecto, lanza la interfaz gráfica moderna PyQt6
        from license_validator.app import main as run_app
        run_app()
