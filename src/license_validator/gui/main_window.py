import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QFileDialog,
    QMenu,
    QApplication,
    QFrame,
    QAbstractItemView,
)

from license_validator.core.crypto import CryptoService
from license_validator.database.db import init_db, is_cloud_database, is_database_encrypted
from license_validator.database.models import License, User
from license_validator.database.repository import LicenseRepository
from license_validator.database.user_repository import UserRepository
from license_validator.gui.keys_dialog import KeysDialog
from license_validator.gui.license_dialog import LicenseDialog
from license_validator.gui.styles import MODERN_STYLE
from license_validator.gui.verify_dialog import VerifyDialog
from license_validator.gui.users_dialog import UsersDialog
from license_validator.gui.icons import get_icon, get_app_icon


class MainWindow(QMainWindow):
    """Main Application Window for MetaTrader 5 License Management."""

    logout_requested = pyqtSignal()

    def __init__(
        self,
        repo: Optional[LicenseRepository] = None,
        crypto_service: Optional[CryptoService] = None,
        current_user: Optional[User] = None,
        user_repo: Optional[UserRepository] = None,
        session_token: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.repo = repo or LicenseRepository()
        self.crypto_service = crypto_service or CryptoService()
        self.current_user = current_user
        self.user_repo = user_repo or UserRepository()
        self.session_token = session_token

        self.setWindowTitle("F2T Administrador de licencias")
        app_icon = get_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)

        self.setMinimumSize(980, 680)

        # Apply global styling
        self.setStyleSheet(MODERN_STYLE)

        self._init_ui()
        self._check_and_import_existing_key()
        self.refresh_data()

        # Heartbeat timer (every 30 seconds) to maintain active session
        if self.current_user and self.session_token:
            self.heartbeat_timer = QTimer(self)
            self.heartbeat_timer.timeout.connect(self._send_heartbeat)
            self.heartbeat_timer.start(30000)

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(18, 18, 18, 18)

        # 1. Header with Title & Stat Cards
        main_layout.addLayout(self._create_header_section())

        # 2. Main Toolbar Actions (New, Edit, Delete, Export, etc.)
        main_layout.addLayout(self._create_toolbar_section())

        # 3. Search and Filter Bar
        main_layout.addLayout(self._create_filter_section())

        # 4. Licenses Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Cliente / Titular",
            "Cuenta MT5",
            "Terminal MT5",
            "Expiración",
            "Estado",
            "Creado",
            "Notas",
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().resizeSection(0, 50)   # ID
        self.table.horizontalHeader().resizeSection(1, 160)  # Cliente
        self.table.horizontalHeader().resizeSection(2, 110)  # Cuenta
        self.table.horizontalHeader().resizeSection(3, 140)  # Terminal MT5
        self.table.horizontalHeader().resizeSection(4, 110)  # Expiracion
        self.table.horizontalHeader().resizeSection(5, 120)  # Estado
        self.table.horizontalHeader().resizeSection(6, 130)  # Creado
        self.table.horizontalHeader().resizeSection(7, 180)  # Notas

        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.itemDoubleClicked.connect(self._on_edit_license)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        main_layout.addWidget(self.table)

        # 5. Bottom Status Bar
        status_bar_layout = QHBoxLayout()
        status_bar_layout.setContentsMargins(2, 4, 2, 0)
        status_bar_layout.setSpacing(6)

        self.status_label = QLabel("Listo.")
        self.status_label.setStyleSheet("color: #64748b; font-size: 12px;")
        status_bar_layout.addWidget(self.status_label)

        status_bar_layout.addSpacing(14)

        self.status_db_icon = QLabel()
        status_bar_layout.addWidget(self.status_db_icon)

        self.status_db_label = QLabel()
        self.status_db_label.setStyleSheet("color: #475569; font-size: 12px;")
        status_bar_layout.addWidget(self.status_db_label)

        status_bar_layout.addStretch()
        main_layout.addLayout(status_bar_layout)

    def _create_header_section(self) -> QHBoxLayout:
        header_layout = QHBoxLayout()

        # Title Info
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        # Title Row with App Logo / Icon
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title_row.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        lbl_logo = QLabel()
        app_icon = get_app_icon()
        lbl_logo.setPixmap(app_icon.pixmap(36, 36))
        lbl_logo.setFixedSize(36, 36)
        lbl_logo.setScaledContents(True)
        title_row.addWidget(lbl_logo)

        app_title = QLabel("F2T Administrador de licencias")
        app_title.setObjectName("HeaderTitle")
        title_row.addWidget(app_title)

        title_box.addLayout(title_row)

        app_subtitle = QLabel("Gestor criptográfico de licencias y validación RSA")
        app_subtitle.setObjectName("HeaderSubtitle")
        title_box.addWidget(app_subtitle)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # User profile & Actions
        if self.current_user:
            user_card = QFrame()
            user_card.setObjectName("HeaderCard")
            user_layout = QHBoxLayout(user_card)
            user_layout.setContentsMargins(10, 6, 10, 6)
            user_layout.setSpacing(8)

            lbl_avatar = QLabel()
            lbl_avatar.setPixmap(get_icon("user", color="#2563eb", size=20).pixmap(20, 20))
            user_layout.addWidget(lbl_avatar)

            user_text_box = QVBoxLayout()
            user_text_box.setSpacing(1)
            self.lbl_user_name = QLabel(self.current_user.name)
            self.lbl_user_name.setStyleSheet("font-weight: bold; font-size: 13px; color: #0f172a;")
            
            role_badge = "ADMIN" if self.current_user.is_admin else "MANAGER"
            role_color = "#1d4ed8" if self.current_user.is_admin else "#475569"
            self.lbl_uname = QLabel(
                f"@{self.current_user.username} • <span style='color: {role_color}; font-weight: 700;'>{role_badge}</span>"
            )
            self.lbl_uname.setStyleSheet("font-size: 11px;")
            user_text_box.addWidget(self.lbl_user_name)
            user_text_box.addWidget(self.lbl_uname)
            user_layout.addLayout(user_text_box)

            # Manage Users Button (Solo visible para Administradores)
            self.btn_manage_users = QPushButton("Usuarios")
            self.btn_manage_users.setIcon(get_icon("user", color="#334155", size=16))
            self.btn_manage_users.setIconSize(QSize(16, 16))
            self.btn_manage_users.setToolTip("Administrar usuarios y permisos del sistema (Solo Admin)")
            self.btn_manage_users.clicked.connect(self._on_open_users)
            self.btn_manage_users.setVisible(bool(self.current_user.is_admin))
            user_layout.addWidget(self.btn_manage_users)

            # Logout Button
            btn_logout = QPushButton("Salir")
            btn_logout.setIcon(get_icon("logout", color="#dc2626", size=16))
            btn_logout.setIconSize(QSize(16, 16))
            btn_logout.setToolTip("Cerrar sesión actual")
            btn_logout.clicked.connect(self._on_logout)
            user_layout.addWidget(btn_logout)

            header_layout.addWidget(user_card)
            header_layout.addSpacing(12)

        # Stat Cards
        self.card_total = self._build_stat_card("Total Licencias", "0", "#0f172a")
        self.card_active = self._build_stat_card("Activas", "0", "#15803d")
        self.card_expiring = self._build_stat_card("Por Expirar", "0", "#b45309")
        self.card_expired = self._build_stat_card("Expiradas", "0", "#b91c1c")

        header_layout.addWidget(self.card_total)
        header_layout.addWidget(self.card_active)
        header_layout.addWidget(self.card_expiring)
        header_layout.addWidget(self.card_expired)

        return header_layout

    def _build_stat_card(self, title: str, value: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setObjectName("StatCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setObjectName("StatTitle")

        lbl_val = QLabel(value)
        lbl_val.setObjectName("StatValue")
        lbl_val.setStyleSheet(f"color: {color_hex}; font-size: 20px; font-weight: bold;")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        card.value_label = lbl_val  # Store reference for updates
        return card

    def _create_toolbar_section(self) -> QHBoxLayout:
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        # 1. Crear: debe ser un más (+)
        self.btn_new = QPushButton("Nueva Licencia")
        self.btn_new.setObjectName("PrimaryButton")
        self.btn_new.setIcon(get_icon("plus", color="#ffffff", size=18))
        self.btn_new.setIconSize(QSize(18, 18))
        self.btn_new.clicked.connect(self._on_new_license)
        toolbar.addWidget(self.btn_new)

        # Editar: lápiz
        self.btn_edit = QPushButton("Editar")
        self.btn_edit.setIcon(get_icon("edit", color="#334155", size=18))
        self.btn_edit.setIconSize(QSize(18, 18))
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self._on_edit_license)
        toolbar.addWidget(self.btn_edit)

        # 2. Eliminar: un signo de menos (-)
        self.btn_delete = QPushButton("Eliminar")
        self.btn_delete.setIcon(get_icon("minus", color="#dc2626", size=18))
        self.btn_delete.setIconSize(QSize(18, 18))
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._on_delete_license)
        toolbar.addWidget(self.btn_delete)

        toolbar.addSpacing(12)

        # 3. Guardar: el típico signo tipo rectángulo con puntas (disquete / save)
        self.btn_export = QPushButton("Guardar 'license.key'...")
        self.btn_export.setIcon(get_icon("save", color="#2563eb", size=18))
        self.btn_export.setIconSize(QSize(18, 18))
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._on_export_file)
        toolbar.addWidget(self.btn_export)

        # 4. Copiar: el signo de la hoja con una esquina doblada
        self.btn_copy_token = QPushButton("Copiar Token")
        self.btn_copy_token.setIcon(get_icon("copy", color="#334155", size=18))
        self.btn_copy_token.setIconSize(QSize(18, 18))
        self.btn_copy_token.setEnabled(False)
        self.btn_copy_token.clicked.connect(self._on_copy_token)
        toolbar.addWidget(self.btn_copy_token)

        toolbar.addStretch()

        # 5. Llaves RSA: un candado o una llave
        self.btn_keys = QPushButton("Llaves RSA & MQL5")
        self.btn_keys.setIcon(get_icon("lock", color="#334155", size=18))
        self.btn_keys.setIconSize(QSize(18, 18))
        self.btn_keys.clicked.connect(self._on_open_keys)
        toolbar.addWidget(self.btn_keys)

        # Verificar: escudo con verificación
        self.btn_verify = QPushButton("Verificar Licencia")
        self.btn_verify.setIcon(get_icon("verify", color="#334155", size=18))
        self.btn_verify.setIconSize(QSize(18, 18))
        self.btn_verify.clicked.connect(self._on_open_verify)
        toolbar.addWidget(self.btn_verify)

        return toolbar

    def _create_filter_section(self) -> QHBoxLayout:
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        self.input_search = QLineEdit()
        self.input_search.addAction(
            get_icon("search", color="#64748b", size=16),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self.input_search.setPlaceholderText("Buscar por titular, cuenta MT5 o terminal...")
        self.input_search.textChanged.connect(self.refresh_data)
        filter_layout.addWidget(self.input_search, stretch=3)

        # Status filter
        self.combo_status_filter = QComboBox()
        self.combo_status_filter.addItems(["Todos los estados", "Activa", "Por expirar", "Expirada"])
        self.combo_status_filter.currentIndexChanged.connect(self.refresh_data)
        filter_layout.addWidget(self.combo_status_filter, stretch=1)

        btn_clear = QPushButton("Limpiar")
        btn_clear.clicked.connect(self._clear_filters)
        filter_layout.addWidget(btn_clear)

        return filter_layout

    def _clear_filters(self) -> None:
        self.input_search.clear()
        self.combo_status_filter.setCurrentIndex(0)
        self.refresh_data()

    def _check_and_import_existing_key(self) -> None:
        """If database is empty and a local 'license.key' exists, auto-import it."""
        try:
            licenses = self.repo.get_all()
            if len(licenses) == 0:
                key_path = Path("license.key")
                if key_path.is_file():
                    token = key_path.read_text(encoding="utf-8").strip()
                    payload = CryptoService.decode_token_payload(token)
                    if payload and "account" in payload and "expires" in payload:
                        self.repo.create(
                            account=payload["account"],
                            expires_at=payload["expires"],
                            token=token,
                            client_name="Licencia Inicial Importada",
                            notes="Importada automáticamente desde license.key preexistente",
                        )
        except Exception:
            pass

    def refresh_data(self) -> None:
        search_text = self.input_search.text().strip()
        status_sel = self.combo_status_filter.currentText()

        status_filter = None if status_sel == "Todos los estados" else status_sel

        licenses = self.repo.get_all(
            search_query=search_text or None,
            status_filter=status_filter,
        )

        self.table.setRowCount(len(licenses))

        for row, lic in enumerate(licenses):
            # Store license ID in UserRole of first item
            item_id = QTableWidgetItem(str(lic.id))
            item_id.setData(Qt.ItemDataRole.UserRole, lic.id)
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item_client = QTableWidgetItem(lic.client_name or "(Sin titular)")
            item_account = QTableWidgetItem(str(lic.account))
            item_account.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Terminal cell
            term_hash = getattr(lic, "terminal_hash", "") or ""
            if term_hash:
                term_display = f"🔒 {term_hash[:10]}..." if len(term_hash) > 10 else f"🔒 {term_hash}"
                item_terminal = QTableWidgetItem(term_display)
                item_terminal.setToolTip(f"Vinculada a Terminal MT5:\n{term_hash}")
                item_terminal.setForeground(Qt.GlobalColor.darkBlue)
            else:
                item_terminal = QTableWidgetItem("⚠️ (Sin vincular)")
                item_terminal.setToolTip("Licencia antigua sin terminal_hash registrado.")
                item_terminal.setForeground(Qt.GlobalColor.darkYellow)
            item_terminal.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item_expires = QTableWidgetItem(lic.expires_at)
            item_expires.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Status cell
            status_text = lic.status
            if status_text == "Activa":
                status_display = f"● Activa ({lic.days_remaining}d)"
            elif status_text == "Por expirar":
                status_display = f"▲ Por expirar ({lic.days_remaining}d)"
            else:
                status_display = "✕ Expirada"

            item_status = QTableWidgetItem(status_display)
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Status coloring
            if status_text == "Activa":
                item_status.setForeground(Qt.GlobalColor.darkGreen)
            elif status_text == "Por expirar":
                item_status.setForeground(Qt.GlobalColor.darkYellow)
            else:
                item_status.setForeground(Qt.GlobalColor.red)

            created_str = lic.created_at.strftime("%Y-%m-%d %H:%M") if lic.created_at else ""
            item_created = QTableWidgetItem(created_str)
            item_created.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item_notes = QTableWidgetItem(lic.notes or "-")

            self.table.setItem(row, 0, item_id)
            self.table.setItem(row, 1, item_client)
            self.table.setItem(row, 2, item_account)
            self.table.setItem(row, 3, item_terminal)
            self.table.setItem(row, 4, item_expires)
            self.table.setItem(row, 5, item_status)
            self.table.setItem(row, 6, item_created)
            self.table.setItem(row, 7, item_notes)

        # Update stats
        stats = self.repo.get_stats()
        self.card_total.value_label.setText(str(stats["total"]))
        self.card_active.value_label.setText(str(stats["active"]))
        self.card_expiring.value_label.setText(str(stats["expiring"]))
        self.card_expired.value_label.setText(str(stats["expired"]))

        is_cloud = is_cloud_database()
        icon_color = "#10b981"
        self.status_db_icon.setPixmap(get_icon("lock", color=icon_color, size=15).pixmap(15, 15))
        db_badge = "PostgreSQL Cloud (Aiven) [SSL]" if is_cloud else "Base de Datos [Conectada]"
        self.status_label.setText(
            f"Mostrando {len(licenses)} de {stats['total']} licencias."
        )
        self.status_db_label.setText(f"Base de datos: <b>{db_badge}</b>")
        self._on_selection_changed()

    def _get_selected_license_id(self) -> Optional[int]:
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        item = self.table.item(row, 0)
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _on_selection_changed(self) -> None:
        has_sel = self._get_selected_license_id() is not None
        self.btn_edit.setEnabled(has_sel)
        self.btn_delete.setEnabled(has_sel)
        self.btn_export.setEnabled(has_sel)
        self.btn_copy_token.setEnabled(has_sel)

    def _on_new_license(self) -> None:
        dialog = LicenseDialog(self, crypto_service=self.crypto_service)
        if dialog.exec():
            data = dialog.result_data
            self.repo.create(
                account=data["account"],
                expires_at=data["expires_at"],
                token=data["token"],
                broker=data.get("broker", ""),
                tier=data.get("tier", ""),
                client_name=data.get("client_name", ""),
                notes=data.get("notes", ""),
                terminal_hash=data.get("terminal_hash", ""),
            )
            self.refresh_data()
            QMessageBox.information(
                self, "Licencia Creada", f"Licencia para la cuenta {data['account']} creada y firmada con éxito."
            )

    def _on_edit_license(self) -> None:
        lic_id = self._get_selected_license_id()
        if not lic_id:
            return
        lic = self.repo.get_by_id(lic_id)
        if not lic:
            return

        dialog = LicenseDialog(self, license_obj=lic, crypto_service=self.crypto_service)
        if dialog.exec():
            data = dialog.result_data
            self.repo.update(
                license_id=lic_id,
                account=data["account"],
                expires_at=data["expires_at"],
                token=data["token"],
                broker=data.get("broker", ""),
                tier=data.get("tier", ""),
                client_name=data.get("client_name", ""),
                notes=data.get("notes", ""),
                terminal_hash=data.get("terminal_hash", ""),
            )
            self.refresh_data()
            QMessageBox.information(self, "Licencia Actualizada", "Los cambios han sido guardados y re-firmados.")

    def _on_delete_license(self) -> None:
        lic_id = self._get_selected_license_id()
        if not lic_id:
            return
        lic = self.repo.get_by_id(lic_id)
        if not lic:
            return

        reply = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Estás seguro de que deseas eliminar la licencia de la cuenta {lic.account} "
            f"({lic.client_name or 'Sin titular'})?\n\nEsta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.repo.delete(lic_id)
            self.refresh_data()

    def _on_copy_token(self) -> None:
        lic_id = self._get_selected_license_id()
        if not lic_id:
            return
        lic = self.repo.get_by_id(lic_id)
        if not lic:
            return

        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(lic.token)
            QMessageBox.information(
                self,
                "Token Copiado",
                f"El token firmado para la cuenta {lic.account} ha sido copiado al portapapeles.",
            )

    def _on_export_file(self) -> None:
        lic_id = self._get_selected_license_id()
        if not lic_id:
            return
        lic = self.repo.get_by_id(lic_id)
        if not lic:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Archivo de Licencia",
            "license.key",
            "Archivos de Licencia (*.key);;Todos los archivos (*.*)",
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(lic.token)
                QMessageBox.information(
                    self,
                    "Archivo Guardado",
                    f"Licencia guardada exitosamente en:\n{file_path}\n\n"
                    "👉 Cópialo en la carpeta 'MQL5/Files' de MetaTrader 5.",
                )
            except Exception as e:
                QMessageBox.critical(self, "Error al Guardar", f"No se pudo guardar el archivo: {e}")

    def _show_context_menu(self, pos) -> None:
        lic_id = self._get_selected_license_id()
        if not lic_id:
            return
        lic = self.repo.get_by_id(lic_id)
        if not lic:
            return

        menu = QMenu(self)

        action_copy = menu.addAction(get_icon("copy", color="#334155", size=16), "Copiar Token")
        action_copy.triggered.connect(self._on_copy_token)

        action_export = menu.addAction(get_icon("save", color="#2563eb", size=16), "Guardar como license.key...")
        action_export.triggered.connect(self._on_export_file)

        action_verify = menu.addAction(get_icon("verify", color="#334155", size=16), "Verificar Licencia")
        action_verify.triggered.connect(lambda: self._open_verify_with_token(lic.token))

        menu.addSeparator()

        action_edit = menu.addAction(get_icon("edit", color="#334155", size=16), "Editar")
        action_edit.triggered.connect(self._on_edit_license)

        action_delete = menu.addAction(get_icon("minus", color="#dc2626", size=16), "Eliminar")
        action_delete.triggered.connect(self._on_delete_license)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _on_open_keys(self) -> None:
        dialog = KeysDialog(self, crypto_service=self.crypto_service)
        dialog.exec()

    def _on_open_verify(self) -> None:
        dialog = VerifyDialog(self, crypto_service=self.crypto_service)
        dialog.exec()

    def _open_verify_with_token(self, token: str) -> None:
        dialog = VerifyDialog(self, crypto_service=self.crypto_service, initial_token=token)
        dialog.exec()

    def _on_open_users(self) -> None:
        if not (self.current_user and self.current_user.is_admin):
            QMessageBox.warning(
                self,
                "Acceso Denegado",
                "Solo los usuarios con rol Administrador tienen permiso para gestionar usuarios.",
            )
            return

        dialog = UsersDialog(self, user_repo=self.user_repo, current_user=self.current_user)
        dialog.exec()
        # In case the current user changed their own full name or profile
        if self.current_user:
            refreshed = self.user_repo.get_by_id(self.current_user.id)
            if refreshed:
                self.current_user = refreshed
                if hasattr(self, "lbl_user_name"):
                    self.lbl_user_name.setText(self.current_user.name)
                if hasattr(self, "lbl_uname"):
                    role_badge = "ADMIN" if self.current_user.is_admin else "MANAGER"
                    role_color = "#1d4ed8" if self.current_user.is_admin else "#475569"
                    self.lbl_uname.setText(
                        f"@{self.current_user.username} • <span style='color: {role_color}; font-weight: 700;'>{role_badge}</span>"
                    )
                if hasattr(self, "btn_manage_users"):
                    self.btn_manage_users.setVisible(bool(self.current_user.is_admin))

    def _send_heartbeat(self) -> None:
        if not (self.current_user and self.session_token):
            return
        try:
            is_valid = self.user_repo.heartbeat(self.current_user.id, self.session_token)
            if not is_valid:
                if hasattr(self, "heartbeat_timer") and self.heartbeat_timer.isActive():
                    self.heartbeat_timer.stop()
                QMessageBox.warning(
                    self,
                    "Sesión Finalizada",
                    "Tu sesión ya no está activa o ha sido cerrada.\nLa aplicación se cerrará.",
                )
                self.close()
        except Exception:
            pass

    def closeEvent(self, event) -> None:
        if hasattr(self, "heartbeat_timer") and self.heartbeat_timer.isActive():
            self.heartbeat_timer.stop()
        if self.current_user and self.session_token:
            try:
                self.user_repo.end_session(self.current_user.id, self.session_token)
            except Exception:
                pass
        super().closeEvent(event)

    def _on_logout(self) -> None:
        reply = QMessageBox.question(
            self,
            "Cerrar Sesión",
            f"¿Estás seguro de que deseas cerrar la sesión de @{self.current_user.username if self.current_user else 'usuario'}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if hasattr(self, "heartbeat_timer") and self.heartbeat_timer.isActive():
                self.heartbeat_timer.stop()
            if self.current_user and self.session_token:
                try:
                    self.user_repo.end_session(self.current_user.id, self.session_token)
                except Exception:
                    pass
            self.logout_requested.emit()
            self.close()


