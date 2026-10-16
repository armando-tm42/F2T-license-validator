from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QCheckBox,
    QAbstractItemView,
)

from license_validator.database.models import User
from license_validator.database.user_repository import UserRepository
from license_validator.gui.icons import get_icon


class UserFormDialog(QDialog):
    """Dialog to create or edit a user."""

    def __init__(
        self,
        parent=None,
        user: Optional[User] = None,
        is_password_only: bool = False,
        current_user: Optional[User] = None,
    ) -> None:
        super().__init__(parent)
        self.user = user
        self.is_password_only = is_password_only
        self.is_edit_mode = user is not None and not is_password_only
        self.current_user = current_user

        if self.is_password_only:
            self.setWindowTitle(f"Cambiar Contraseña: {user.username}")
        elif self.is_edit_mode:
            self.setWindowTitle(f"Editar Usuario: {user.username}")
        else:
            self.setWindowTitle("Nuevo Usuario del Sistema")

        self.setMinimumWidth(420)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        form = QFormLayout()
        form.setSpacing(12)

        if not self.is_password_only:
            self.input_username = QLineEdit()
            self.input_username.setPlaceholderText("Ej: operador1")
            if self.is_edit_mode and self.user:
                self.input_username.setText(self.user.username)
                self.input_username.setEnabled(False)  # Username is identifier
            form.addRow("Usuario (*):", self.input_username)

            self.input_name = QLineEdit()
            self.input_name.setPlaceholderText("Ej: Carlos Rodríguez")
            if self.is_edit_mode and self.user:
                self.input_name.setText(self.user.name)
            form.addRow("Nombre Completo (*):", self.input_name)

            self.combo_role = QComboBox()
            self.combo_role.addItem("Manager (CRUD de Licencias)", "manager")
            self.combo_role.addItem("Administrador (Control Total + Usuarios)", "admin")
            if self.is_edit_mode and self.user:
                idx = self.combo_role.findData(self.user.role or "manager")
                if idx >= 0:
                    self.combo_role.setCurrentIndex(idx)
                # If editing own account, prevent demoting self from admin
                if self.current_user and self.user.id == self.current_user.id and self.user.is_admin:
                    self.combo_role.setEnabled(False)
                    self.combo_role.setToolTip("No puedes quitarte el rol de Administrador a ti mismo.")
            form.addRow("Rol (*):", self.combo_role)

        if not self.is_edit_mode or self.is_password_only:
            self.input_password = QLineEdit()
            self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
            self.input_password.setPlaceholderText("Mínimo 4 caracteres")
            form.addRow("Nueva Contraseña (*):", self.input_password)

            self.input_confirm = QLineEdit()
            self.input_confirm.setEchoMode(QLineEdit.EchoMode.Password)
            self.input_confirm.setPlaceholderText("Repite la contraseña")
            form.addRow("Confirmar (*):", self.input_confirm)

        if self.is_edit_mode and not self.is_password_only and self.user:
            self.chk_active = QCheckBox("Usuario activo (puede iniciar sesión)")
            self.chk_active.setChecked(self.user.is_active)
            form.addRow("Estado:", self.chk_active)

        layout.addLayout(form)

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)

        btn_save = QPushButton("Guardar")
        btn_save.setObjectName("PrimaryButton")
        btn_save.clicked.connect(self._on_save)
        btns.addWidget(btn_save)

        layout.addLayout(btns)

    def _on_save(self) -> None:
        if not self.is_password_only:
            name = self.input_name.text().strip()
            if not name:
                QMessageBox.warning(self, "Campo Requerido", "El nombre completo no puede estar vacío.")
                return

            if not self.is_edit_mode:
                username = self.input_username.text().strip()
                if not username:
                    QMessageBox.warning(self, "Campo Requerido", "El nombre de usuario es obligatorio.")
                    return

        if not self.is_edit_mode or self.is_password_only:
            pwd = self.input_password.text().strip()
            confirm = self.input_confirm.text().strip()
            if len(pwd) < 4:
                QMessageBox.warning(self, "Contraseña Corta", "La contraseña debe tener al menos 4 caracteres.")
                return
            if pwd != confirm:
                QMessageBox.warning(self, "Error", "Las contraseñas no coinciden.")
                return

        self.accept()


