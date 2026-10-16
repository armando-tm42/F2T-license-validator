# 🛡️ F2T Administrador de licencias

Aplicación de escritorio desarrollada con **PyQt6**, **SQLAlchemy** y **PostgreSQL en la Nube (Aiven Cloud)** para generar, administrar, validar y exportar licencias criptográficas asimétricas (RSA-2048) para asesores expertos (EAs) e indicadores en **MetaTrader 5 (MQL5)**.

---

## ✨ Características Principales

1. **Interfaz Gráfica de Escritorio (PyQt6)**:
   * Dashboard con tarjetas métricas: Total de Licencias, Activas, Por Expirar (7 días o menos) y Expiradas.
   * Tabla interactiva con búsqueda en tiempo real por número de cuenta MT5, nombre del cliente o notas.
   * Filtros dinámicos por estado de vigencia (Activa, Por expirar, Expirada).
   * Acciones directas con clic derecho o barra de herramientas (Copiar token, exportar `.key`, verificar).

2. **Control de Acceso Basado en Roles (`Admin` vs `Manager`)**:
   * **Manager**: Control total sobre el CRUD de licencias (crear, editar, eliminar, exportar y verificar).
   * **Administrador**: Todo lo del Manager más el control de usuarios (crear usuarios, editar perfiles, asignar roles `admin`/`manager`, cambiar contraseñas y desactivar accesos).
   * Contraseñas cifradas con **bcrypt** combinadas con un *secret pepper* custodiado en **Infisical Cloud**.

3. **Base de Datos PostgreSQL en la Nube & Migraciones con Alembic**:
   * Base de datos centralizada y segura en **Aiven Cloud** con cifrado en tránsito forzado (**SSL/TLS**) y en reposo (AES-256).
   * Cadena de conexión custodiada exclusivamente en **Infisical Cloud** (`DATABASE_URL`).
   * Control de versiones y migraciones de esquema mediante **Alembic** (`alembic upgrade head`).

