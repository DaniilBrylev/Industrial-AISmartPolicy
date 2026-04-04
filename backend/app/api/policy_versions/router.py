from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.policy import PolicyVersionCreate, PolicyVersionRead
from app.services import policy_document_service

router = APIRouter(prefix="/policy-versions", tags=["policy-versions"])


@router.get("", response_model=list[PolicyVersionRead])
def list_policy_versions(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    policy_document_id: int | None = Query(
        None,
        description="Фильтр по документу политики",
    ),
) -> list[PolicyVersionRead]:
    return policy_document_service.list_policy_versions(
        db,
        skip=skip,
        limit=limit,
        policy_document_id=policy_document_id,
    )


@router.post("", response_model=PolicyVersionRead, status_code=201)
def create_policy_version(
    payload: PolicyVersionCreate,
    db: Session = Depends(get_db),
) -> PolicyVersionRead:
    result = policy_document_service.create_policy_version(db, payload)
    if result is None:
        raise HTTPException(status_code=404, detail="Policy document not found")
    if isinstance(result, str):
        raise HTTPException(
            status_code=409,
            detail="Version number already exists for this policy document",
        )
    return result


@router.get("/{version_id}", response_model=PolicyVersionRead)
def get_policy_version(
    version_id: int,
    db: Session = Depends(get_db),
) -> PolicyVersionRead:
    obj = policy_document_service.get_policy_version(db, version_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Policy version not found")
    return obj
