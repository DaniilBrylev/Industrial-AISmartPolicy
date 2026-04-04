from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.schemas.asset import AssetCreate, AssetUpdate

from app.services import department_service


def list_assets(
    db: Session,
    *,
    skip: int,
    limit: int,
    department_id: int | None = None,
) -> list[Asset]:
    stmt = select(Asset).order_by(Asset.id)
    if department_id is not None:
        stmt = stmt.where(Asset.department_id == department_id)
    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


def get_asset(db: Session, asset_id: int) -> Asset | None:
    return db.get(Asset, asset_id)


def create_asset(db: Session, data: AssetCreate) -> Asset | None:
    if department_service.get_department(db, data.department_id) is None:
        return None
    obj = Asset(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_asset(db: Session, asset_id: int, data: AssetUpdate) -> Asset | None:
    obj = get_asset(db, asset_id)
    if obj is None:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_asset(db: Session, asset_id: int) -> bool:
    obj = get_asset(db, asset_id)
    if obj is None:
        return False
    db.delete(obj)
    db.commit()
    return True
