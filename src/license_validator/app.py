import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtNetwork import QLocalSocket, QLocalServer

from license_validator.database.db import init_db
from license_validator.database.user_repository import UserRepository
from license_validator.gui.icons import get_app_icon
from license_validator.gui.login_dialog import LoginDialog
from license_validator.gui.main_window import MainWindow

SINGLE_INSTANCE_SERVER_NAME = "f2t_license_validator_single_instance_lock"


def main() -> None:
    # Windows Taskbar Grouping Fix: Asegura que el icono de la barra de tareas sea el de la app y no el de python.exe
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("f2t.license_validator.app.1.0")
        except Exception:
            pass

    # High DPI settings
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    # Create QApplication first so error dialogs can be displayed if needed
    app = QApplication(sys.argv)
    app.setApplicationName("F2T Administrador de licencias")
    app.setApplicationDisplayName("F2T Administrador de licencias")

    # Set Application & Taskbar Icon
    app_icon = get_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    # Single Instance Guard: Prevent running multiple instances on the same machine
    single_socket = QLocalSocket()
    single_socket.connectToServer(SINGLE_INSTANCE_SERVER_NAME)
    if single_socket.waitForConnected(400):
        single_socket.close()
        QMessageBox.warning(
            None,
            "Aplicación Ya en Ejecución",
            "F2T Administrador de Licencias ya se encuentra abierto en este equipo.\n\n"
            "No se permite tener dos instancias de la aplicación abiertas al mismo tiempo.",
        )
        sys.exit(0)

    # Start local server to hold the single-instance lock
    local_server = QLocalServer()
    local_server.removeServer(SINGLE_INSTANCE_SERVER_NAME)
    local_server.listen(SINGLE_INSTANCE_SERVER_NAME)

    # Initialize Database with Retry / Graceful Error Dialog
    while True:
        try:
            init_db()
            user_repo = UserRepository()
            break
        except Exception as e:
            reply = QMessageBox.critical(
                None,
                "Error de Conexión a la Base de Datos",
                "No se pudo conectar con la base de datos en la nube:\n\n"
                f"{e}\n\n"
                "Causas comunes:\n"
                "1. Sin conexión a Internet o DNS no resuelve el host.\n"
                "2. Intente cambiar su servidor DNS a 8.8.8.8 (Google) o 1.1.1.1 (Cloudflare).\n"
                "3. En Windows ejecute: ipconfig /flushdns",
                QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Retry,
            )
            if reply != QMessageBox.StandardButton.Retry:
                sys.exit(1)

    # Authentication Loop: allows logging out and logging back in
    while True:
        login_dlg = LoginDialog(user_repo=user_repo)
        if not login_dlg.exec():
            # User closed login dialog or clicked exit
            break

        current_user = login_dlg.authenticated_user
        if not current_user:
            break

        main_win = MainWindow(
            current_user=current_user,
            user_repo=user_repo,
            session_token=login_dlg.session_token,
        )

        # Flag to detect if logout was requested
        logged_out = [False]

        def on_logout():
            logged_out[0] = True

        main_win.logout_requested.connect(on_logout)
        main_win.show()

        app.exec()

        if not logged_out[0]:
            # Normal close of window (not logout) -> exit app
            break

    sys.exit(0)


if __name__ == "__main__":
    main()
