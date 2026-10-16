import json
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QMessageBox,
    QGroupBox,
    QFileDialog,
    QFormLayout,
)

from license_validator.core.crypto import CryptoService
from license_validator.gui.icons import get_icon


class VerifyDialog(QDialog):
    """Dialog to test, inspect and verify license tokens and license.key files."""

    def __init__(
        self,
        parent=None,
        crypto_service: Optional[CryptoService] = None,
        initial_token: str = "",
    ) -> None:
        super().__init__(parent)
        self.crypto_service = crypto_service or CryptoService()
        self.initial_token = initial_token

        self.setWindowTitle("Verificar Licencia")
        self.setMinimumSize(580, 480)
        self.setModal(True)

        self._init_ui()
        if self.initial_token:
            self.text_token.setPlainText(self.initial_token)
            self._verify_token()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QVBoxLayout()
        title = QLabel("Verificar Licencia")
        title.setObjectName("HeaderTitle")
        subtitle = QLabel(
            "Valida la autenticidad criptográfica y vigencia de cualquier licencia o archivo 'license.key' con la clave pública."
        )
        subtitle.setObjectName("HeaderSubtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        layout.addLayout(header)

        # Input Group
        input_group = QGroupBox("Token de Licencia")
        input_layout = QVBoxLayout(input_group)

        self.text_token = QPlainTextEdit()
        self.text_token.setPlaceholderText("Pega aquí la cadena del token (<base64_payload>.<base64_firma>)...")
        self.text_token.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        self.text_token.setMaximumHeight(90)
        input_layout.addWidget(self.text_token)

        action_row = QHBoxLayout()
        self.btn_load_file = QPushButton("Cargar archivo license.key...")
        self.btn_load_file.setIcon(get_icon("copy", color="#334155", size=18))
        self.btn_load_file.setIconSize(QSize(18, 18))
        self.btn_load_file.clicked.connect(self._load_from_file)
        action_row.addWidget(self.btn_load_file)

        self.btn_verify = QPushButton("Verificar Licencia")
        self.btn_verify.setObjectName("PrimaryButton")
        self.btn_verify.setIcon(get_icon("verify", color="#ffffff", size=18))
        self.btn_verify.setIconSize(QSize(18, 18))
        self.btn_verify.clicked.connect(self._verify_token)
        action_row.addWidget(self.btn_verify)
        action_row.addStretch()

        input_layout.addLayout(action_row)
        layout.addWidget(input_group)

        # Results Group
        self.result_group = QGroupBox("Resultado de la Verificación")
        res_layout = QVBoxLayout(self.result_group)

        self.label_status = QLabel("Ingresa un token y presiona 'Verificar Licencia'.")
        self.label_status.setStyleSheet("font-size: 14px; font-weight: bold; padding: 6px;")
        res_layout.addWidget(self.label_status)

        self.form_details = QFormLayout()
        self.form_details.setSpacing(10)
        self.val_account = QLabel("-")
        self.val_expires = QLabel("-")
        self.val_terminal = QLabel("-")

        self.form_details.addRow("Cuenta MT5:", self.val_account)
        self.form_details.addRow("Fecha de Expiración:", self.val_expires)
        self.form_details.addRow("Hash de Terminal:", self.val_terminal)
        res_layout.addLayout(self.form_details)

        self.text_decoded_json = QPlainTextEdit()
        self.text_decoded_json.setReadOnly(True)
        self.text_decoded_json.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 11px; background-color: #f1f5f9;"
        )
        self.text_decoded_json.setMaximumHeight(90)
        res_layout.addWidget(QLabel("Payload Decodificado (JSON):"))
        res_layout.addWidget(self.text_decoded_json)

        layout.addWidget(self.result_group)

        # Close
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        bottom_row.addWidget(btn_close)
        layout.addLayout(bottom_row)

    def _load_from_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de licencia",
            "",
            "Archivos de Licencia (*.key *.txt);;Todos los archivos (*.*)",
        )
        if file_path:
            try:
                content = Path(file_path).read_text(encoding="utf-8").strip()
                self.text_token.setPlainText(content)
                self._verify_token()
            except Exception as e:
                QMessageBox.critical(self, "Error al leer archivo", f"No se pudo leer el archivo: {e}")

    def _verify_token(self) -> None:
        token = self.text_token.toPlainText().strip()
        if not token:
            QMessageBox.warning(self, "Token Vacío", "Por favor ingresa o carga un token para verificar.")
            return

        is_valid, payload, msg = self.crypto_service.verify_token(token)

        if payload:
            self.val_account.setText(str(payload.get("account", "-")))
            self.val_expires.setText(str(payload.get("expires", "-")))
            term = payload.get("terminal_hash")
            self.val_terminal.setText(str(term) if term else "⚠️ No presente (Token sin terminal)")
            self.text_decoded_json.setPlainText(json.dumps(payload, indent=2))
        else:
            self.val_account.setText("-")
            self.val_expires.setText("-")
            self.val_terminal.setText("-")
            self.text_decoded_json.setPlainText("")

        if is_valid:
            if "EXPIRÓ" in msg or "terminal_hash" in msg:
                self.label_status.setText(f"⚠️ {msg}")
                self.label_status.setStyleSheet("color: #b45309; font-size: 14px; font-weight: bold;")
            else:
                self.label_status.setText(f"✅ {msg}")
                self.label_status.setStyleSheet("color: #15803d; font-size: 14px; font-weight: bold;")
        else:
            self.label_status.setText(f"❌ {msg}")
            self.label_status.setStyleSheet("color: #b91c1c; font-size: 14px; font-weight: bold;")
