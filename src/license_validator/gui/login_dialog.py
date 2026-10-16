import socket
from typing import Optional

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QGroupBox,
    QFrame,
)

from license_validator.database.models import User
from license_validator.database.user_repository import UserRepository
from license_validator.gui.icons import get_icon, get_app_icon


class LoginDialog(QDialog):
    """Authentication dialog for logging in or setting up the initial admin user."""

    def __init__(self, parent=None, user_repo: Optional[UserRepository] = None) -> None:
        super().__init__(parent)
        self.user_repo = user_repo or UserRepository()
        self.authenticated_user: Optional[User] = None
        self.session_token: Optional[str] = None

        self.user_count = self.user_repo.count()
        self.is_setup_mode = self.user_count == 0

        self.setWindowTitle(
            "Configuración Inicial - Crear Administrador" if self.is_setup_mode else "Iniciar Sesión"
        )
        app_icon = get_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)

        self.setFixedSize(460, 480 if self.is_setup_mode else 380)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header Box
        header = QVBoxLayout()
        header.setSpacing(6)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_logo = QLabel()
        app_icon = get_app_icon()
        lbl_logo.setPixmap(app_icon.pixmap(44, 44))
        lbl_logo.setFixedSize(44, 44)
        lbl_logo.setScaledContents(True)
        header.addWidget(lbl_logo, alignment=Qt.AlignmentFlag.AlignCenter)

        title = QLabel(
            "Bienvenido a F2T Administrador de licencias" if self.is_setup_mode else "Acceso al Sistema"
        )
        title.setObjectName("HeaderTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_text = (
            "No se encontraron usuarios. Por favor crea la cuenta del Administrador principal:"
            if self.is_setup_mode
            else "Ingresa tus credenciales para administrar las licencias."
        )
        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("HeaderSubtitle")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header.addWidget(title)
        header.addWidget(subtitle)
        layout.addLayout(header)

        # Card / Form Container
        form_card = QFrame()
        form_card.setObjectName("HeaderCard")
        form_layout = QFormLayout(form_card)
        form_layout.setSpacing(14)
        form_layout.setContentsMargins(16, 16, 16, 16)

        if self.is_setup_mode:
            self.input_name = QLineEdit()
            self.input_name.setPlaceholderText("Ej: Armando Tapia")
            form_layout.addRow("Nombre Completo (*):", self.input_name)

        self.input_username = QLineEdit()
        self.input_username.setPlaceholderText("Ej: admin")
        form_layout.addRow("Nombre de Usuario (*):", self.input_username)

        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_password.setPlaceholderText("Tu contraseña")
        form_layout.addRow("Contraseña (*):", self.input_password)

        if self.is_setup_mode:
            self.input_confirm_password = QLineEdit()
            self.input_confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
            self.input_confirm_password.setPlaceholderText("Repite tu contraseña")
            form_layout.addRow("Confirmar Contraseña (*):", self.input_confirm_password)

        layout.addWidget(form_card)

        # Feedback Label
        self.lbl_feedback = QLabel()
        self.lbl_feedback.setStyleSheet("color: #dc2626; font-size: 12px; font-weight: 500;")
        self.lbl_feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_feedback.setVisible(False)
        layout.addWidget(self.lbl_feedback)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_exit = QPushButton("Salir")
        self.btn_exit.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_exit)

        action_text = "Crear Administrador y Entrar" if self.is_setup_mode else "Ingresar"
        self.btn_submit = QPushButton(action_text)
        self.btn_submit.setObjectName("PrimaryButton")
        self.btn_submit.setIcon(get_icon("user", color="#ffffff", size=18))
        self.btn_submit.setIconSize(QSize(18, 18))
        self.btn_submit.clicked.connect(self._on_submit)
        btn_layout.addWidget(self.btn_submit)

        layout.addLayout(btn_layout)

        # Connect Enter key to submit
        self.input_username.returnPressed.connect(self._on_submit)
        self.input_password.returnPressed.connect(self._on_submit)
        if self.is_setup_mode:
            self.input_name.returnPressed.connect(self._on_submit)
            self.input_confirm_password.returnPressed.connect(self._on_submit)

    def _show_error(self, message: str) -> None:
        self.lbl_feedback.setText(message)
        self.lbl_feedback.setVisible(True)

    def _on_submit(self) -> None:
        self.lbl_feedback.setVisible(False)

        username = self.input_username.text().strip()
        password = self.input_password.text().strip()

        if self.is_setup_mode:
            name = self.input_name.text().strip()
            confirm = self.input_confirm_password.text().strip()

            if not name:
                self._show_error("Por favor ingresa tu nombre completo.")
                self.input_name.setFocus()
                return

            if not username:
                self._show_error("Por favor ingresa un nombre de usuario.")
                self.input_username.setFocus()
                return

            if len(password) < 4:
                self._show_error("La contraseña debe tener al menos 4 caracteres.")
                self.input_password.setFocus()
                return

            if password != confirm:
                self._show_error("Las contraseñas no coinciden.")
                self.input_confirm_password.setFocus()
                return

            try:
                new_admin = self.user_repo.create(
                    username=username,
                    name=name,
                    password=password,
                    role="admin",
                )
                device_name = socket.gethostname()
                self.session_token = self.user_repo.start_session_for_user(new_admin.id, device_name)
                self.authenticated_user = new_admin
                QMessageBox.information(
                    self,
                    "Administrador Creado",
                    f"¡Bienvenido, {name}!\nTu cuenta de Administrador ha sido configurada exitosamente.",
                )
                self.accept()
            except Exception as e:
                self._show_error(f"Error al crear usuario: {e}")
                return

        else:
            # Login Mode
            if not username or not password:
                self._show_error("Por favor completa el usuario y la contraseña.")
                return

            device_name = socket.gethostname()
            success, user, session_token, err_msg = self.user_repo.authenticate_and_start_session(
                username=username,
                password=password,
                device_name=device_name,
            )
            if not success:
                self._show_error(err_msg or "Usuario o contraseña incorrectos.")
                if "sesión abierta" in (err_msg or "").lower():
                    QMessageBox.warning(
                        self,
                        "Acceso Denegado - Sesión en Uso",
                        err_msg,
                    )
                self.input_password.selectAll()
                self.input_password.setFocus()
                return

            self.authenticated_user = user
            self.session_token = session_token
            self.accept()
