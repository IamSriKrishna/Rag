from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.security import create_access_token, hash_password, verify_password
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.tenants = TenantRepository(db)

    def register(self, tenant_name: str, email: str, password: str) -> User:
        normalized = email.lower().strip()
        if self.users.get_by_email(normalized):
            raise HTTPException(status_code=409, detail="Email is already registered")
        try:
            tenant = Tenant(name=tenant_name.strip())
            self.db.add(tenant)
            self.db.flush()
            user = User(
                tenant_id=tenant.id,
                email=normalized,
                hashed_password=hash_password(password),
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=409, detail="Account could not be created"
            ) from exc

    def login(self, email: str, password: str) -> str:
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return create_access_token(user.id, user.tenant_id)
