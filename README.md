# 🛡️ F2T Administrador de Licencias

Aplicación de escritorio desarrollada con **PyQt6**, **SQLAlchemy** y **PostgreSQL en la Nube (Aiven Cloud)** para generar, administrar, validar y exportar licencias criptográficas asimétricas (RSA-2048) para asesores expertos (EAs) e indicadores en **MetaTrader 5 (MQL5)**.

---

## ✨ Características Principales

### 1. Interfaz Gráfica de Escritorio (PyQt6)
* **Dashboard con métricas en tiempo real**: Total de Licencias, Activas, Por Expirar (7 días o menos) y Expiradas.
* **Tabla interactiva y filtros avanzados**: Búsqueda en tiempo real por número de cuenta MT5, nombre del cliente, broker o notas. Filtros por estado de vigencia.
* **Acciones rápidas con clic derecho o barra de herramientas**: Generar, editar, eliminar, copiar token, exportar archivo `.key` y verificar licencias.

### 2. Bloqueo de Múltiples Instancias (`Single-Instance Guard`)
* Impide la ejecución simultánea de dos copias del programa en la misma computadora.
* Utiliza sockets IPC locales (`QLocalSocket` y `QLocalServer`) integrados con *Named Pipes* del kernel de Windows.
* Si un usuario intenta abrir una segunda ventana, se le notifica mediante un cuadro de diálogo y el nuevo proceso se cierra de inmediato, previniendo condiciones de carrera y bloqueos de archivos.

### 3. Control de Sesión Única en la Base de Datos (`Anti-Account Sharing`)
* **Acceso Exclusivo por Cuenta**: Cada usuario (Admin o Manager) solo puede tener una sesión abierta a la vez en todo el sistema.
* **Detección Concurrente**: Si un usuario intenta iniciar sesión desde otra máquina mientras ya está activo, el sistema bloquea el acceso e informa el nombre del equipo que tiene la sesión abierta y la hora del último latido.
* **Heartbeat & Auto-Recuperación (120s)**: La aplicación envía un pulso automático cada 30 segundos. Si una máquina sufre un corte de luz o un apagón imprevisto, la sesión expira a los 120 segundos de inactividad, permitiendo que el usuario ingrese nuevamente sin requerir intervención técnica.
* **Monitoreo y Liberación Remota**: En el panel de administración de usuarios, los administradores pueden ver en tiempo real qué operador está conectado (`🟢 En línea (NOMBRE-PC)` o `⚪ Desconectado`) y forzar la desconexión mediante el botón **"Liberar Sesión"**.

### 4. Control de Acceso Basado en Roles (`Admin` vs `Manager`)
* **Manager**: Control sobre el ciclo de vida de las licencias (crear, editar, eliminar, exportar y verificar).
* **Administrador**: Control total del sistema más gestión de usuarios y accesos (crear usuarios, editar perfiles, asignar roles `admin`/`manager`, cambiar contraseñas, desactivar cuentas y liberar sesiones activas).
* **Seguridad de Credenciales**: Cifrado con **bcrypt** reforzado con un *secret pepper* custodiado en **Infisical Cloud**.

### 5. Base de Datos en la Nube (Aiven PostgreSQL) & Migraciones
* Base de datos centralizada con cifrado forzado en tránsito (**SSL/TLS**) y en reposo (AES-256).
* Cadena de conexión custodiada exclusivamente en **Infisical Cloud** (`DATABASE_URL`).
* Control de versiones de esquema con **Alembic** y auto-migración integrada al inicio de la aplicación.

