from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.common import DeleteStatusResponse
from app.schemas.department import DepartmentCreate, DepartmentRead, DepartmentUpdate
from app.services import department_service

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentRead])
def list_departments(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[DepartmentRead]:
    return department_service.list_departments(db, skip=skip, limit=limit)


@router.post("", response_model=DepartmentRead, status_code=201)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
) -> DepartmentRead:
    return department_service.create_department(db, payload)


@router.get("/{department_id}", response_model=DepartmentRead)
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
) -> DepartmentRead:
    obj = department_service.get_department(db, department_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Department not found")
    return obj


@router.put("/{department_id}", response_model=DepartmentRead)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
) -> DepartmentRead:
    obj = department_service.update_department(db, department_id, payload)
    if obj is None:
        raise HTTPException(status_code=404, detail="Department not found")
    return obj


@router.delete("/{department_id}", response_model=DeleteStatusResponse)
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
) -> DeleteStatusResponse:
    ok = department_service.delete_department(db, department_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Department not found")
    return DeleteStatusResponse(message="Department deleted")
