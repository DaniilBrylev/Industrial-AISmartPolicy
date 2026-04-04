from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.common import DeleteStatusResponse
from app.schemas.policy import (
    PolicyDocumentCreate,
    PolicyDocumentRead,
    PolicyDocumentUpdate,
    PolicySnapshotDiff,
    PolicyVersionSummaryRead,
)
from app.services import policy_document_service

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("", response_model=list[PolicyDocumentRead])
def list_policies(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[PolicyDocumentRead]:
    return policy_document_service.list_policy_documents(db, skip=skip, limit=limit)


@router.post("", response_model=PolicyDocumentRead, status_code=201)
def create_policy(
    payload: PolicyDocumentCreate,
    db: Session = Depends(get_db),
) -> PolicyDocumentRead:
    return policy_document_service.create_policy_document(db, payload)


@router.get(
    "/{policy_id}/versions",
    response_model=list[PolicyVersionSummaryRead],
)
def list_policy_versions_by_document(
    policy_id: int,
    db: Session = Depends(get_db),
) -> list[PolicyVersionSummaryRead]:
    if policy_document_service.get_policy_document(db, policy_id) is None:
        raise HTTPException(status_code=404, detail="Policy document not found")
    rows = policy_document_service.list_policy_versions(
        db, skip=0, limit=500, policy_document_id=policy_id
    )
    return [PolicyVersionSummaryRead.model_validate(r) for r in rows]


@router.get("/{policy_id}/diff", response_model=PolicySnapshotDiff)
def compare_policy_versions(
    policy_id: int,
    db: Session = Depends(get_db),
    from_version: int = Query(..., ge=1, alias="from", description="Номер версии «с»"),
    to_version: int = Query(..., ge=1, alias="to", description="Номер версии «по»"),
) -> PolicySnapshotDiff:
    if policy_document_service.get_policy_document(db, policy_id) is None:
        raise HTTPException(status_code=404, detail="Policy document not found")

    v_from = policy_document_service.get_policy_version_by_number(
        db, policy_id, from_version
    )
    v_to = policy_document_service.get_policy_version_by_number(db, policy_id, to_version)
    if v_from is None or v_to is None:
        raise HTTPException(status_code=404, detail="One or both versions not found")

    old_snap = v_from.snapshot if isinstance(v_from.snapshot, dict) else {}
    new_snap = v_to.snapshot if isinstance(v_to.snapshot, dict) else {}
    raw = policy_document_service.compute_diff(old_snap, new_snap)
    return PolicySnapshotDiff.model_validate(raw)


@router.get("/{policy_id}", response_model=PolicyDocumentRead)
def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
) -> PolicyDocumentRead:
    obj = policy_document_service.get_policy_document(db, policy_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Policy document not found")
    return obj


@router.put("/{policy_id}", response_model=PolicyDocumentRead)
def update_policy(
    policy_id: int,
    payload: PolicyDocumentUpdate,
    db: Session = Depends(get_db),
) -> PolicyDocumentRead:
    result = policy_document_service.update_policy_document(db, policy_id, payload)
    if result is None:
        raise HTTPException(status_code=404, detail="Policy document not found")
    if isinstance(result, str):
        raise HTTPException(
            status_code=400,
            detail="current_version_id must reference an existing version of this policy",
        )
    return result


@router.delete("/{policy_id}", response_model=DeleteStatusResponse)
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
) -> DeleteStatusResponse:
    ok = policy_document_service.delete_policy_document(db, policy_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Policy document not found")
    return DeleteStatusResponse(message="Policy document deleted")
