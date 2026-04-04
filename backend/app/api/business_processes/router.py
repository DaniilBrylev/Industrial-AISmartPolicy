from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.business_process import (
    BusinessProcessCreate,
    BusinessProcessRead,
    BusinessProcessUpdate,
)
from app.schemas.common import DeleteStatusResponse
from app.services import business_process_service

router = APIRouter(prefix="/business-processes", tags=["business-processes"])


@router.get("", response_model=list[BusinessProcessRead])
def list_business_processes(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    department_id: int | None = Query(None, description="Фильтр по подразделению"),
) -> list[BusinessProcessRead]:
    return business_process_service.list_business_processes(
        db, skip=skip, limit=limit, department_id=department_id
    )


@router.post("", response_model=BusinessProcessRead, status_code=201)
def create_business_process(
    payload: BusinessProcessCreate,
    db: Session = Depends(get_db),
) -> BusinessProcessRead:
    obj = business_process_service.create_business_process(db, payload)
    if obj is None:
        raise HTTPException(status_code=404, detail="Department not found")
    return obj


@router.get("/{process_id}", response_model=BusinessProcessRead)
def get_business_process(
    process_id: int,
    db: Session = Depends(get_db),
) -> BusinessProcessRead:
    obj = business_process_service.get_business_process(db, process_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Business process not found")
    return obj


@router.put("/{process_id}", response_model=BusinessProcessRead)
def update_business_process(
    process_id: int,
    payload: BusinessProcessUpdate,
    db: Session = Depends(get_db),
) -> BusinessProcessRead:
    obj = business_process_service.update_business_process(db, process_id, payload)
    if obj is None:
        raise HTTPException(status_code=404, detail="Business process not found")
    return obj


@router.delete("/{process_id}", response_model=DeleteStatusResponse)
def delete_business_process(
    process_id: int,
    db: Session = Depends(get_db),
) -> DeleteStatusResponse:
    ok = business_process_service.delete_business_process(db, process_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Business process not found")
    return DeleteStatusResponse(message="Business process deleted")
