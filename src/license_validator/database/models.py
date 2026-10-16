from datetime import date, datetime
from typing import Any, Dict, Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, func
from license_validator.database.db import Base
from license_validator.core.auth import hash_password, verify_password


class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_name = Column(String(120), nullable=False, default="")
    account = Column(Integer, nullable=False, index=True)
    broker = Column(String(80), nullable=True, default="")
    tier = Column(String(50), nullable=True, default="")
    expires_at = Column(String(10), nullable=False)  # YYYY-MM-DD
    token = Column(Text, nullable=False)
    terminal_hash = Column(String(100), nullable=True, default="")
    notes = Column(Text, nullable=True, default="")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @property
    def expiration_date(self) -> Optional[date]:
        try:
            return datetime.strptime(self.expires_at, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    @property
    def is_expired(self) -> bool:
        exp = self.expiration_date
        if not exp:
            return True
        return exp < date.today()

    @property
    def days_remaining(self) -> int:
        exp = self.expiration_date
        if not exp:
            return -9999
        return (exp - date.today()).days

    @property
    def status(self) -> str:
        """Returns one of: 'Activa', 'Por expirar', 'Expirada'."""
        days = self.days_remaining
        if days < 0:
            return "Expirada"
        elif days <= 7:
            return "Por expirar"
        return "Activa"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "client_name": self.client_name,
            "account": self.account,
            "broker": self.broker,
            "tier": self.tier,
            "expires_at": self.expires_at,
            "token": self.token,
            "terminal_hash": self.terminal_hash or "",
            "notes": self.notes,
            "status": self.status,
            "days_remaining": self.days_remaining,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else "",
        }

    def __repr__(self) -> str:
        return f"<License(id={self.id}, client='{self.client_name}', account={self.account}, terminal='{self.terminal_hash}', expires='{self.expires_at}')>"


class User(Base):
    """User model for app authentication and access control."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(60), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="manager")  # 'admin' or 'manager'
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    current_session_token = Column(String(64), nullable=True, default=None)
    session_device = Column(String(100), nullable=True, default=None)
    last_heartbeat = Column(DateTime, nullable=True, default=None)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @property
    def is_admin(self) -> bool:
        return (self.role or "").strip().lower() == "admin"

    @property
    def is_manager(self) -> bool:
        return (self.role or "").strip().lower() == "manager"

    def set_password(self, plain_password: str) -> None:
        """Encrypts plain password with bcrypt and the environment secret."""
        self.password_hash = hash_password(plain_password)

    def check_password(self, plain_password: str) -> bool:
        """Validates plain password against the stored bcrypt hash."""
        return verify_password(plain_password, self.password_hash)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "role": self.role,
            "is_active": self.is_active,
            "session_device": self.session_device,
            "last_heartbeat": self.last_heartbeat.strftime("%Y-%m-%d %H:%M:%S") if self.last_heartbeat else "",
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else "",
        }

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', name='{self.name}', role='{self.role}')>"
