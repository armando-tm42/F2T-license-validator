from typing import Optional

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QMessageBox,
    QGroupBox,
    QApplication,
)

from license_validator.core.crypto import CryptoService
from license_validator.core.secrets import SecretsManager
from license_validator.gui.icons import get_icon


class KeysDialog(QDialog):
    """Dialog to manage RSA cryptographic keys and export public modulus for MQL5."""

    def __init__(self, parent=None, crypto_service: Optional[CryptoService] = None) -> None:
        super().__init__(parent)
        self.crypto_service = crypto_service or CryptoService()

        self.setWindowTitle("Administración de Llaves RSA & MQL5")
        self.setMinimumSize(640, 500)
        self.setModal(True)

        self._init_ui()
        self._refresh_status()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QVBoxLayout()
        title = QLabel("Criptografía & Llaves RSA")
        title.setObjectName("HeaderTitle")
        subtitle = QLabel(
            "Administra el par de llaves asimétricas (2048-bit) para firmar licencias y vincular con MQL5."
        )
        subtitle.setObjectName("HeaderSubtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        layout.addLayout(header)

        # Status Group
        status_group = QGroupBox("Estado de los Archivos de Claves")
        status_layout = QVBoxLayout(status_group)
        status_layout.setSpacing(8)

        self.label_priv_status = QLabel()
        self.label_pub_status = QLabel()
        status_layout.addWidget(self.label_priv_status)
        status_layout.addWidget(self.label_pub_status)

        layout.addWidget(status_group)

        # MQL5 Modulus N Group
        mql5_group = QGroupBox("Clave Pública para MetaTrader 5")
        mql5_layout = QVBoxLayout(mql5_group)
        mql5_layout.setSpacing(10)

        help_label = QLabel(
            "Copia este valor y pégalo en la línea 9 "
            "de tu archivo <b>LicenseValidator.mqh</b> en MetaTrader 5:"
        )
        help_label.setWordWrap(True)
        mql5_layout.addWidget(help_label)

        self.text_hex = QPlainTextEdit()
        self.text_hex.setReadOnly(True)
        self.text_hex.setStyleSheet(
            "font-family: Consolas, 'Courier New', monospace; font-size: 11px; background-color: #f1f5f9;"
        )
        self.text_hex.setMaximumHeight(110)
        mql5_layout.addWidget(self.text_hex)

        mql5_actions = QHBoxLayout()
        self.btn_copy_hex = QPushButton("Copiar llave pública")
        self.btn_copy_hex.setObjectName("PrimaryButton")
        self.btn_copy_hex.setIcon(get_icon("copy", color="#ffffff", size=18))
        self.btn_copy_hex.setIconSize(QSize(18, 18))
        self.btn_copy_hex.clicked.connect(self._on_copy_hex)
        mql5_actions.addWidget(self.btn_copy_hex)
        mql5_actions.addStretch()
        mql5_layout.addLayout(mql5_actions)

        layout.addWidget(mql5_group)

        # Bottom Close Button
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        bottom_row.addWidget(btn_close)
        layout.addLayout(bottom_row)

    def _refresh_status(self) -> None:
        has_priv = self.crypto_service.has_private_key()
        has_pub = self.crypto_service.has_public_key()

        # Check private key status (Infisical only)
        if has_priv:
            self.label_priv_status.setText(
                "<span style='color: #10b981; font-size: 14px;'>■</span> <b>Clave Privada:</b> Conectada <b>Infisical</b>"
            )
        else:
            self.label_priv_status.setText(
                "<span style='color: #ef4444; font-size: 14px;'>■</span> <b>Clave Privada:</b> No disponible en Infisical. Verifica tu conexión e INFISICAL_CLIENT_SECRET en .env"
            )

        # Check public key status
        if has_pub:
            # Determine origin
            if SecretsManager.get_secret("RSA_PUBLIC_KEY_PEM"):
                source_desc = "Infisical Cloud (RSA_PUBLIC_KEY_PEM)"
            elif has_priv:
                source_desc = "Sincronizada con Clave Privada (Infisical)"
            else:
                source_desc = f"Archivo local ({self.crypto_service.public_key_path})"

            self.label_pub_status.setText(
                f"<span style='color: #10b981; font-size: 14px;'>■</span> <b>Clave Pública:</b> Disponible ({source_desc})"
            )
            try:
                hex_str = self.crypto_service.get_public_key_hex_for_mql5()
                self.text_hex.setPlainText(hex_str)
                self.btn_copy_hex.setEnabled(True)
            except Exception as e:
                self.text_hex.setPlainText(f"Error al leer clave pública: {e}")
                self.btn_copy_hex.setEnabled(False)
        else:
            self.label_pub_status.setText(
                "<span style='color: #ef4444; font-size: 14px;'>■</span> <b>Clave Pública:</b> No disponible en Infisical ni en archivo local"
            )
            self.text_hex.setPlainText("No se encontró la clave pública.")
            self.btn_copy_hex.setEnabled(False)

    def _on_copy_hex(self) -> None:
        hex_text = self.text_hex.toPlainText().strip()
        if not hex_text:
            return
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(hex_text)
            QMessageBox.information(
                self,
                "Copiado",
                "Módulo HEX copiado al portapapeles.\nPégalo en LicenseValidator.mqh en MetaTrader 5.",
            )