4. **Criptografía Asimétrica RSA-2048 & Compatibilidad MQL5**:
   * Generación de firmas digitales seguras (RSA 2048-bit, SHA-256 con padding PKCS#1 v1.5).
   * Clave privada custodiada estrictamente en la memoria RAM de Infisical (sin archivos `.pem` privados en disco).
   * Visor y copia en 1 clic de la **clave pública (Módulo N en HEX)** para la línea 9 de `LicenseValidator.mqh`.
   * Exportación de archivos `license.key` listos para la carpeta `MQL5/Files`.

5. **Protección Anti-Compartición con Hash de Terminal MT5**:
   * Permite vincular criptográficamente la licencia no solo al número de cuenta, sino también al identificador/hash único de instalación de MetaTrader 5 (`TERMINAL_DATA_PATH`).
   * **Objetivo**: Evita que un usuario comparta las credenciales de su cuenta de trading y el Asesor Experto (`.ex5`) para usarlo en otras computadoras.
   * Si la licencia incluye `terminal_hash`, el Asesor Experto comprueba que el hash de la instalación actual de MT5 coincida exactamente con el firmado por RSA.
   * Si se deja en blanco, la licencia opera de manera universal para cualquier terminal de esa cuenta.

---

## 🚀 Cómo Ejecutar en Desarrollo

### Opción 1: Acceso Rápido con 1 Clic (Windows)
Simplemente haz doble clic sobre:
```text
run_app.bat
```
El script verificará e instalará automáticamente las dependencias si faltan y lanzará la interfaz gráfica.

### Opción 2: Desde la Terminal
```bash
pip install "PyQt6>=6.5.0" "sqlalchemy>=2.0.0" "cryptography>=50.0.2" "bcrypt>=4.0.0" "python-dotenv>=1.0.0" "infisicalsdk>=0.3.0" "psycopg2-binary>=2.9.9" "alembic>=1.13.0" "pillow>=10.0.0"
python src/license_validator/main.py
```

---

## 📦 Empaquetado a Ejecutable (.EXE) e Instalador (Inno Setup)

### Paso 1: Generar el Ejecutable Autónomo (.exe)
Hemos preparado el script automatizado [build_exe.bat](file:///mnt/c/Users/armando-miguel-tapia/Documents/Projects/f2t/license-validator/build_exe.bat) junto con la especificación [f2t_licencias.spec](file:///mnt/c/Users/armando-miguel-tapia/Documents/Projects/f2t/license-validator/f2t_licencias.spec):

1. En Windows, haz doble clic en `build_exe.bat` (o ejecuta `pyinstaller --clean f2t_licencias.spec`).
2. El script limpiará compilaciones anteriores, empaquetará la aplicación con su icono oficial `app_icon.ico`, copiará el `.env` de configuración y generará la carpeta autónoma en:
   ```text
   dist\F2T-Licencias\F2T-Licencias.exe
   ```
3. Puedes probar la aplicación ejecutando directamente `dist\F2T-Licencias\F2T-Licencias.exe`.

---

### Paso 2: Crear el Instalador de Windows (Inno Setup)

Para distribuir la aplicación a los usuarios finales en un único instalador profesional tipo asistente:

1. Descarga e instala [Inno Setup](https://jrsoftware.org/isdl.php) (gratuito).
2. Haz clic derecho sobre el archivo [installer_inno.iss](file:///mnt/c/Users/armando-miguel-tapia/Documents/Projects/f2t/license-validator/installer_inno.iss) en el explorador de Windows y selecciona **"Compile"** (o ábrelo en el compilador de Inno Setup y presiona `Ctrl + F9`).
3. El instalador autónomo se creará automáticamente en:
   ```text
   dist_installer\F2T-Licencias-Setup.exe
   ```
   **Características del instalador:**
   * Asistente en español con estilo moderno.
   * Instalación predeterminada en `Archivos de Programa` (modo 64 bits).
   * Creación de accesos directos en el Menú Inicio y Escritorio con el icono de la aplicación.
   * Registro del desinstalador en el Panel de Control / Configuración de Windows.
   * Empaquetado comprimido (LZMA2 Ultra) con verificación de integridad.

---

## 🔐 Configuración de Secretos en Infisical

El archivo local `.env` solo requiere las credenciales de conexión de la máquina con Infisical:
```env
INFISICAL_PROJECT_ID=f41cf578-44df-4fda-aad2-180d39b4843c
INFISICAL_CLIENT_ID=43508662-5a9b-4a21-b512-1cf09a1f924a
INFISICAL_CLIENT_SECRET=tu_client_secret_aqui
INFISICAL_ENVIRONMENT=dev
INFISICAL_HOST=https://app.infisical.com
```

Todos los datos sensibles se gestionan en la bóveda de Infisical:
* `DATABASE_URL`: Cadena de conexión de PostgreSQL Aiven Cloud (`postgres://avnadmin:...@f2t-...aivencloud.com:27481/defaultdb?sslmode=require`).
* `RSA_PRIVATE_KEY_PEM`: Clave privada RSA en formato PEM (solo en memoria RAM).
* `AUTH_SECRET_KEY`: Pepper secreto para las contraseñas de usuarios con bcrypt.
* `HASH_ALGORITHM`: Algoritmo de hash (`bcrypt`).
* `RSA_PUBLIC_KEY_PEM`: (Opcional) Clave pública en la nube.

---

## 🔒 Hash de Terminal MT5 Obligatorio (Anti-Sharing)

Para evitar que los usuarios compartan sus licencias o usen el Expert Advisor en múltiples computadoras con la misma cuenta, **el Hash de Terminal es 100% obligatorio** en cada emisión.

### ¿Qué es el Hash de Terminal?
Es el identificador hexadecimal único de 32 caracteres que MetaTrader 5 asigna a la carpeta de datos (`TERMINAL_DATA_PATH`) de esa instalación específica en Windows:
```text
C:\Users\<Usuario>\AppData\Roaming\MetaQuotes\Terminal\<32_HEX_HASH>
```

Se obtiene en MQL5 mediante:
```mql5
string data_path = TerminalInfoString(TERMINAL_DATA_PATH);
// El último directorio corresponde al hash de 32 caracteres hexadecimales
```

El token generado contiene este campo y el validador rechaza cualquier licencia que no incluya o no coincida con el hash de la terminal.

