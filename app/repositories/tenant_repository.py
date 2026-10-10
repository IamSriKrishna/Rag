from sqlalchemy.orm import Session
from app.models.tenant import Tenant


class TenantRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str) -> Tenant:
        tenant = Tenant(name=name.strip())

        self.db.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)

        return tenant
