from datetime import date, datetime, timedelta
from typing import Optional

from PyQt6.QtCore import Qt, QDate, QSize
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QDateEdit,
    QTextEdit,
    QPushButton,
    QMessageBox,
    QGroupBox,
    QFrame,
)

from license_validator.core.crypto import CryptoService
from license_validator.database.models import License
from license_validator.gui.icons import get_icon


class LicenseDialog(QDialog):
    """Dialog to create or edit a license with real-time preview and digital signature."""

    def __init__(
        self,
        parent=None,
        license_obj: Optional[License] = None,
        crypto_service: Optional[CryptoService] = None,
    ) -> None:
        super().__init__(parent)
        self.license_obj = license_obj
        self.crypto_service = crypto_service or CryptoService()
        self.result_data = None

        is_edit = self.license_obj is not None
        title = "Editar Licencia de MetaTrader 5" if is_edit else "Nueva Licencia de MetaTrader 5"
        self.setWindowTitle(title)
        self.setMinimumSize(560, 480)
        self.setModal(True)

        self._init_ui()
        if is_edit:
            self._load_license_data()
        else:
            self._set_defaults()

        self._update_preview()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header Title
        header_layout = QVBoxLayout()
        title_text = "Modificar Licencia" if self.license_obj else "Generar Nueva Licencia"
        header_title = QLabel(title_text)
        header_title.setObjectName("HeaderTitle")
        header_subtitle = QLabel(
            "Configura la cuenta de MetaTrader 5 y la vigencia. El token será firmado criptográficamente con RSA-2048."
        )
        header_subtitle.setObjectName("HeaderSubtitle")
        header_layout.addWidget(header_title)
        header_layout.addWidget(header_subtitle)
        main_layout.addLayout(header_layout)

        # Form Container
        form_group = QGroupBox("Datos de la Licencia")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(14)
        form_layout.setContentsMargins(15, 15, 15, 15)

        # 1. Cliente / Alias
        self.input_client = QLineEdit()
        self.input_client.setPlaceholderText("Ej: Juan Pérez / Empresa X (Opcional)")
        self.input_client.textChanged.connect(self._update_preview)
        form_layout.addRow("Cliente / Titular:", self.input_client)

        # 2. Cuenta MT5 (Account number)
        self.input_account = QLineEdit()
        self.input_account.setPlaceholderText("Ej: 138976 (Solo números)")
        self.input_account.textChanged.connect(self._update_preview)
        form_layout.addRow("Cuenta MT5 (*):", self.input_account)

        # 3. Hash de Terminal / Instalación MT5 (Obligatorio)
        self.input_terminal = QLineEdit()
        self.input_terminal.setPlaceholderText("Ej: D0E8209F77C8CF37AD8BF550E51FF075 (32 hex)")
        self.input_terminal.setToolTip(
            "Identificador único de la instalación MT5 del cliente (carpeta TERMINAL_DATA_PATH).\n"
            "Obligatorio para evitar que compartan la cuenta y el EA con otras máquinas."
        )
        self.input_terminal.textChanged.connect(self._update_preview)
        form_layout.addRow("Hash Terminal MT5 (*):", self.input_terminal)

        # 3. Expiración
        date_container = QVBoxLayout()
        date_row = QHBoxLayout()
        self.date_expires = QDateEdit()
        self.date_expires.setCalendarPopup(True)
        self.date_expires.setDisplayFormat("yyyy-MM-dd")
        self.date_expires.dateChanged.connect(self._update_preview)
        date_row.addWidget(self.date_expires)

        # Quick date preset buttons (eliminada la opción 2099)
        btn_30d = QPushButton("+30 Días")
        btn_30d.clicked.connect(lambda: self._add_days(30))
        btn_90d = QPushButton("+90 Días")
        btn_90d.clicked.connect(lambda: self._add_days(90))
        btn_1y = QPushButton("+1 Año")
        btn_1y.clicked.connect(lambda: self._add_days(365))

        date_row.addWidget(btn_30d)
        date_row.addWidget(btn_90d)
        date_row.addWidget(btn_1y)
        date_container.addLayout(date_row)
        form_layout.addRow("Fecha de Expiración (*):", date_container)

        # 4. Notas internas
        self.input_notes = QTextEdit()
        self.input_notes.setPlaceholderText("Notas adicionales, contacto, referencia de pago...")
        self.input_notes.setMaximumHeight(70)
        form_layout.addRow("Notas internas:", self.input_notes)

        main_layout.addWidget(form_group)

        # Live Preview Box
        preview_group = QGroupBox("Vista Previa del Payload de la Licencia (MQL5)")
        preview_layout = QVBoxLayout(preview_group)
        self.label_preview = QLabel()
        self.label_preview.setStyleSheet(
            "background-color: #f1f5f9; padding: 10px; border-radius: 6px; font-family: monospace; color: #0f172a;"
        )
        self.label_preview.setWordWrap(True)
        preview_layout.addWidget(self.label_preview)
        main_layout.addWidget(preview_group)

        # Buttons Row
        button_row = QHBoxLayout()
        button_row.addStretch()

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        button_row.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Guardar y Firmar Licencia")
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.setIcon(get_icon("save", color="#ffffff", size=18))
        self.btn_save.setIconSize(QSize(18, 18))
        self.btn_save.clicked.connect(self._on_save)
        button_row.addWidget(self.btn_save)

        main_layout.addLayout(button_row)

    def _set_defaults(self) -> None:
        today = date.today()
        # Default expiration is 1 year from now
        default_exp = today + timedelta(days=365)
        self.date_expires.setDate(QDate(default_exp.year, default_exp.month, default_exp.day))

    def _load_license_data(self) -> None:
        if not self.license_obj:
            return
        self.input_client.setText(self.license_obj.client_name or "")
        self.input_account.setText(str(self.license_obj.account))
        self.input_terminal.setText(getattr(self.license_obj, "terminal_hash", "") or "")
        self.input_notes.setPlainText(self.license_obj.notes or "")

        try:
            d = datetime.strptime(self.license_obj.expires_at, "%Y-%m-%d").date()
            self.date_expires.setDate(QDate(d.year, d.month, d.day))
        except Exception:
            pass

    def _add_days(self, days: int) -> None:
        current_date = date.today()
        new_date = current_date + timedelta(days=days)
        self.date_expires.setDate(QDate(new_date.year, new_date.month, new_date.day))

    def _update_preview(self) -> None:
        account_str = self.input_account.text().strip() or "00000000"
        expires_str = self.date_expires.date().toString("yyyy-MM-dd")
        term_str = self.input_terminal.text().strip().upper()

        if term_str:
            preview_text = f'{{\n  "account": {account_str},\n  "expires": "{expires_str}",\n  "terminal_hash": "{term_str}"\n}}'
        else:
            preview_text = f'{{\n  "account": {account_str},\n  "expires": "{expires_str}"\n}}'
        self.label_preview.setText(f"JSON Payload:\n{preview_text}")

    def _on_save(self) -> None:
        account_text = self.input_account.text().strip()
        if not account_text:
            QMessageBox.warning(self, "Campo Requerido", "Por favor ingresa el número de cuenta de MetaTrader 5.")
            self.input_account.setFocus()
            return

        try:
            account = int(account_text)
            if account <= 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(
                self, "Valor Inválido", "El número de cuenta de MT5 debe ser un número entero positivo."
            )
            self.input_account.setFocus()
            return

        expires = self.date_expires.date().toString("yyyy-MM-dd")
        client_name = self.input_client.text().strip()
        terminal_hash = self.input_terminal.text().strip().upper()
        notes = self.input_notes.toPlainText().strip()

        if not terminal_hash:
            QMessageBox.warning(
                self,
                "Campo Requerido",
                "El Hash de Terminal MT5 es obligatorio.\n\n"
                "Ingresa el identificador único de la instalación de MetaTrader 5 del cliente para evitar el uso no autorizado en otras máquinas.",
            )
            self.input_terminal.setFocus()
            return

        # Ensure RSA private key exists in Infisical
        if not self.crypto_service.has_private_key():
            QMessageBox.critical(
                self,
                "Firma Digital No Disponible",
                "No se puede emitir la licencia porque la clave privada no está disponible en Infisical.\n\n"
                "Verifica que:\n"
                "1. Tengas conexión a internet.\n"
                "2. 'INFISICAL_CLIENT_SECRET' esté configurado en tu archivo .env.\n"
                "3. El secreto 'RSA_PRIVATE_KEY_PEM' exista en tu proyecto de Infisical.",
            )
            return

        # Sign the token with account, expiration and mandatory terminal_hash
        try:
            token = self.crypto_service.issue_license(
                account=account,
                expires=expires,
                terminal_hash=terminal_hash,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error de Firma", f"No se pudo generar la firma digital: {e}")
            return

        self.result_data = {
            "account": account,
            "broker": getattr(self.license_obj, "broker", "") if self.license_obj else "",
            "tier": getattr(self.license_obj, "tier", "") if self.license_obj else "",
            "expires_at": expires,
            "client_name": client_name,
            "terminal_hash": terminal_hash,
            "notes": notes,
            "token": token,
        }

        self.accept()
