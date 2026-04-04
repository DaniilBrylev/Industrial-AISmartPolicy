from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.common import DeleteStatusResponse
from app.schemas.asset import AssetCreate, AssetRead, AssetUpdate
from app.services import asset_service

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[AssetRead])
def list_assets(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    department_id: int | None = Query(None, description="Фильтр по подразделению"),
) -> list[AssetRead]:
    return asset_service.list_assets(
        db, skip=skip, limit=limit, department_id=department_id
    )


@router.post("", response_model=AssetRead, status_code=201)
def create_asset(
    payload: AssetCreate,
    db: Session = Depends(get_db),
) -> AssetRead:
    obj = asset_service.create_asset(db, payload)
    if obj is None:
        raise HTTPException(status_code=404, detail="Department not found")
    return obj


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
) -> AssetRead:
    obj = asset_service.get_asset(db, asset_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return obj


@router.put("/{asset_id}", response_model=AssetRead)
def update_asset(
    asset_id: int,
    payload: AssetUpdate,
    db: Session = Depends(get_db),
) -> AssetRead:
    obj = asset_service.update_asset(db, asset_id, payload)
    if obj is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return obj


@router.delete("/{asset_id}", response_model=DeleteStatusResponse)
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
) -> DeleteStatusResponse:
    ok = asset_service.delete_asset(db, asset_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Asset not found")
    return DeleteStatusResponse(message="Asset deleted")