### 6. Criptografía Asimétrica RSA-2048 & MQL5
* Firmas digitales asimétricas seguras (RSA 2048-bit con SHA-256 y padding PKCS#1 v1.5).
* Clave privada custodiada estrictamente en la memoria RAM de Infisical (sin almacenar archivos `.pem` privados en disco).
* Exportación de módulos públicos y generación de archivos `license.key` listos para la carpeta `MQL5/Files`.

### 7. Seguridad Reforzada en MetaTrader 5 (Anti-Sharing & Anti-Portable)
* **Hash de Terminal Obligatorio**: Cada licencia se firma vinculada exclusivamente al identificador único de instalación de MT5 (`TERMINAL_DATA_PATH`), impidiendo que un cliente use el bot en computadoras no autorizadas aunque comparta sus credenciales de broker.
* **Bloqueo de Modo Portable**: El validador `LicenseValidator.mqh` detecta y rechaza la ejecución si MetaTrader 5 está corriendo en modo portable (`/portable`), evitando que se copie la carpeta completa a un pendrive para evadir la licencia.
* **Privacidad de Logs**: En caso de fallo de validación por máquina no autorizada, no se expone el hash en los logs públicos de la terminal; se emite una alerta genérica y se deriva al cliente a soporte técnico.

---

## 🚀 Cómo Ejecutar en Desarrollo

### Opción 1: Acceso Rápido con 1 Clic (Windows)
Haz doble clic sobre:
```text
run_app.bat
```
El script verificará e instalará automáticamente las dependencias si faltan y lanzará la interfaz gráfica.

### Opción 2: Desde la Terminal
```bash
pip install -r requirements.txt
python src/license_validator/app.py
```

---

## 📦 Empaquetado a Ejecutable (.EXE) e Instalador (Inno Setup)

### Paso 1: Generar el Ejecutable Autónomo (.exe)
Utiliza el script automatizado [build_exe.bat](file:///mnt/c/Users/armando-miguel-tapia/Documents/Projects/f2t/license-validator/build_exe.bat) junto con la especificación [f2t_licencias.spec](file:///mnt/c/Users/armando-miguel-tapia/Documents/Projects/f2t/license-validator/f2t_licencias.spec):

1. En Windows, haz doble clic en `build_exe.bat` (o ejecuta `pyinstaller --clean f2t_licencias.spec`).
2. El script limpiará compilaciones previas, empaquetará la aplicación con su icono oficial `app_icon.ico`, copiará las configuraciones y generará la carpeta autónoma en:
   ```text
   dist\F2T-Licencias\F2T-Licencias.exe
   ```

---

### Paso 2: Crear el Instalador de Windows (Inno Setup)

Para distribuir la aplicación en un instalador profesional con asistente:

1. Descarga e instala [Inno Setup](https://jrsoftware.org/isdl.php).
2. Haz clic derecho sobre el archivo [installer_inno.iss](file:///mnt/c/Users/armando-miguel-tapia/Documents/Projects/f2t/license-validator/installer_inno.iss) en el explorador de Windows y selecciona **"Compile"**.
3. El instalador autónomo se creará automáticamente en:
   ```text
   dist_installer\F2T-Licencias-Setup.exe
   ```

**Características del instalador:**
* Asistente en español con estilo corporativo F2T.
* Instalación en `Archivos de Programa` (modo nativo 64 bits).
* Creación de accesos directos en el Menú Inicio y Escritorio con icono oficial.
* Registro de desinstalación en el Panel de Control de Windows.
* Compresión LZMA2 Ultra con comprobación de integridad.

---

## 🔐 Configuración de Secretos en Infisical

El archivo local `.env` solo contiene las credenciales de la máquina para autenticarse con Infisical:
```env
INFISICAL_PROJECT_ID=f41cf578-44df-4fda-aad2-180d39b4843c
INFISICAL_CLIENT_ID=43508662-5a9b-4a21-b512-1cf09a1f924a
INFISICAL_CLIENT_SECRET=tu_client_secret_aqui
INFISICAL_ENVIRONMENT=dev
INFISICAL_HOST=https://app.infisical.com
```

Todos los datos sensibles se gestionan en la bóveda de Infisical:
* `DATABASE_URL`: Cadena de conexión PostgreSQL Aiven Cloud con SSL requerido (`postgres://avnadmin:...@...aivencloud.com:27481/defaultdb?sslmode=require`).
* `RSA_PRIVATE_KEY_PEM`: Clave privada RSA-2048 (mantenida solo en memoria RAM).
* `AUTH_SECRET_KEY`: Pepper secreto para el hashing de contraseñas con bcrypt.
* `HASH_ALGORITHM`: Algoritmo de hash (`bcrypt`).
* `RSA_PUBLIC_KEY_PEM`: Clave pública correspondiente.

---

## 🔒 Hash de Terminal MT5 Obligatorio (Anti-Sharing)

Para evitar que los usuarios compartan sus licencias o usen el Asesor Experto en múltiples computadoras con la misma cuenta, **el Hash de Terminal es 100% obligatorio** en cada emisión.

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

El token generado contiene este campo firmado criptográficamente con RSA-2048, garantizando que el bot solo funcione en la computadora asignada.
