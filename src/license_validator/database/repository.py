from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import or_, desc
from sqlalchemy.orm import Session

from license_validator.database.db import get_session
from license_validator.database.models import License


class LicenseRepository:
    """Repository handling CRUD operations for licenses in SQLite."""

    def __init__(self, session_factory=get_session) -> None:
        self.session_factory = session_factory

    def get_all(
        self,
        search_query: Optional[str] = None,
        status_filter: Optional[str] = None,
        tier_filter: Optional[str] = None,
    ) -> List[License]:
        with self.session_factory() as session:
            query = session.query(License)

            if search_query:
                clean_search = f"%{search_query.strip()}%"
                # Search by client_name, account (as string), broker, notes, or terminal_hash
                from sqlalchemy import cast, String
                query = query.filter(
                    or_(
                        License.client_name.ilike(clean_search),
                        License.broker.ilike(clean_search),
                        License.notes.ilike(clean_search),
                        License.terminal_hash.ilike(clean_search),
                        cast(License.account, String).ilike(clean_search),
                    )
                )

            if tier_filter and tier_filter.upper() != "TODOS":
                query = query.filter(License.tier == tier_filter)

            results = query.order_by(desc(License.id)).all()

            # Filter by dynamic status in Python if requested
            if status_filter and status_filter.upper() != "TODOS":
                results = [lic for lic in results if lic.status.upper() == status_filter.upper()]

            # Detach instances or return list (with SQLite check_same_thread=False)
            return results

    def get_by_id(self, license_id: int) -> Optional[License]:
        with self.session_factory() as session:
            return session.query(License).filter(License.id == license_id).first()

    def get_by_account(self, account: int) -> List[License]:
        with self.session_factory() as session:
            return session.query(License).filter(License.account == int(account)).all()

    def create(
        self,
        account: int,
        expires_at: str,
        token: str,
        broker: str = "",
        tier: str = "",
        client_name: str = "",
        notes: str = "",
        terminal_hash: str = "",
    ) -> License:
        with self.session_factory() as session:
            license_obj = License(
                account=int(account),
                expires_at=str(expires_at).strip(),
                token=str(token).strip(),
                broker=str(broker).strip(),
                tier=str(tier).strip(),
                client_name=str(client_name).strip(),
                notes=str(notes).strip() if notes else "",
                terminal_hash=str(terminal_hash).strip().upper() if terminal_hash else "",
            )
            session.add(license_obj)
            session.commit()
            session.refresh(license_obj)
            return license_obj

    def update(
        self,
        license_id: int,
        account: Optional[int] = None,
        expires_at: Optional[str] = None,
        token: Optional[str] = None,
        broker: Optional[str] = None,
        tier: Optional[str] = None,
        client_name: Optional[str] = None,
        notes: Optional[str] = None,
        terminal_hash: Optional[str] = None,
    ) -> Optional[License]:
        with self.session_factory() as session:
            lic = session.query(License).filter(License.id == license_id).first()
            if not lic:
                return None

            if account is not None:
                lic.account = int(account)
            if expires_at is not None:
                lic.expires_at = str(expires_at).strip()
            if token is not None:
                lic.token = str(token).strip()
            if broker is not None:
                lic.broker = str(broker).strip()
            if tier is not None:
                lic.tier = str(tier).strip()
            if client_name is not None:
                lic.client_name = str(client_name).strip()
            if notes is not None:
                lic.notes = str(notes).strip()
            if terminal_hash is not None:
                lic.terminal_hash = str(terminal_hash).strip().upper()

            lic.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(lic)
            return lic

    def delete(self, license_id: int) -> bool:
        with self.session_factory() as session:
            lic = session.query(License).filter(License.id == license_id).first()
            if not lic:
                return False
            session.delete(lic)
            session.commit()
            return True

    def get_stats(self) -> Dict[str, int]:
        licenses = self.get_all()
        total = len(licenses)
        active = sum(1 for lic in licenses if lic.status == "Activa")
        expiring = sum(1 for lic in licenses if lic.status == "Por expirar")
        expired = sum(1 for lic in licenses if lic.status == "Expirada")
        return {
            "total": total,
            "active": active,
            "expiring": expiring,
            "expired": expired,
        }
