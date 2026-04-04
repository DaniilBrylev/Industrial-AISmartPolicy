from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentUpdate


def list_departments(db: Session, *, skip: int, limit: int) -> list[Department]:
    stmt = select(Department).order_by(Department.id).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


def get_department(db: Session, department_id: int) -> Department | None:
    return db.get(Department, department_id)


def create_department(db: Session, data: DepartmentCreate) -> Department:
    obj = Department(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_department(
    db: Session, department_id: int, data: DepartmentUpdate
) -> Department | None:
    obj = get_department(db, department_id)
    if obj is None:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_department(db: Session, department_id: int) -> bool:
    obj = get_department(db, department_id)
    if obj is None:
        return False
    db.delete(obj)
    db.commit()
    return True