class UsersDialog(QDialog):
    """Management dialog for User CRUD operations (Admin only)."""

    def __init__(
        self,
        parent=None,
        user_repo: Optional[UserRepository] = None,
        current_user: Optional[User] = None,
    ) -> None:
        super().__init__(parent)
        self.user_repo = user_repo or UserRepository()
        self.current_user = current_user

        self.setWindowTitle("Administración de Usuarios y Accesos")
        self.setMinimumSize(780, 480)
        self.setModal(True)

        self._init_ui()
        self.refresh_users()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QVBoxLayout()
        title = QLabel("👥 Gestión de Usuarios y Roles")
        title.setObjectName("HeaderTitle")
        subtitle = QLabel("Crea, edita y administra los usuarios y roles (Admin / Manager) con acceso al sistema.")
        subtitle.setObjectName("HeaderSubtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        layout.addLayout(header)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.btn_new = QPushButton("Nuevo Usuario")
        self.btn_new.setObjectName("PrimaryButton")
        self.btn_new.setIcon(get_icon("plus", color="#ffffff", size=16))
        self.btn_new.setIconSize(QSize(16, 16))
        self.btn_new.clicked.connect(self._on_new_user)
        toolbar.addWidget(self.btn_new)

        self.btn_edit = QPushButton("Editar")
        self.btn_edit.setIcon(get_icon("edit", color="#334155", size=16))
        self.btn_edit.setIconSize(QSize(16, 16))
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self._on_edit_user)
        toolbar.addWidget(self.btn_edit)

        self.btn_change_pwd = QPushButton("Cambiar Contraseña")
        self.btn_change_pwd.setIcon(get_icon("lock", color="#334155", size=16))
        self.btn_change_pwd.setIconSize(QSize(16, 16))
        self.btn_change_pwd.setEnabled(False)
        self.btn_change_pwd.clicked.connect(self._on_change_password)
        toolbar.addWidget(self.btn_change_pwd)

        self.btn_delete = QPushButton("Eliminar")
        self.btn_delete.setIcon(get_icon("minus", color="#dc2626", size=16))
        self.btn_delete.setIconSize(QSize(16, 16))
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._on_delete_user)
        toolbar.addWidget(self.btn_delete)

        self.btn_reset_session = QPushButton("Liberar Sesión")
        self.btn_reset_session.setIcon(get_icon("refresh", color="#334155", size=16))
        self.btn_reset_session.setIconSize(QSize(16, 16))
        self.btn_reset_session.setEnabled(False)
        self.btn_reset_session.setToolTip("Cierra forzosamente la sesión activa del usuario para permitirle entrar desde otro equipo.")
        self.btn_reset_session.clicked.connect(self._on_reset_session)
        toolbar.addWidget(self.btn_reset_session)

        toolbar.addStretch()

        # Search
        self.input_search = QLineEdit()
        self.input_search.addAction(
            get_icon("search", color="#64748b", size=16),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self.input_search.setPlaceholderText("Buscar usuario...")
        self.input_search.setMaximumWidth(220)
        self.input_search.textChanged.connect(self.refresh_users)
        toolbar.addWidget(self.input_search)

        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Usuario",
            "Nombre Completo",
            "Rol",
            "Estado",
            "Sesión Actual",
            "Fecha Creación",
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().resizeSection(0, 45)
        self.table.horizontalHeader().resizeSection(1, 120)
        self.table.horizontalHeader().resizeSection(2, 160)
        self.table.horizontalHeader().resizeSection(3, 120)
        self.table.horizontalHeader().resizeSection(4, 85)
        self.table.horizontalHeader().resizeSection(5, 170)

        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table)

        # Close
        bottom = QHBoxLayout()
        bottom.addStretch()
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        bottom.addWidget(btn_close)
        layout.addLayout(bottom)

    def refresh_users(self) -> None:
        query = self.input_search.text().strip()
        users = self.user_repo.get_all(search_query=query or None)
        now = datetime.utcnow()

        self.table.setRowCount(len(users))
        for row, u in enumerate(users):
            item_id = QTableWidgetItem(str(u.id))
            item_id.setData(Qt.ItemDataRole.UserRole, u.id)
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            user_display = f"@{u.username}"
            if self.current_user and u.id == self.current_user.id:
                user_display += " (Tú)"

            item_user = QTableWidgetItem(user_display)
            item_name = QTableWidgetItem(u.name)

            role_display = "🛡️ Administrador" if u.is_admin else "👤 Manager"
            item_role = QTableWidgetItem(role_display)
            item_role.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if u.is_admin:
                item_role.setForeground(Qt.GlobalColor.darkBlue)

            status_str = "● Activo" if u.is_active else "○ Inactivo"
            item_status = QTableWidgetItem(status_str)
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_status.setForeground(Qt.GlobalColor.darkGreen if u.is_active else Qt.GlobalColor.gray)

            # Sesión activa
            if u.current_session_token and u.last_heartbeat:
                elapsed = (now - u.last_heartbeat).total_seconds()
                if elapsed < 120:
                    device = u.session_device or "Conectado"
                    session_str = f"🟢 En línea ({device})"
                    item_session = QTableWidgetItem(session_str)
                    item_session.setForeground(Qt.GlobalColor.darkGreen)
                else:
                    session_str = "⚪ Inactiva (>2m)"
                    item_session = QTableWidgetItem(session_str)
                    item_session.setForeground(Qt.GlobalColor.gray)
            else:
                session_str = "⚪ Desconectado"
                item_session = QTableWidgetItem(session_str)
                item_session.setForeground(Qt.GlobalColor.gray)
            item_session.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            created_str = u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else ""
            item_created = QTableWidgetItem(created_str)
            item_created.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(row, 0, item_id)
            self.table.setItem(row, 1, item_user)
            self.table.setItem(row, 2, item_name)
            self.table.setItem(row, 3, item_role)
            self.table.setItem(row, 4, item_status)
            self.table.setItem(row, 5, item_session)
            self.table.setItem(row, 6, item_created)

        self._on_selection_changed()

    def _get_selected_user_id(self) -> Optional[int]:
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_selection_changed(self) -> None:
        has_sel = self._get_selected_user_id() is not None
        self.btn_edit.setEnabled(has_sel)
        self.btn_change_pwd.setEnabled(has_sel)
        self.btn_delete.setEnabled(has_sel)
        self.btn_reset_session.setEnabled(has_sel)

    def _on_reset_session(self) -> None:
        if not (self.current_user and self.current_user.is_admin):
            QMessageBox.warning(self, "Acceso Denegado", "Solo un Administrador puede liberar sesiones.")
            return

        user_id = self._get_selected_user_id()
        if not user_id:
            return
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return

        reply = QMessageBox.question(
            self,
            "Liberar Sesión Activa",
            f"¿Deseas cerrar forzosamente la sesión activa del usuario @{user.username}?\n\n"
            f"Esto liberará el bloqueo para que pueda iniciar sesión en otro equipo de inmediato.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.user_repo.force_reset_session(user_id)
            self.refresh_users()
            QMessageBox.information(
                self,
                "Sesión Liberada",
                f"La sesión de @{user.username} ha sido liberada exitosamente.",
            )

    def _on_new_user(self) -> None:
        if not (self.current_user and self.current_user.is_admin):
            QMessageBox.warning(self, "Acceso Denegado", "Solo un Administrador puede crear nuevos usuarios.")
            return

        dialog = UserFormDialog(self, current_user=self.current_user)
        if dialog.exec():
            username = dialog.input_username.text().strip()
            name = dialog.input_name.text().strip()
            password = dialog.input_password.text().strip()
            role = dialog.combo_role.currentData() or "manager"
            try:
                self.user_repo.create(
                    username=username,
                    name=name,
                    password=password,
                    role=role,
                )
                self.refresh_users()
                QMessageBox.information(
                    self,
                    "Usuario Creado",
                    f"Usuario @{username} con rol '{role.upper()}' creado exitosamente."
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo crear el usuario: {e}")

    def _on_edit_user(self) -> None:
        if not (self.current_user and self.current_user.is_admin):
            QMessageBox.warning(self, "Acceso Denegado", "Solo un Administrador puede editar usuarios.")
            return

        user_id = self._get_selected_user_id()
        if not user_id:
            return
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return

        dialog = UserFormDialog(self, user=user, current_user=self.current_user)
        if dialog.exec():
            name = dialog.input_name.text().strip()
            is_active = dialog.chk_active.isChecked()
            role = dialog.combo_role.currentData() or user.role

            # Don't let user deactivate themselves
            if self.current_user and user.id == self.current_user.id and not is_active:
                QMessageBox.warning(self, "Acción no permitida", "No puedes desactivar tu propia cuenta actual.")
                is_active = True

            self.user_repo.update(
                user_id=user_id,
                name=name,
                role=role,
                is_active=is_active,
            )
            self.refresh_users()

    def _on_change_password(self) -> None:
        if not (self.current_user and self.current_user.is_admin):
            QMessageBox.warning(self, "Acceso Denegado", "Solo un Administrador puede cambiar contraseñas.")
            return

        user_id = self._get_selected_user_id()
        if not user_id:
            return
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return

        dialog = UserFormDialog(self, user=user, is_password_only=True, current_user=self.current_user)
        if dialog.exec():
            new_pwd = dialog.input_password.text().strip()
            self.user_repo.update(user_id=user_id, password=new_pwd)
            QMessageBox.information(
                self, "Contraseña Actualizada", f"La contraseña de @{user.username} ha sido actualizada."
            )

    def _on_delete_user(self) -> None:
        if not (self.current_user and self.current_user.is_admin):
            QMessageBox.warning(self, "Acceso Denegado", "Solo un Administrador puede eliminar usuarios.")
            return

        user_id = self._get_selected_user_id()
        if not user_id:
            return
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return

        if self.current_user and user.id == self.current_user.id:
            QMessageBox.warning(self, "Acción no permitida", "No puedes eliminar la cuenta con la que has iniciado sesión.")
            return

        if self.user_repo.count() <= 1:
            QMessageBox.warning(self, "Acción no permitida", "No puedes eliminar el único usuario del sistema.")
            return

        # Check if deleting the last admin
        all_users = self.user_repo.get_all()
        admin_count = sum(1 for u in all_users if u.is_admin)
        if user.is_admin and admin_count <= 1:
            QMessageBox.warning(self, "Acción no permitida", "No puedes eliminar al único Administrador del sistema.")
            return

        reply = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Estás seguro de que deseas eliminar al usuario @{user.username} ({user.name}) con rol {user.role.upper()}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.user_repo.delete(user_id)
            self.refresh_users()
