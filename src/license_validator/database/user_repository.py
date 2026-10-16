import uuid
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy import or_, desc
from sqlalchemy.orm import Session

from license_validator.database.db import get_session
from license_validator.database.models import User


class UserRepository:
    """Repository handling CRUD operations and authentication for Users in SQLite."""

    def __init__(self, session_factory=get_session) -> None:
        self.session_factory = session_factory

    def count(self) -> int:
        """Returns the total number of registered users."""
        with self.session_factory() as session:
            return session.query(User).count()

    def get_by_id(self, user_id: int) -> Optional[User]:
        with self.session_factory() as session:
            return session.query(User).filter(User.id == user_id).first()

    def get_by_username(self, username: str) -> Optional[User]:
        clean_user = username.strip().lower()
        with self.session_factory() as session:
            return session.query(User).filter(User.username.ilike(clean_user)).first()

    def get_all(self, search_query: Optional[str] = None) -> List[User]:
        with self.session_factory() as session:
            query = session.query(User)
            if search_query:
                clean_search = f"%{search_query.strip()}%"
                query = query.filter(
                    or_(
                        User.username.ilike(clean_search),
                        User.name.ilike(clean_search),
                    )
                )
            return query.order_by(desc(User.id)).all()

    def create(
        self,
        username: str,
        name: str,
        password: str,
        role: str = "manager",
        is_active: bool = True,
    ) -> User:
        """Creates a new user with encrypted password using bcrypt."""
        clean_user = username.strip().lower()
        clean_name = name.strip()
        clean_role = (role or "manager").strip().lower()
        if clean_role not in ("admin", "manager"):
            clean_role = "manager"

        with self.session_factory() as session:
            existing = session.query(User).filter(User.username.ilike(clean_user)).first()
            if existing:
                raise ValueError(f"El nombre de usuario '{clean_user}' ya existe.")

            # El primer usuario registrado en el sistema siempre será admin
            user_count = session.query(User).count()
            if user_count == 0:
                clean_role = "admin"

            user = User(
                username=clean_user,
                name=clean_name,
                role=clean_role,
                is_active=is_active,
            )
            user.set_password(password)

            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    def update(
        self,
        user_id: int,
        name: Optional[str] = None,
        role: Optional[str] = None,
        password: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[User]:
        with self.session_factory() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return None

            if name is not None:
                user.name = name.strip()
            if role is not None:
                clean_role = role.strip().lower()
                if clean_role in ("admin", "manager"):
                    user.role = clean_role
            if password is not None and password.strip():
                user.set_password(password.strip())
            if is_active is not None:
                user.is_active = is_active

            user.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(user)
            return user

    def delete(self, user_id: int) -> bool:
        with self.session_factory() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            session.delete(user)
            session.commit()
            return True

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Authenticates a user by username and plain password.
        Returns the User object if valid, otherwise None.
        """
        user = self.get_by_username(username)
        if not user or not user.is_active:
            return None

        if user.check_password(password):
            return user
        return None

    def authenticate_and_start_session(
        self,
        username: str,
        password: str,
        device_name: str,
        timeout_seconds: int = 120,
    ) -> Tuple[bool, Optional[User], Optional[str], Optional[str]]:
        """
        Authenticates credentials and ensures single active session.
        Returns (success, user_obj, session_token, error_message).
        If another active session exists and heartbeated within timeout_seconds, login is rejected.
        """
        with self.session_factory() as session:
            clean_user = username.strip().lower()
            user = session.query(User).filter(User.username.ilike(clean_user)).first()

            if not user:
                return False, None, None, "Usuario o contraseña incorrectos."

            if not user.is_active:
                return False, None, None, "Esta cuenta ha sido desactivada por un administrador."

            if not user.check_password(password):
                return False, None, None, "Usuario o contraseña incorrectos."

            # Check for existing active concurrent session
            now = datetime.utcnow()
            if user.current_session_token and user.last_heartbeat:
                elapsed = (now - user.last_heartbeat).total_seconds()
                # If session has heartbeated recently, reject new concurrent login
                if elapsed < timeout_seconds:
                    other_device = user.session_device or "otro equipo"
                    last_time = user.last_heartbeat.strftime("%H:%M:%S")
                    return (
                        False,
                        None,
                        None,
                        f"Esta cuenta ya tiene una sesión abierta en el equipo '{other_device}' "
                        f"(actividad reciente: {last_time} UTC).\n\n"
                        f"Por seguridad, no se permite el acceso simultáneo desde dos lugares. "
                        f"Cierra la aplicación en ese equipo para ingresar.",
                    )

            # Start new session
            new_token = str(uuid.uuid4())
            user.current_session_token = new_token
            user.session_device = device_name
            user.last_heartbeat = now
            session.commit()
            session.refresh(user)
            return True, user, new_token, None

    def start_session_for_user(self, user_id: int, device_name: str) -> str:
        """Starts a session for a newly created or existing user, returning session_token."""
        with self.session_factory() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("Usuario no encontrado.")
            new_token = str(uuid.uuid4())
            user.current_session_token = new_token
            user.session_device = device_name
            user.last_heartbeat = datetime.utcnow()
            session.commit()
            return new_token

    def heartbeat(self, user_id: int, session_token: str) -> bool:
        """
        Updates last_heartbeat timestamp.
        Returns True if heartbeat was accepted, False if session is invalid or replaced.
        """
        if not user_id or not session_token:
            return False
        with self.session_factory() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user or user.current_session_token != session_token:
                return False
            user.last_heartbeat = datetime.utcnow()
            session.commit()
            return True

    def end_session(self, user_id: int, session_token: str) -> bool:
        """Gracefully ends an active session on logout or app window close."""
        if not user_id or not session_token:
            return False
        with self.session_factory() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user and user.current_session_token == session_token:
                user.current_session_token = None
                user.session_device = None
                user.last_heartbeat = None
                session.commit()
                return True
            return False

    def force_reset_session(self, user_id: int) -> bool:
        """Admin recovery tool to forcibly clear a stuck session."""
        with self.session_factory() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                user.current_session_token = None
                user.session_device = None
                user.last_heartbeat = None
                session.commit()
                return True
            return False

