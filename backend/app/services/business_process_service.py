from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business_process import BusinessProcess
from app.schemas.business_process import BusinessProcessCreate, BusinessProcessUpdate

from app.services import department_service


def list_business_processes(
    db: Session,
    *,
    skip: int,
    limit: int,
    department_id: int | None = None,
) -> list[BusinessProcess]:
    stmt = select(BusinessProcess).order_by(BusinessProcess.id)
    if department_id is not None:
        stmt = stmt.where(BusinessProcess.department_id == department_id)
    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


def get_business_process(db: Session, process_id: int) -> BusinessProcess | None:
    return db.get(BusinessProcess, process_id)


def create_business_process(
    db: Session, data: BusinessProcessCreate
) -> BusinessProcess | None:
    if department_service.get_department(db, data.department_id) is None:
        return None
    obj = BusinessProcess(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_business_process(
    db: Session, process_id: int, data: BusinessProcessUpdate
) -> BusinessProcess | None:
    obj = get_business_process(db, process_id)
    if obj is None:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_business_process(db: Session, process_id: int) -> bool:
    obj = get_business_process(db, process_id)
    if obj is None:
        return False
    db.delete(obj)
    db.commit()
    return True
